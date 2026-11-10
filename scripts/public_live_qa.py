"""Public DEV guard replay or twelve-case production HTTP smoke; never a benchmark."""
import argparse
from datetime import datetime
from itertools import combinations
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import create_app
from backend.app.models import Claim, CheckRecord, SourcePublic, VerdictDraft
from backend.app.services.corpus import canonical_hash, load_corpus
from backend.app.services.evidence import validate_verdicts
from backend.app.services.normalization import normalize_claim
from backend.app.services.retrieve import Retriever
from backend.app.services.temporal import check_claim
from scripts.verification_dev import LIVE_CASES

STAMP = '2026-11-10T00:00:00+07:00'


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
        stream.flush()
        import os
        os.fsync(stream.fileno())


def replay(settings, recording):
    sources, chunks, manifest = load_corpus(settings.corpus_dir)
    retriever = Retriever(sources, chunks, manifest)
    cases = {c['case_id']: c for c in json.loads(LIVE_CASES.read_text())['cases']}
    recorded = json.loads(recording.read_text())
    rows = []
    for row in recorded['public_dev']:
        case = cases[row['case_id']]
        if case['corpus_version'] != retriever.corpus_version:
            raise ValueError('Recording corpus mismatch')
        claim = normalize_claim(Claim.model_validate(case['claim']))
        stamp = datetime.fromisoformat(case['as_of'])
        bundle = retriever.retrieve_claim(claim, retriever.corpus_version, stamp)
        if [list(pair) for pair in row['shared_bundle']] != [[h.chunk_id,h.version_id] for h in bundle.hits]:
            raise ValueError('Recording retrieval mismatch')
        audit = []
        result = validate_verdicts([VerdictDraft.model_validate(d) for d in row['raw_public_drafts']],
            [claim], [bundle], [check_claim(claim,bundle,stamp)], audit=audit)
        rows.append({'case_id':row['case_id'], 'original_label':row['label'],
                     'verdict':result[0].model_dump(mode='json'), 'guard':audit})
    return {'mode':'offline_guard_replay', 'model_calls':0, 'recording_hash':canonical_hash(recorded),
            'note':'Recomputed guard only from actual public DEV drafts. Original recording retained. No gold or benchmark metrics.',
            'rows':rows}


def public_pairs(settings):
    """Select twelve field-distinct pairs before calls, round-robin over exposed families."""
    sources, _, manifest = load_corpus(settings.corpus_dir)
    queues = []
    for source in sorted(sources,key=lambda s:s.version_id):
        if source.review_status != 'approved':
            continue
        pairs = [(a,b) for a,b in combinations(source.facts,2) if a.field_type != b.field_type and a.scope == b.scope]
        queues.append((source,pairs))
    cases = []
    while len(cases) < 12 and any(pairs for _,pairs in queues):
        for source,pairs in queues:
            if not pairs or len(cases) == 12:
                continue
            a,b = pairs.pop(0)
            text = f'{source.title}\n{a.quote}\n{b.quote}'
            cases.append({'case_id':f'http{len(cases)+1:02d}', 'family_id':source.family_id,
                'version_id':source.version_id, 'input_text':text,
                'source_fields':[a.field_type.value,b.field_type.value]})
    if len(cases) != 12:
        raise ValueError('Insufficient preselected public two-field pairs')
    return {'mode':'public_dev_http_smoke', 'corpus_version':manifest['corpus_version'],
        'as_of':STAMP, 'cases':cases, 'human_gold':False,
        'code_hashes':{p:canonical_hash(Path(p).read_text()) for p in (
            'prompts/extract.txt','prompts/verify_c.txt','backend/app/services/verify.py',
            'backend/app/services/evidence.py','backend/app/services/llm.py')},
        'note':'Source-derived public DEV across exposed families. Field list describes input, not human-annotated extraction gold.'}


def check_citations(client, result):
    checked = 0
    for claim in result.claims:
        if claim.label in ('supported','contradicted') and not claim.evidence:
            raise ValueError('S/C missing citation')
        for ref in claim.evidence:
            response = client.get('/api/v1/sources/'+ref.version_id)
            if response.status_code != 200:
                raise ValueError('Missing public source')
            source = SourcePublic.model_validate(response.json())
            hits = [c for c in source.chunks if c.chunk_id == ref.chunk_id and c.version_id == ref.version_id]
            if source.is_fixture or len(hits) != 1 or hits[0].text[ref.quote_span.start:ref.quote_span.end] != ref.quote:
                raise ValueError('Invalid emitted citation')
            checked += 1
    return checked


def http_smoke(settings, directory, manifest):
    """No capability tokens in saved artifacts; delete each job even when it fails."""
    completed = []
    with TestClient(create_app(settings)) as client:
        for case in manifest['cases']:
            response = client.post('/api/v1/checks',json={'schema_version':'1.0','input_mode':'text',
                'confirmed_text':case['input_text'],'asset_id':None,'asset_token':None,
                'as_of':manifest['as_of'],'consent_to_process':True})
            if response.status_code != 202:
                write(directory/(case['case_id']+'.json'), {'case_id':case['case_id'], 'http_status':response.status_code,
                    'error':response.json().get('error')})
                break
            created = response.json()
            url = '/api/v1/checks/'+created['check']['check_id']
            headers = {'X-Resource-Token':created['access_token']}
            try:
                record = CheckRecord.model_validate(client.get(url,headers=headers).json())
                row = {'case_id':case['case_id'], 'record':record.model_dump(mode='json')}
                row['checked_citations'] = check_citations(client,record.result) if record.result else 0
                write(directory/(case['case_id']+'.json'),row)
                completed.append(row)
                if record.status != 'completed':
                    break
            finally:
                if client.delete(url,headers=headers).status_code != 204:
                    raise ValueError('Own smoke job cleanup failed')
    successful = sum(r['record']['status']=='completed' for r in completed)
    summary = {'mode':'actual_public_dev_http', 'planned':12, 'recorded':len(completed),'completed':successful,
        'passed_technical_smoke':successful==12, 'human_gold':False, 'benchmark':False,
        'note':'Actual production HTTP extraction/retrieval/verification and source/delete endpoints; no accuracy/effectiveness claim.'}
    write(directory/'summary.json',summary)
    return 0 if successful == 12 else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['replay','http'])
    parser.add_argument('--recording',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--readiness-report',type=Path)
    parser.add_argument('--secret-file',type=Path)
    args = parser.parse_args()
    settings = Settings(_env_file=None)
    if args.mode == 'replay':
        write(args.output,replay(settings,args.recording))
        return 0
    from scripts.preflight import account_mode
    from scripts.provider_check import load_key
    if settings.app_mode != 'live' or account_mode(args.readiness_report,settings.llm_model) != 'free_tier':
        parser.error('HTTP smoke requires live mode and current owner Free Tier authorization')
    # Never resume or overwrite a partial run. Record inputs before provider access.
    manifest = public_pairs(settings)
    args.output.mkdir()
    write(args.output/'manifest.json',manifest)
    settings.llm_billing_mode = 'free_tier'
    settings.llm_live_enabled = True
    settings.gemini_api_key = load_key(args.secret_file)
    return http_smoke(settings,args.output,manifest)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception:
        print('Public DEV QA stopped; inspect saved safe records and ledger. Raw exceptions suppressed.')
        raise SystemExit(2)
