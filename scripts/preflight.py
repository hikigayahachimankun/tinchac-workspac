"""Owner-run only: python -m scripts.preflight --model-check --max-calls 3.

No model-list/count-token requests: all paid attempts, including repair/retry,
share the same durable run limit. Samples are public approved T02 source facts.
"""
import argparse
import asyncio
import json
from pathlib import Path
from uuid import uuid4

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.models import CheckCreate, SourceVersion
from backend.app.services.errors import ServiceError
from backend.app.services.extract import extract_claims
from backend.app.services.llm import GeminiAdapter, digest

ROOT = Path(__file__).resolve().parents[1]


def public_samples():
    sources = [SourceVersion.model_validate(item) for item in
               json.loads((ROOT / 'data/corpus/sources.json').read_text())]
    approved = [source for source in sources if source.review_status == 'approved' and source.facts
                and not source.is_fixture]
    if len(approved) < 3:
        raise ValueError('Need three approved public seed sources')
    return [(source.title + '\n' + source.facts[0].quote, source.available_at) for source in approved[:3]]


async def run(settings: Settings, max_calls: int) -> int:
    if settings.app_mode != 'live' or not settings.gemini_api_key.get_secret_value():
        print('Preflight requires APP_MODE=live and a server-side key in the owner environment.')
        return 2
    samples = public_samples()
    initialize(settings.database_path)
    run_id = str(uuid4())
    adapter = GeminiAdapter(settings, run_id=run_id, max_calls=max_calls)
    print(json.dumps({'run_id': run_id, 'model': settings.llm_model, 'sdk': '3.0.0',
                      'temperature': settings.llm_temperature, 'thinking_budget': 0,
                      'max_output_tokens': 2400, 'max_calls_including_retry': max_calls,
                      'input_price_usd_per_million': settings.llm_input_price_per_million_usd,
                      'output_price_usd_per_million': settings.llm_output_price_per_million_usd}))
    corpus_version = 'preflight-' + digest([(text, stamp.isoformat()) for text, stamp in samples])
    for text, as_of in samples[:max_calls]:
        request = CheckCreate(schema_version='1.0', input_mode='text', confirmed_text=text,
                              asset_id=None, asset_token=None, as_of=as_of, consent_to_process=True)
        try:
            result = await extract_claims(request, llm=adapter, corpus_version=corpus_version,
                                          public=False)
        except ServiceError as exc:
            print(json.dumps({'run_id': run_id, 'error': exc.detail.model_dump(mode='json')}))
            return 1
        print(json.dumps({'run_id': run_id, 'claims': len(result.claims),
                          'usage': result.usage.model_dump(mode='json')}))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-check', required=True, action='store_true')
    parser.add_argument('--max-calls', type=int, choices=(1, 2, 3), default=3)
    args = parser.parse_args()
    try:
        # Key only comes from the owner's process; do not load a workspace .env.
        return asyncio.run(run(Settings(_env_file=None), args.max_calls))
    except Exception:
        # Provider/validation exception strings may contain private input or credentials.
        print('Preflight failed locally. Review configuration and ledger; no raw exception is printed.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
