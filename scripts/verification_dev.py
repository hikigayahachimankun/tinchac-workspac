"""T08 DEV checks. Default is offline; --live is owner-only after D02.

Each live case gets a durable T05 run limit of at most three attempts, including
repair/retry. Six one-claim invocations, no extraction or conclusion rewrite.
"""
import argparse
import asyncio
from datetime import datetime
import json
from pathlib import Path
from uuid import uuid4

from google.genai import types

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.models import (Claim, ExtractionResult, RetrievalBundle, Usage,
                                VerificationOutput, VerdictDraft)
from backend.app.services.corpus import canonical_hash, load_corpus
from backend.app.services.errors import ServiceError
from backend.app.services.evidence import fact_relation, scoped_facts
from backend.app.services.llm import GeminiAdapter, provider_schema, thinking_config
from backend.app.services.normalization import normalize_claim
from backend.app.services.retrieve import Retriever
from backend.app.services.temporal import check_claim
from backend.app.services.verify import PROMPT, context_text, verify_extraction

ROOT = Path(__file__).resolve().parents[1]
LIVE_CASES = ROOT / 'data/dev/verification_live.json'


def zero_usage(provider='fixture', model='fixture-v1'):
    return Usage(provider=provider,model=model,input_tokens=0,output_tokens=0,cost_usd=0,
                 cost_vnd_estimate=0,attempts=0,cache_hit=False,duration_ms=0)


def mock_response(drafts):
    """Synthetic SDK response for offline budget/schema path; never a quality measurement."""
    return types.GenerateContentResponse(candidates=[types.Candidate(finish_reason='STOP',content=types.Content(
        parts=[types.Part(text=json.dumps({'drafts':[d.model_dump(mode='json') for d in drafts]}))]))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=100,candidates_token_count=100,total_token_count=200),
        response_id='offline-mock',model_version='offline-mock')


def mock_draft(claim, bundle):
    matches = scoped_facts(claim,bundle)
    match = next((m for m in matches if fact_relation(claim,m.fact)),None)
    relation = fact_relation(claim,match.fact) if match else None
    return VerdictDraft(claim_id=claim.claim_id,label=('supported' if relation=='supports' else 'contradicted' if relation=='contradicts' else 'insufficient_evidence'),
        reason_codes=['MATCHED'] if relation else ['SOURCE_SILENT'],explanation='Offline scripted draft, not Gemini.',
        evidence=[match.citation(relation)] if match else [],temporal_status='unknown')


async def synthetic_cases():
    rows=[]
    cases=json.loads((ROOT/'data/fixtures/verification/cases.json').read_text())
    for case in cases:
        extraction=ExtractionResult.model_validate(case['extraction'])
        bundles=[RetrievalBundle.model_validate(b) for b in case['bundles']]
        output=VerificationOutput.model_validate(case['output'])
        class Mock:
            async def generate(self, **kwargs):
                kwargs['validate'](output)
                return output
        audit=[]
        result=await verify_extraction(uuid4(),extraction,bundles,llm=Mock(),run_mode='fixture',
            corpus_updated_at=datetime.fromisoformat('2026-11-09T12:00:00Z'),audit=audit)
        v=result.claims[0]
        actual={'label':v.label.value,'reason':v.reason_codes[0].value,'temporal':v.temporal_status.value}
        rows.append({'case_id':case['case_id'],'expected':case['expected'],'actual':actual,
                     'passed':actual==case['expected'],'guard':audit})
    return rows


