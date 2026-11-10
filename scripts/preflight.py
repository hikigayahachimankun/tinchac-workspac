"""Owner-run only: python -m scripts.preflight --model-check --max-calls 3.

No model-list/count-token requests: all paid attempts, including repair/retry,
share the same durable run limit. Samples are public approved T02 source facts.
"""
import argparse
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.models import CheckCreate, SourceVersion
from backend.app.services.errors import ServiceError
from backend.app.services.extract import extract_claims
from backend.app.services.llm import GeminiAdapter, digest, thinking_config

ROOT = Path(__file__).resolve().parents[1]
AUTHORIZED_RUN_ID = 'tinchac-preflight-2026-11-10-cap-0p03usd'


def account_ready(path: Path | None, model: str) -> bool:
    """Operator's genuine account-read receipt; never infer readiness from a key or model GET."""
    if path is None:
        return False
    try:
        receipt = json.loads(path.read_text())
        checked = datetime.fromisoformat(receipt['checked_at'])
        if checked.utcoffset() is None:
            return False
        age = (datetime.now(timezone.utc) - checked).total_seconds()
        return (0 <= age <= 86400 and receipt['model'] == model
                and receipt.get('billing_verified') is True and receipt.get('quota_verified') is True
                and receipt.get('preflight_status') == 'ready')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return False


def public_samples():
    sources = [SourceVersion.model_validate(item) for item in
               json.loads((ROOT / 'data/corpus/sources.json').read_text())]
    approved = [source for source in sources if source.review_status == 'approved' and source.facts
                and not source.is_fixture]
    if len(approved) < 3:
        raise ValueError('Need three approved public seed sources')
    return [(source.title + '\n' + source.facts[0].quote, source.available_at) for source in approved[:3]]


async def run(settings: Settings, max_calls: int, *, run_id=AUTHORIZED_RUN_ID,
              max_cost_usd=Decimal('.03')) -> int:
    if settings.app_mode != 'live' or not settings.gemini_api_key.get_secret_value():
        print('Preflight requires APP_MODE=live and a server-side key in the owner environment.')
        return 2
    samples = public_samples()
    initialize(settings.database_path)
    adapter = GeminiAdapter(settings, run_id=run_id, max_calls=max_calls, run_budget_usd=max_cost_usd)
    print(json.dumps({'run_id': run_id, 'model': settings.llm_model, 'sdk': '3.0.0',
                      'temperature': settings.llm_temperature,
                      'thinking_config': thinking_config(settings.llm_model).model_dump(mode='json', exclude_none=True),
                      'max_output_tokens': 2400, 'max_calls_including_retry': max_calls,
                      'max_run_cost_usd': str(max_cost_usd),
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
    parser.add_argument('--max-cost-usd', type=Decimal, default=Decimal('.03'))
    parser.add_argument('--run-id', default=AUTHORIZED_RUN_ID, help='Stable authorization ID; changing it requires new spending authorization')
    parser.add_argument('--secret-file',type=Path,help='Owner-only outside-repo env file; loaded as data, never sourced')
    parser.add_argument('--readiness-report',type=Path,help='Fresh genuine authenticated account/billing/quota receipt; metadata-only reports block generation')
    args = parser.parse_args()
    try:
        # Key only comes from the owner's process; do not load a workspace .env.
        settings = Settings(_env_file=None)
        if not account_ready(args.readiness_report, settings.llm_model):
            print('Preflight blocked: authenticated account billing/quota verification is missing or stale. No generation attempted.')
            return 2
        if args.secret_file:
            from scripts.provider_check import load_key
            settings.gemini_api_key = load_key(args.secret_file)
        return asyncio.run(run(settings, args.max_calls, run_id=args.run_id, max_cost_usd=args.max_cost_usd))
    except Exception:
        # Provider/validation exception strings may contain private input or credentials.
        print('Preflight failed locally. Review configuration and ledger; no raw exception is printed.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
