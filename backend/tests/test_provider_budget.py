import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from threading import Barrier
from unittest.mock import AsyncMock

from google.genai import errors, types
import httpx
import pytest

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.models import CheckCreate, ExtractionResult
from backend.app.services.budget import Budget, units
from backend.app.services.errors import ServiceError
from backend.app.services.extract import extract_claims, PROMPT
from backend.app.services.llm import GeminiAdapter, provider_schema
from scripts import preflight

ROOT = Path(__file__).resolve().parents[2]
PAYLOAD = json.loads((ROOT / 'contracts/examples/ExtractionResult.json').read_text())
PAYLOAD.pop('usage')
REQUEST = json.loads((ROOT / 'contracts/examples/check_create.json').read_text())


def response(payload=None, *, finish='STOP', usage=True, thoughts=0, **kwargs):
    return types.GenerateContentResponse(
        candidates=[types.Candidate(finish_reason=finish, content=types.Content(
            parts=[types.Part(text=json.dumps(PAYLOAD if payload is None else payload))]))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(
            prompt_token_count=100, candidates_token_count=40, thoughts_token_count=thoughts,
            total_token_count=140 + thoughts) if usage else None,
        response_id='provider-request-1', model_version='mock-version', **kwargs)


@pytest.fixture
def adapter(tmp_path):
    settings = Settings(_env_file=None, app_mode='live', gemini_api_key='mock-key-never-real',
                        database_path=tmp_path / 'budget.sqlite3')
    initialize(settings.database_path)
    return GeminiAdapter(settings)


def rows(adapter):
    with adapter.budget.db() as db:
        return [dict(row) for row in db.execute('SELECT * FROM llm_attempts ORDER BY rowid')]


def request():
    return CheckCreate.model_validate(deepcopy(REQUEST))


def call(adapter, **kwargs):
    return extract_claims(request(), llm=adapter, corpus_version='corpus-v1', **kwargs)


def run(awaitable):
    return asyncio.run(awaitable)


def test_success_full_validation_usage_and_metadata(adapter):
    adapter._invoke = AsyncMock(return_value=response(thoughts=7))
    result = run(call(adapter))
    assert isinstance(result, ExtractionResult)
    assert result.usage.output_tokens == 47 and result.usage.attempts == 1
    row = rows(adapter)[0]
    assert row['state'] == 'settled' and row['actual_nusd'] == adapter.budget.cost(100, 47)
    assert row['provider_request_id'] == 'provider-request-1' and row['model_version'] == 'mock-version'
    assert row['input_tokens'] == 100 and row['output_tokens'] == 47
    metadata = json.loads(row['metadata'])
    assert {'model','prompt_hash','schema_version','input_hash','corpus_version','as_of'} <= metadata.keys()
    assert REQUEST['confirmed_text'] not in row['metadata']
    assert 'mock-key-never-real' not in json.dumps(row)
    config = adapter._invoke.call_args.args[1]
    assert config.response_mime_type == 'application/json'
    assert config.max_output_tokens == 2400 and config.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL and config.candidate_count is None
    assert 'usage' not in config.response_json_schema['properties']
    assert 'additionalProperties' not in json.dumps(provider_schema(ExtractionResult))


def test_budget_exhausted_does_not_call_provider(adapter):
    adapter.settings.llm_budget_usd = 0
    adapter._invoke = AsyncMock(return_value=response())
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'BUDGET_EXCEEDED'
    adapter._invoke.assert_not_awaited()
    assert rows(adapter) == []


def test_stage_and_total_caps_across_restart(adapter):
    budget = adapter.budget
    budget.reserve(units('.8'), 'dev', {})
    with pytest.raises(ServiceError):
        Budget(adapter.settings).reserve(1, 'dev', {})
    budget.reserve(units('1.4'), 'evaluation', {})
    budget.reserve(units('.8'), 'demo', {})
    assert sum(row['charged_nusd'] for row in rows(adapter)) == units('3')
    with pytest.raises(ServiceError):
        budget.reserve(1, 'demo', {})
    # Lowered global limit applies even with stage headroom in an existing ledger.
    adapter.settings.llm_budget_usd = .5
    with pytest.raises(ServiceError):
        budget.reserve(1, 'evaluation', {})


def test_transaction_race_separate_connections(adapter):
    adapter.settings.llm_budget_usd = .01
    barrier = Barrier(2)

    def reserve():
        budget = Budget(adapter.settings)
        barrier.wait()
        try:
            return budget.reserve(units('.007'), 'dev', {})
        except ServiceError as exc:
            return exc.detail.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))
    assert results.count('BUDGET_EXCEEDED') == 1
    assert len(rows(adapter)) == 1


