"""Gemini JSON boundary. No network I/O until after a durable reservation."""
import asyncio
from collections import OrderedDict
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import json
import logging
import math
import time
from typing import Callable, TypeVar
from uuid import uuid4

from google import genai
from google.genai import errors, types
import httpx
import httpx2
from pydantic import BaseModel

from ..config import Settings
from ..models import Usage
from .budget import Budget, SCALE
from .errors import ServiceError

logger = logging.getLogger(__name__)
Output = TypeVar('Output', bound=BaseModel)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def provider_schema(model: type[BaseModel]) -> dict:
    """Only structural JSON constraints go to Gemini; Python owns full validation."""
    schema = model.model_json_schema()
    schema['properties'].pop('usage')
    schema['required'].remove('usage')
    schema.get('$defs', {}).pop('Usage', None)

    def compact(node):
        if isinstance(node, list):
            return [compact(item) for item in node]
        if not isinstance(node, dict):
            return node
        if 'const' in node:
            node = {key: value for key, value in node.items() if key != 'const'} | {'enum': [node['const']]}
        return {key: ({name: compact(value) for name, value in item.items()}
                      if key in ('properties', '$defs') else compact(item))
                for key, item in node.items()
                if key in ('type', 'enum', 'const', 'properties', 'required', 'items', 'anyOf', '$ref', '$defs')}
    return compact(schema)


def retry_delay(exc, attempt: int) -> float:
    response = getattr(exc, 'response', None)
    raw = response.headers.get('Retry-After') if response is not None else None
    try:
        delay = float(raw)
    except (TypeError, ValueError):
        try:
            delay = (parsedate_to_datetime(raw) - datetime.now(timezone.utc)).total_seconds()
        except (TypeError, ValueError, OverflowError):
            delay = 2 ** attempt
    # Refuse a long Retry-After rather than retry earlier than requested.
    return delay if math.isfinite(delay) and 0 <= delay <= 30 else -1


def response_usage(response: types.GenerateContentResponse) -> tuple[int, int] | None:
    usage = response.usage_metadata
    if usage is None:
        return None
    values = (usage.prompt_token_count, usage.candidates_token_count, usage.total_token_count)
    if any(type(value) is not int or value < 0 for value in values):
        return None
    incoming, outgoing, total = values
    thoughts = usage.thoughts_token_count or 0
    # Tools/cached content are not enabled. Unexplained usage stays held for reconciliation.
    has_text = any(part.text for candidate in response.candidates or []
                   for part in (candidate.content.parts or [] if candidate.content else []))
    if incoming <= 0 or (has_text and outgoing <= 0) or thoughts < 0 or total != incoming + outgoing + thoughts:
        return None
    return incoming, outgoing + thoughts


def thinking_config(model: str) -> types.ThinkingConfig:
    # Gemini 3 uses levels; minimal still may produce billable thought tokens.
    # Keep the total output reservation and validate actual usage, including thoughts.
    return (types.ThinkingConfig(thinking_level=types.ThinkingLevel.MINIMAL)
            if model.startswith('gemini-3') else types.ThinkingConfig(thinking_budget=0))