async def run_public_cases(settings, *, live=False, case_id=None):
    sources,chunks,manifest=load_corpus(settings.corpus_dir)
    retriever=Retriever(sources,chunks,manifest)
    cases=json.loads(LIVE_CASES.read_text())['cases']
    if case_id:
        cases=[c for c in cases if c['case_id']==case_id]
        if not cases:
            raise ValueError('Unknown dev case')
    rows=[]
    for case in cases:
        if case['corpus_version']!=retriever.corpus_version:
            raise ServiceError('CORPUS_UNAVAILABLE','Ca dev không khớp corpus_version bàn giao.')
        claim=normalize_claim(Claim.model_validate(case['claim']))
        stamp=datetime.fromisoformat(case['as_of'])
        bundle=retriever.retrieve_claim(claim,retriever.corpus_version,stamp)
        if case['source_version_id'] not in {h.version_id for h in bundle.hits}:
            raise ServiceError('CORPUS_UNAVAILABLE','Nguồn ca dev không có trong top-k.')
        report=check_claim(claim,bundle,stamp)
        text=context_text([claim],[bundle],[report])
        bound=len((text+PROMPT.read_text()+json.dumps(provider_schema(VerificationOutput))).encode())+1024
        run_id=str(uuid4())
        adapter=GeminiAdapter(settings,run_id=run_id,max_calls=3)
        if not live:
            draft=mock_draft(claim,bundle)
            async def invoke(contents,config):
                return mock_response([draft])
            adapter._invoke=invoke
        extraction=ExtractionResult(claims=[claim],warnings=[] if live else ['OFFLINE MOCK: usage là số giả kiểm ledger, không phải usage tài khoản.'],
                                    usage=zero_usage('gemini',settings.llm_model))
        audit=[]
        try:
            result=await verify_extraction(uuid4(),extraction,[bundle],llm=adapter,
                run_mode='live' if live else 'replay',corpus_updated_at=datetime.fromisoformat(manifest['build_at']),public=False,audit=audit)
        except ServiceError as exc:
            rows.append({'case_id':case['case_id'],'run_id':run_id,'error':exc.detail.code.value,'input_bound':bound})
            # Owner must inspect failed/unknown reservations before continuing.
            break
        v=result.claims[0]
        rows.append({'case_id':case['case_id'],'run_id':run_id,'mode':'live' if live else 'offline_mock',
            'source_version_id':case['source_version_id'],'source_url':case['source_url'],
            'shared_bundle':[(h.chunk_id,h.version_id) for h in bundle.hits], 'input_bound':bound,
            'label':v.label.value,'reasons':[r.value for r in v.reason_codes], 'temporal_status':v.temporal_status.value,
            'guard':audit,'usage':result.usage.model_dump(mode='json')})
    return rows


async def run(settings, *, live=False, case_id=None):
    if live and (settings.app_mode!='live' or not settings.gemini_api_key.get_secret_value()):
        print('Owner live run requires D02 verified, APP_MODE=live and a server-side key.')
        return 2
    initialize(settings.database_path)
    synthetic=[] if live else await synthetic_cases()
    rows=await run_public_cases(settings,live=live,case_id=case_id)
    report={'mode':'live' if live else 'offline_mock','prompt_sha256':canonical_hash(PROMPT.read_text()),
            'model_candidate':settings.llm_model,'temperature':settings.llm_temperature,'thinking_config':thinking_config(settings.llm_model).model_dump(mode='json', exclude_none=True),
            'output_cap_per_claim':1200,'synthetic_dev':synthetic,'public_dev':rows,
            'live_calls':None if live else 0,'note':'Mock ledger/token amounts are synthetic. D02/live remain owner verified.'}
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return int(any('error' in row for row in rows) or any(not c['passed'] for c in synthetic))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true',help='Owner only, after D02; uses durable T05 dev budget')
    parser.add_argument('--case',choices=[f'live{i:02d}' for i in range(1,7)])
    args=parser.parse_args()
    try:
        if args.live:
            settings=Settings(_env_file=None)
        else:
            # Ignore all process provider secrets. A fresh local mock ledger never spends account money.
            import tempfile
            with tempfile.TemporaryDirectory(prefix='tinchac-t08-mock-') as directory:
                settings=Settings(_env_file=None,app_mode='live',gemini_api_key='offline-mock-key',
                                  database_path=Path(directory)/'ledger.db')
                return asyncio.run(run(settings,case_id=args.case))
        return asyncio.run(run(settings,live=True,case_id=args.case))
    except Exception:
        print('Verification dev stopped. Check snapshot/config/ledger locally; raw exceptions are not printed.')
        return 2


if __name__=='__main__':
    raise SystemExit(main())