def test_two_requests_only_one_reaches_provider(adapter):
    adapter.settings.llm_budget_usd = .008

    async def scenario():
        entered = asyncio.Event()
        release = asyncio.Event()

        async def provider(*_):
            entered.set()
            await release.wait()
            return response()
        adapter._invoke = AsyncMock(side_effect=provider)
        other = GeminiAdapter(adapter.settings)
        other._invoke = adapter._invoke
        first = asyncio.create_task(call(adapter))
        await entered.wait()
        try:
            with pytest.raises(ServiceError) as caught:
                await call(other)
            assert caught.value.detail.code == 'BUDGET_EXCEEDED'
        finally:
            release.set()
        await first
        adapter._invoke.assert_awaited_once()
    run(scenario())


@pytest.mark.parametrize('failure,code', [
    (TimeoutError('mock-key-never-real private text'), 'PROVIDER_TIMEOUT'),
    (errors.ClientError(429, {'error': {'message': 'mock-key-never-real'}}), 'RATE_LIMITED'),
    (errors.ServerError(503, {'error': {'message': 'private text'}}), 'INTERNAL_ERROR'),
])
def test_finite_transport_retry_keeps_reservations(adapter, monkeypatch, caplog, failure, code):
    monkeypatch.setattr('backend.app.services.llm.asyncio.sleep', AsyncMock())
    adapter._invoke = AsyncMock(side_effect=failure)
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == code
    assert adapter._invoke.await_count == 2
    assert all(row['state'] == 'unknown' and row['actual_nusd'] is None
               and row['charged_nusd'] == row['reserved_nusd'] for row in rows(adapter))
    assert 'mock-key-never-real' not in str(caught.value.detail) + caplog.text
    assert 'private text' not in str(caught.value.detail) + caplog.text


def test_real_deadline_cancels_attempt_and_holds(adapter):
    adapter.settings.llm_timeout_seconds = 1
    adapter.settings.llm_max_retries = 0
    canceled = []

    async def slow(*_):
        try:
            await asyncio.Event().wait()
        finally:
            canceled.append(True)
    adapter._invoke = AsyncMock(side_effect=slow)
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'PROVIDER_TIMEOUT' and canceled == [True]
    assert rows(adapter)[0]['state'] == 'unknown'


def test_retry_reserves_again_and_can_be_blocked(adapter, monkeypatch):
    adapter.settings.llm_budget_usd = .008
    monkeypatch.setattr('backend.app.services.llm.asyncio.sleep', AsyncMock())
    adapter._invoke = AsyncMock(side_effect=TimeoutError())
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'BUDGET_EXCEEDED'
    adapter._invoke.assert_awaited_once()
    assert len(rows(adapter)) == 1 and rows(adapter)[0]['state'] == 'unknown'


def test_success_after_timeout_does_not_invent_usage(adapter, monkeypatch):
    monkeypatch.setattr('backend.app.services.llm.asyncio.sleep', AsyncMock())
    adapter._invoke = AsyncMock(side_effect=[TimeoutError(), response()])
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'PROVIDER_BAD_OUTPUT'
    assert [row['state'] for row in rows(adapter)] == ['unknown', 'settled']


@pytest.mark.parametrize('bad', [
    'json', 'empty', 'missing', 'truncated', 'schema', 'duplicate', 'span', 'too_many', 'usage_field', 'blocked',
])
def test_bad_output_bounded_repair(adapter, bad):
    payload = deepcopy(PAYLOAD)
    answer = response(payload)
    if bad == 'json':
        answer.candidates[0].content.parts[0].text = '{broken'
    elif bad == 'empty':
        answer.candidates = []
    elif bad == 'missing':
        del payload['claims'][0]['scope']
        answer = response(payload)
    elif bad == 'truncated':
        answer = response(finish='MAX_TOKENS')
    elif bad == 'blocked':
        answer = response(finish='SAFETY')
    elif bad == 'schema':
        payload['claims'][0]['normalized']['money']['amount'] = -1
        answer = response(payload)
    elif bad == 'duplicate':
        payload['claims'] *= 2
        answer = response(payload)
    elif bad == 'too_many':
        payload['claims'] = [payload['claims'][0] | {'claim_id': str(i)} for i in range(9)]
        answer = response(payload)
    elif bad == 'usage_field':
        payload['usage'] = {}
        answer = response(payload)
    elif bad == 'span':
        payload['claims'][0]['input_span'] = {'start': 0, 'end': 5}
        answer = response(payload)
    adapter._invoke = AsyncMock(return_value=answer)
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'PROVIDER_BAD_OUTPUT'
    assert adapter._invoke.await_count == 2 and len(rows(adapter)) == 2
    assert all(row['state'] == 'settled' for row in rows(adapter))