class GeminiAdapter:
    def __init__(self, settings: Settings, *, run_id: str | None = None, max_calls: int | None = None):
        self.settings = settings
        self.budget = Budget(settings)
        if max_calls is not None and (not run_id or not 1 <= max_calls <= 3):
            raise ValueError('A preflight run id and max_calls in 1..3 are required')
        self.run_id, self.max_calls = run_id, max_calls
        self.cache = OrderedDict()

    async def _invoke(self, contents: str, config: types.GenerateContentConfig) -> types.GenerateContentResponse:
        # SDK attempts=1 means one total attempt, not one retry. Never bypass ledger.
        options = types.HttpOptions(timeout=self.settings.llm_timeout_seconds * 1000,
                                    retry_options=types.HttpRetryOptions(attempts=1))
        async with genai.Client(vertexai=False, api_key=self.settings.gemini_api_key.get_secret_value(),
                                http_options=options).aio as client:
            return await client.models.generate_content(model=self.settings.llm_model,
                                                        contents=contents, config=config)

    async def generate(self, *, prompt: str, text: str, output_type: type[Output],
                       corpus_version: str, as_of: datetime, stage: str = 'dev',
                       public: bool = False, max_output_tokens: int = 2400,
                       validate: Callable[[Output], None] | None = None) -> Output:
        if self.settings.app_mode != 'live':
            raise ServiceError('INTERNAL_ERROR', 'Gemini yêu cầu chế độ live tường minh.', status=503)
        if not self.settings.gemini_api_key.get_secret_value():
            raise ServiceError('INTERNAL_ERROR', 'Chưa cấu hình provider phía server.', status=503)
        if not 1 <= max_output_tokens <= 2400 or as_of.utcoffset() is None:
            raise ValueError('Invalid output cap or as_of')
        schema = provider_schema(output_type)
        config = types.GenerateContentConfig(
            system_instruction=prompt, temperature=self.settings.llm_temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type='application/json', response_json_schema=schema,
            thinking_config=thinking_config(self.settings.llm_model),
        )
        identity = dict(model=self.settings.llm_model, prompt_hash=digest(prompt), schema_version='1.0',
                        input_hash=digest(text), corpus_version=corpus_version,
                        as_of=as_of.astimezone(timezone.utc).isoformat(),
                        config_hash=digest(config.model_dump(mode='json')), schema_hash=digest(output_type.model_json_schema()))
        cache_key = digest(identity)
        started = time.monotonic()
        for key, (expires, _) in list(self.cache.items()):
            if expires <= started:
                del self.cache[key]
        if public and cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            result = self.cache[cache_key][1].model_copy(deep=True)
            result.usage = Usage(provider='gemini', model=self.settings.llm_model, input_tokens=0,
                                 output_tokens=0, cost_usd=0, cost_vnd_estimate=0,
                                 attempts=0, cache_hit=True, duration_ms=0)
            if validate:
                validate(result)
            return result
        incoming = outgoing = cost = 0
        unknown = False
        request_id = str(uuid4())
        contents = text
        for attempt in range(1 + self.settings.llm_max_retries):
            # One token per UTF-8 byte plus schema/system overhead is deliberately conservative.
            input_bound = len((contents + prompt + json.dumps(schema)).encode()) + 1024
            if input_bound > 6000:
                raise ServiceError('INPUT_TOO_LARGE', 'Đầu vào vượt trần token bảo thủ.', status=413)
            reserved = self.budget.cost(input_bound, max_output_tokens)
            attempt_id = self.budget.reserve(reserved, stage, identity | {
                'request_id': request_id, 'attempt': attempt + 1,
                'input_bound': input_bound, 'output_cap': max_output_tokens,
                'sdk_version': '3.0.0', 'temperature': self.settings.llm_temperature,
                'thinking_config': config.thinking_config.model_dump(mode='json', exclude_none=True),
                'input_price_usd_per_million': self.settings.llm_input_price_per_million_usd,
                'output_price_usd_per_million': self.settings.llm_output_price_per_million_usd},
                run_id=self.run_id, max_calls=self.max_calls)
            attempt_started = time.monotonic()
            try:
                response = await asyncio.wait_for(self._invoke(contents, config), self.settings.llm_timeout_seconds)
            except BaseException as exc:
                self.budget.finish(attempt_id, outcome='transport_error',
                                   duration_ms=int((time.monotonic() - attempt_started) * 1000))
                logger.info('llm_attempt id=%s outcome=transport_error', attempt_id)
                if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
                    raise
                unknown = True
                timeout = isinstance(exc, (TimeoutError, httpx.TimeoutException, httpx2.TimeoutException))
                code = exc.code if isinstance(exc, errors.APIError) else None
                retryable = timeout or code == 429 or (isinstance(code, int) and 500 <= code <= 599)
                delay = retry_delay(exc, attempt)
                if retryable and attempt < self.settings.llm_max_retries and delay >= 0:
                    await asyncio.sleep(delay)
                    continue
                error_code = 'PROVIDER_TIMEOUT' if timeout else ('RATE_LIMITED' if code == 429 else 'INTERNAL_ERROR')
                raise ServiceError(error_code, 'Lỗi kỹ thuật từ provider; phí cần đối soát.', retryable,
                                   status=503) from None
            tokens = response_usage(response)
            actual = self.budget.cost(*tokens) if tokens is not None else None
            self.budget.finish(attempt_id, outcome='response', actual=actual,
                               input_tokens=tokens[0] if tokens else None,
                               output_tokens=tokens[1] if tokens else None,
                               provider_request_id=response.response_id, model_version=response.model_version,
                               duration_ms=int((time.monotonic() - attempt_started) * 1000))
            logger.info('llm_attempt id=%s state=%s', attempt_id, 'unknown' if actual is None else 'settled')
            if tokens is None:
                raise ServiceError('PROVIDER_BAD_OUTPUT', 'Provider thiếu usage đầy đủ; giữ khoản dự phòng.', status=503)
            if unknown:
                raise ServiceError('PROVIDER_BAD_OUTPUT', 'Usage lần gọi trước chưa rõ; cần đối soát.', status=503)
            incoming += tokens[0]
            outgoing += tokens[1]
            cost += actual
            if actual > reserved or tokens[0] > input_bound or tokens[1] > max_output_tokens:
                raise ServiceError('PROVIDER_BAD_OUTPUT', 'Usage vượt trần đã yêu cầu; dừng để đối soát.', status=503)
            usage = Usage(provider='gemini', model=self.settings.llm_model, input_tokens=incoming,
                          output_tokens=outgoing, cost_usd=cost / SCALE,
                          cost_vnd_estimate=cost / SCALE * self.settings.usd_vnd_planning_rate,
                          attempts=attempt + 1, cache_hit=False, duration_ms=int((time.monotonic() - started) * 1000))
            try:
                candidates = response.candidates or []
                if len(candidates) != 1 or candidates[0].finish_reason != types.FinishReason.STOP:
                    raise ValueError('Incomplete output')
                content = candidates[0].content
                parts = content.parts if content else []
                if not parts or any(part.text is None or part.thought for part in parts):
                    raise ValueError('Missing output')
                data = json.loads(''.join(part.text for part in parts))
                if not isinstance(data, dict) or 'usage' in data:
                    raise ValueError('Provider must not supply usage')
                result = output_type.model_validate(data | {'usage': usage})
                if validate:
                    validate(result)
            except ValueError:
                if attempt < self.settings.llm_max_retries:
                    # Fresh repair instruction, never echo invalid/private provider output.
                    contents = text + '\nReturn complete JSON matching the supplied schema. Correct invalid fields.'
                    continue
                raise ServiceError('PROVIDER_BAD_OUTPUT', 'Provider trả dữ liệu thiếu, bị cắt hoặc sai schema.', status=503) from None
            if public:
                self.cache[cache_key] = (started + self.settings.resource_ttl_hours * 3600, result.model_copy(deep=True))
                while len(self.cache) > 64:
                    self.cache.popitem(last=False)
            return result
        raise AssertionError('Unreachable')