def test_schema_repair_aggregates_usage(adapter):
    adapter._invoke = AsyncMock(side_effect=[response({}), response()])
    result = run(call(adapter))
    assert result.usage.input_tokens == 200 and result.usage.attempts == 2
    assert result.usage.cost_usd == sum(row['actual_nusd'] for row in rows(adapter)) / 1e9


@pytest.mark.parametrize('missing', ['all', 'input', 'output', 'total', 'unexplained'])
def test_missing_usage_stays_held_no_zero_or_repair(adapter, missing):
    answer = response(usage=missing != 'all')
    if missing == 'input': answer.usage_metadata.prompt_token_count = None
    if missing == 'output': answer.usage_metadata.candidates_token_count = None
    if missing == 'total': answer.usage_metadata.total_token_count = None
    if missing == 'unexplained': answer.usage_metadata.total_token_count += 1
    adapter._invoke = AsyncMock(return_value=answer)
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'PROVIDER_BAD_OUTPUT'
    adapter._invoke.assert_awaited_once()
    row = rows(adapter)[0]
    assert row['state'] == 'unknown' and row['actual_nusd'] is None and row['input_tokens'] is None
    assert row['charged_nusd'] > 0


def test_redaction_and_spans(adapter):
    body = request()
    body.confirmed_text += ' Email: user@example.com; SĐT: 0912345678; STK: 12345678.'
    payload = deepcopy(PAYLOAD)
    payload['claims'][0]['input_span'] = {'start': 0, 'end': 5}
    adapter._invoke = AsyncMock(return_value=response(payload))
    result = run(extract_claims(body, llm=adapter, corpus_version='c'))
    sent = adapter._invoke.call_args.args[0]
    assert all(secret not in sent for secret in ['user@example.com', '0912345678', '12345678'])
    assert result.claims[0].input_span is None and adapter.cache == {}


def test_private_not_cached_and_public_hit_is_copy_with_zero_new_usage(adapter):
    adapter._invoke = AsyncMock(return_value=response())
    run(call(adapter))
    run(call(adapter))
    assert adapter._invoke.await_count == 2 and not adapter.cache
    original = run(call(adapter, public=True))
    hit = run(call(adapter, public=True))
    assert adapter._invoke.await_count == 3
    assert hit.usage.cache_hit and hit.usage.attempts == 0 and hit.usage.cost_usd == 0
    hit.claims.clear()
    assert len(run(call(adapter, public=True)).claims) == len(original.claims)


@pytest.mark.parametrize('field', ['model', 'prompt', 'schema', 'input', 'corpus', 'as_of', 'temperature', 'cap'])
def test_cache_identity(adapter, field):
    adapter._invoke = AsyncMock(return_value=response())
    args = dict(prompt=PROMPT.read_text(), text=request().confirmed_text, output_type=ExtractionResult,
                corpus_version='c', as_of=request().as_of, public=True)
    run(adapter.generate(**args))
    if field == 'model': adapter.settings.llm_model += '-other'
    if field == 'prompt': args['prompt'] += ' more'
    if field == 'schema':
        class OtherExtraction(ExtractionResult):
            pass
        args['output_type'] = OtherExtraction
    if field == 'input': args['text'] += ' more'
    if field == 'corpus': args['corpus_version'] = 'other'
    if field == 'as_of': args['as_of'] += timedelta(seconds=1)
    if field == 'temperature': adapter.settings.llm_temperature = .1
    if field == 'cap': args['max_output_tokens'] = 1200
    run(adapter.generate(**args))
    assert adapter._invoke.await_count == 2


def test_cache_expiry(adapter, monkeypatch):
    adapter._invoke = AsyncMock(return_value=response())
    run(call(adapter, public=True))
    monkeypatch.setattr('backend.app.services.llm.time.monotonic', lambda: 10**15)
    run(call(adapter, public=True))
    assert adapter._invoke.await_count == 2


def test_no_claim_is_domain_error_and_fixture_mode_cannot_call(adapter):
    adapter._invoke = AsyncMock(return_value=response({'claims': [], 'warnings': []}))
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'NO_CHECKABLE_CLAIM'
    adapter.settings.app_mode = 'fixture'
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'INTERNAL_ERROR'
    assert adapter._invoke.await_count == 1


def test_preflight_total_attempt_limit_includes_retry(adapter, monkeypatch):
    monkeypatch.setattr('backend.app.services.llm.asyncio.sleep', AsyncMock())
    limited = GeminiAdapter(adapter.settings, run_id='test-preflight', max_calls=3)
    limited._invoke = AsyncMock(side_effect=[response({}), response(), response(), response()])
    assert run(call(limited)).usage.attempts == 2
    run(call(limited))
    with pytest.raises(ServiceError) as caught:
        run(call(limited))
    assert caught.value.detail.code == 'BUDGET_EXCEEDED'
    assert limited._invoke.await_count == 3
    restarted = GeminiAdapter(adapter.settings, run_id='test-preflight', max_calls=3)
    restarted._invoke = AsyncMock()
    with pytest.raises(ServiceError):
        run(call(restarted))
    restarted._invoke.assert_not_awaited()


def test_preflight_mock_full_run(adapter, monkeypatch, capsys):
    provider = AsyncMock(return_value=response())
    monkeypatch.setattr(GeminiAdapter, '_invoke', provider)
    assert run(preflight.run(adapter.settings, 3)) == 0
    assert provider.await_count == 3 and len(rows(adapter)) == 3
    assert 'mock-key-never-real' not in capsys.readouterr().out


def test_sdk_wire_no_hidden_retry(adapter, monkeypatch):
    from google import genai
    real_client = genai.Client
    requests = []

    def handler(req):
        requests.append(req)
        return httpx.Response(429, json={'error': {'code': 429, 'message': 'secret-provider-error'}})

    def factory(**kwargs):
        assert kwargs['http_options'].retry_options.attempts == 1
        assert kwargs['http_options'].timeout == 30000
        kwargs['http_options'].httpx_async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return real_client(**kwargs)
    monkeypatch.setattr('backend.app.services.llm.genai.Client', factory)
    monkeypatch.setattr('backend.app.services.llm.asyncio.sleep', AsyncMock())
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'RATE_LIMITED'
    assert len(requests) == len(rows(adapter)) == 2
    wire = json.loads(requests[0].content)
    assert wire['generationConfig']['responseMimeType'] == 'application/json'
    assert 'responseJsonSchema' in wire['generationConfig']


def test_zero_usage_for_nonempty_output_is_unknown(adapter):
    answer = response()
    answer.usage_metadata = types.GenerateContentResponseUsageMetadata(
        prompt_token_count=0, candidates_token_count=0, total_token_count=0)
    adapter._invoke = AsyncMock(return_value=answer)
    with pytest.raises(ServiceError):
        run(call(adapter))
    assert rows(adapter)[0]['state'] == 'unknown'
    assert rows(adapter)[0]['charged_nusd'] > 0


def test_retry_after_and_no_retry_for_400(adapter, monkeypatch):
    sleeper = AsyncMock()
    monkeypatch.setattr('backend.app.services.llm.asyncio.sleep', sleeper)
    first = errors.ClientError(429, {'error': {'message': 'limited'}},
                               httpx.Response(429, headers={'Retry-After': '7'}))
    adapter._invoke = AsyncMock(side_effect=first)
    with pytest.raises(ServiceError):
        run(call(adapter))
    sleeper.assert_awaited_once_with(7)
    adapter._invoke = AsyncMock(side_effect=errors.ClientError(400, {'error': {'message': 'bad config'}}))
    with pytest.raises(ServiceError):
        run(call(adapter))
    adapter._invoke.assert_awaited_once()


def test_long_retry_after_does_not_retry_early(adapter, monkeypatch):
    sleeper = AsyncMock()
    monkeypatch.setattr('backend.app.services.llm.asyncio.sleep', sleeper)
    adapter._invoke = AsyncMock(side_effect=errors.ClientError(429, {'error': {'message': 'limited'}},
                                httpx.Response(429, headers={'Retry-After': '120'})))
    with pytest.raises(ServiceError):
        run(call(adapter))
    adapter._invoke.assert_awaited_once()
    sleeper.assert_not_awaited()


def test_provider_error_reaches_job_as_technical_failure(adapter):
    from backend.app.services.jobs import Jobs
    jobs = Jobs(adapter.settings.model_copy(update={'app_mode': 'fixture'}))
    jobs.initialize()
    adapter.settings.llm_max_retries = 0
    adapter._invoke = AsyncMock(side_effect=TimeoutError())

    class ExtractionBoundary:
        def build_result(self, check_id, body):
            return run(extract_claims(body, llm=adapter, corpus_version='c'))
    jobs.adapter = ExtractionBoundary()
    created = jobs.create(request())
    jobs.run(str(created.check.check_id))
    record = jobs.get(str(created.check.check_id), created.access_token)
    assert record.status == 'failed' and record.result is None
    assert record.error.code == 'PROVIDER_TIMEOUT'
    adapter._invoke.assert_awaited_once()


def test_cancel_keeps_reservation_and_sdk_not_called_for_oversize(adapter):
    adapter._invoke = AsyncMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        run(call(adapter))
    assert rows(adapter)[0]['state'] == 'unknown'
    adapter._invoke.reset_mock()
    with pytest.raises(ServiceError) as caught:
        run(adapter.generate(prompt=PROMPT.read_text(), text='x' * 6000, output_type=ExtractionResult,
                             corpus_version='c', as_of=request().as_of))
    assert caught.value.detail.code == 'INPUT_TOO_LARGE'
    adapter._invoke.assert_not_awaited()


def test_usage_over_output_cap_is_technical_error(adapter):
    answer = response(thoughts=2401)
    adapter._invoke = AsyncMock(return_value=answer)
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'PROVIDER_BAD_OUTPUT'
    assert rows(adapter)[0]['output_tokens'] == 2441
    adapter._invoke.assert_awaited_once()


def test_budget_gate_prevents_sdk_client_creation(adapter, monkeypatch):
    from unittest.mock import Mock
    client = Mock(side_effect=AssertionError('SDK client must not be created'))
    monkeypatch.setattr('backend.app.services.llm.genai.Client', client)
    adapter.settings.llm_budget_usd = 0
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'BUDGET_EXCEEDED'
    client.assert_not_called()


def test_sdk_success_wire_and_no_transaction_during_io(adapter, monkeypatch):
    from google import genai
    real_client = genai.Client
    seen = []

    def handler(req):
        wire = json.loads(req.content)
        seen.append(wire)
        assert rows(adapter)[0]['state'] == 'reserved'
        with adapter.budget.db() as db:
            db.execute('BEGIN IMMEDIATE')  # A provider call must never hold this write lock.
        return httpx.Response(200, json=response().model_dump(mode='json', by_alias=True, exclude_none=True))

    def factory(**kwargs):
        assert kwargs['vertexai'] is False
        kwargs['http_options'].httpx_async_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        return real_client(**kwargs)
    monkeypatch.setattr('backend.app.services.llm.genai.Client', factory)
    result = run(call(adapter))
    assert result.usage.input_tokens == 100 and len(seen) == 1
    schema = seen[0]['generationConfig']['responseJsonSchema']
    assert schema['$defs']['MoneyValue']['properties']['currency']['enum'] == ['VND']
    assert 'usage' not in schema['properties']


def test_preflight_retry_shares_three_attempt_ceiling(adapter, monkeypatch):
    provider = AsyncMock(side_effect=[response({}), response(), response(), response()])
    monkeypatch.setattr(GeminiAdapter, '_invoke', provider)
    assert run(preflight.run(adapter.settings, 3)) == 1
    assert provider.await_count == len(rows(adapter)) == 3


def test_missing_key_does_not_create_attempt(adapter):
    from pydantic import SecretStr
    adapter.settings.gemini_api_key = SecretStr('')
    adapter._invoke = AsyncMock()
    with pytest.raises(ServiceError) as caught:
        run(call(adapter))
    assert caught.value.detail.code == 'INTERNAL_ERROR'
    assert rows(adapter) == []
    adapter._invoke.assert_not_awaited()


def test_thinking_configuration_uses_model_family_without_disabling_accounting():
    from backend.app.services.llm import thinking_config
    assert thinking_config('gemini-3.5-flash-lite').thinking_level == types.ThinkingLevel.MINIMAL
    assert thinking_config('gemini-3.5-flash-lite').thinking_budget is None
    assert thinking_config('gemini-2.5-flash-lite').thinking_budget == 0
