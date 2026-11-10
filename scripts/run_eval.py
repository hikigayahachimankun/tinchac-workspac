"""Run inference only (never reads gold). Fixture/replay are explicitly offline."""
import argparse
import asyncio
import json
import time
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from backend.app.models import Claim, RetrievalBundle, VerificationOutput
from eval.harness import (ROOT, PROMPTS, append_jsonl, digest, infer, prepare_claim,
                          read_jsonl, schedule, shared_bundle, zero_usage, prompt_for, temporal_subset)
from eval.schema import EvalCase


def fixture_inputs():
    fixtures = json.loads((ROOT / 'data/fixtures/verification/cases.json').read_text())[:8]
    cases, claims, bundles, outputs = [], {}, {}, {}
    for f in fixtures:
        claim = Claim.model_validate(f['extraction']['claims'][0])
        bundle = RetrievalBundle.model_validate(f['bundles'][0])
        cid = f['case_id']
        cases.append(EvalCase(case_id=cid, family_id=f'fixture-family-{len(cases)//2}', split='dev',
            origin='synthetic_modified', domain='scholarship', input_text=claim.statement,
            target_claim_id=claim.claim_id, target_statement=claim.statement, field_type=claim.field_type,
            as_of=bundle.as_of, modification_type='fixture', input_image_path=None))
        claims[cid], bundles[cid] = claim, bundle
        outputs[cid] = VerificationOutput.model_validate(f['output'])
    return cases, claims, bundles, outputs


def validate_config(config, *, fresh=False):
    fixed = {'schema_version':'1.0', 'seed':42, 'temperature':0,
             'systems':['A','B','C'], 'ablation_system':'C_NO_TIME'}
    if any(config.get(k) != v for k, v in fixed.items()):
        raise ValueError('Unsupported experiment constants')
    if config['retrieval'] != dict(method='fts5_tfidf_rrf', fts_candidates=10, tfidf_candidates=10,
                                    rrf_k=60, top_k=5, max_context_tokens=6000):
        raise ValueError('Retrieval configuration differs from protocol')
    if config['generation'] != dict(max_output_tokens=1200, max_retries=1, timeout_seconds=30):
        raise ValueError('Generation configuration differs from protocol')
    if (config['execution']['concurrency'] != 1 or config['execution']['cache_mode'] != 'fresh'
            or not 0 < config['execution']['total_budget_usd'] <= 1.4):
        raise ValueError('Invalid execution limits')
    if config['analysis'] != dict(primary='family_macro_ecv_delta_c_minus_b', bootstrap_clusters='family_id',
                                bootstrap_replicates=2000, confidence_level=.95):
        raise ValueError('Analysis differs from protocol')
    if fresh and (not config.get('model_verified') or any(
            not config['data'][k] or 'TO_BE' in config['data'][k] for k in ['corpus_version'])):
        raise ValueError('D02 and corpus freeze required before fresh calls')


async def run(args):
    config = json.loads(Path(args.config).read_text())  # JSON is a YAML 1.2 subset, no new dependency.
    validate_config(config, fresh=args.mode == 'fresh')
    cases, claims, bundles, outputs = [], {}, {}, {}
    replay = {}
    adapter = None
    retrieval_errors, retrieval_ms = {}, {}
    if args.mode == 'fixture':
        if args.cases or args.claims:
            raise ValueError('Fixture mode uses only bundled synthetic inputs')
        cases, claims, bundles, outputs = fixture_inputs()
        config['model'] = 'fixture-v1'
        config['data']['corpus_version'] = 'fixture-per-case'
    else:
        if not args.cases:
            raise ValueError('--cases required')
        cases = read_jsonl(args.cases, EvalCase)
        if args.mode == 'fresh':
            if not args.owner_live_public or not args.claims:
                raise ValueError('Owner must verify public inputs and supply frozen Claim sidecar')
            entries = read_jsonl(args.claims)
            claims = {e['case_id']: Claim.model_validate(e['claim']) for e in entries}
            if len(claims) != len(entries) or set(claims) != {c.case_id for c in cases}:
                raise ValueError('Claim sidecar coverage/duplicates')
            claims = {c.case_id:prepare_claim(c, claims[c.case_id]) for c in cases}
            if (config['data'].get('cases_hash') != digest([c.model_dump(mode='json') for c in cases])
                    or config['data'].get('claims_hash') != digest({k:v.model_dump(mode='json') for k,v in claims.items()})
                    or not isinstance(config['data'].get('temporal_case_ids'), list)):
                raise ValueError('Pin public preparation hashes and temporal subset before fresh calls')
            temporal_subset(cases, expected=config['data']['temporal_case_ids'])
            from backend.app.config import Settings
            from backend.app.services.llm import GeminiAdapter
            from backend.app.services.retrieve import Retriever
            settings = Settings(_env_file=None)
            # Do not create/reset durable ledger; owner initializes it and retains it across runs.
            if (settings.app_mode != 'live' or not settings.database_path.exists()
                    or not settings.gemini_api_key.get_secret_value() or settings.llm_model != config['model']
                    or settings.llm_temperature != 0 or settings.llm_timeout_seconds != 30
                    or settings.llm_max_retries != 1 or config['execution']['total_budget_usd'] != 1.4):
                raise ValueError('Fresh requires live settings, durable ledger, common model and fixed budget')
            split_manifest = json.loads(Path(config['data']['split_manifest']).read_text())
            families = {f['family_id']:f for f in split_manifest['families']}
            if any(c.family_id not in families or families[c.family_id]['split'] != c.split for c in cases):
                raise ValueError('Cases differ from split manifest')
            if any(c.split == 'test' for c in cases) and split_manifest['status'] != 'frozen':
                raise ValueError('Test run requires owner-frozen split manifest')
            retriever = Retriever.from_directory(settings.corpus_dir)
            if retriever.corpus_version != config['data']['corpus_version']:
                raise ValueError('Corpus version drift')
            if len(cases) > (12 if cases and cases[0].split == 'dev' else 72):
                raise ValueError('Planned dev/test case cap exceeded')
            for case in cases:
                claims[case.case_id] = prepare_claim(case, claims[case.case_id])
                from backend.app.services.errors import ServiceError
                retrieval_start = time.perf_counter()
                try:
                    bundles[case.case_id] = retriever.retrieve_claim(claims[case.case_id], retriever.corpus_version, case.as_of, k=5)
                except ServiceError as exc:
                    retrieval_errors[case.case_id] = exc
                    bundles[case.case_id] = RetrievalBundle(claim_id=case.target_claim_id,query='',hits=[],
                        corpus_version=retriever.corpus_version,as_of=case.as_of,reason='no_eligible_source')
                retrieval_ms[case.case_id] = (time.perf_counter() - retrieval_start) * 1000
            # max_calls in T05 is a preflight-only (1..3) gate. Harness limits
            # planned invocations; each adapter invocation still allows <=2 attempts.
            adapter = GeminiAdapter(settings, run_id=str(uuid4()))
        else:
            if not args.replay:
                raise ValueError('--replay required')
            source_manifest = json.loads((Path(args.replay).parent/'manifest.json').read_text())
            config = source_manifest['config']
            validate_config(config)
            if digest([c.model_dump(mode='json') for c in cases]) != source_manifest['cases_hash']:
                raise ValueError('Replay input hash differs from source')
            for envelope in read_jsonl(args.replay):
                row = envelope['row']
                from eval.run_schema import EvalRunRow
                EvalRunRow.model_validate(row)
                if row['config_hash'] != source_manifest['config_hash'] or row['prompt_hash'] != source_manifest['prompts'][row['system']]:
                    raise ValueError('Replay config/prompt drift')
                key = (row['case_id'], row['system'])
                if key in replay:
                    raise ValueError('Duplicate replay key')
                replay[key] = envelope
    ids = [c.case_id for c in cases]
    if not cases or len(ids) != len(set(ids)) or len({c.split for c in cases}) != 1:
        raise ValueError('Nonempty unique cases in one split required')
    temporal = temporal_subset(cases)
    order = schedule(cases, set(temporal))
    if args.mode == 'replay' and set(replay) != {(c.case_id,s) for c,s in order}:
        raise ValueError('Replay must cover entire planned schedule exactly')
    directory = Path(args.output)
    directory.mkdir(mode=0o700)  # refuse existing run; never truncate or mix batches
    batch = str(uuid4())
    cfg_hash = digest(config)
    import subprocess
    commit = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
    manifest = {'git_commit':commit, 'batch_id':batch, 'mode':args.mode, 'config':config, 'config_hash':cfg_hash,
        'cases_hash':digest([c.model_dump(mode='json') for c in cases]),
        'claims_hash':digest({k:v.model_dump(mode='json') for k,v in claims.items()}),
        'implementation': {str(p.relative_to(ROOT)):digest(p.read_text()) for p in sorted(list((ROOT/'eval').glob('*.py')) + list((ROOT/'backend/app/services').glob('*.py')) + [ROOT/'scripts/run_eval.py', ROOT/'scripts/score_eval.py', ROOT/'backend/app/models.py'])},
        'prompts':{s:digest(prompt_for(s)) for s,p in PROMPTS.items()},
        'temporal_case_ids':temporal, 'schedule':[[c.case_id,s] for c,s in order],
        'note':'Fixture is scripted plumbing, never model performance. Replay retains source usage separately.'}
    if args.mode == 'fresh':
        manifest['split_manifest_hash'] = digest(split_manifest)
        manifest['provider_ledger_run_id'] = adapter.run_id
    (directory/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (directory/'cases.jsonl').write_text(''.join(c.model_dump_json()+'\n' for c in cases))
    if args.mode == 'replay':
        manifest['origin_manifest_hash'] = digest(source_manifest)
        manifest['prompts'] = source_manifest['prompts']
        (directory/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        (directory/'claims.jsonl').write_text(''.join(json.dumps({'case_id':k,'claim':v.model_dump(mode='json')},ensure_ascii=False)+'\n' for k,v in claims.items()))
    errors = 0
    error_case_ids = set()
    stop = None
    for case, system in order:
        if args.mode == 'replay':
            original = replay[(case.case_id,system)]
            envelope = json.loads(json.dumps(original))
            row = envelope['row']
            envelope['origin'] = {'run_id':row['run_id'], 'usage':row['usage'], 'stage_ms':row['stage_ms']}
            row.update(run_id=f'{batch}:{system}', cache_mode='replay', stage_ms={},
                       usage=zero_usage(row['model'], 'replay').model_dump(mode='json'))
            envelope['mode'] = 'replay'
        else:
            claim = prepare_claim(case, claims[case.case_id])
            bundle = shared_bundle(claim, bundles[case.case_id])
            if args.mode == 'fixture':
                async def generate(**kw):
                    out = outputs[case.case_id].model_copy(deep=True)
                    out.usage = zero_usage()
                    if system == 'A':
                        from backend.app.models import VerdictDraft
                        out.drafts = [VerdictDraft.model_validate(out.drafts[0].model_dump() | {'label':'insufficient_evidence',
                            'evidence':[], 'reason_codes':['NO_SOURCE']})]
                    kw['validate'](out)
                    return out
                adapter = SimpleNamespace(generate=generate)
            active_adapter = adapter
            if system != 'A' and case.case_id in retrieval_errors:
                async def fail_retrieval(**kwargs):
                    raise retrieval_errors[case.case_id]
                active_adapter = SimpleNamespace(generate=fail_retrieval)
            envelope = await infer(case,claim,bundle,system,active_adapter,batch_id=batch,
                                   config_hash=cfg_hash,model=config['model'],mode=args.mode)
        if args.mode == 'fresh' and system != 'A':
            elapsed = retrieval_ms[case.case_id]
            envelope['row']['stage_ms']['retrieval'] = elapsed
            envelope['row']['stage_ms']['total'] += elapsed
        append_jsonl(directory/'runs.jsonl',envelope)
        error = envelope['row']['technical_error']
        errors += error is not None
        if error is not None:
            error_case_ids.add(case.case_id)
        if args.mode == 'fresh' and (error == 'BUDGET_EXCEEDED' or len(error_case_ids)/len(cases) > .1):
            stop = 'budget' if error == 'BUDGET_EXCEEDED' else 'technical_error_cases_over_10pct_planned'
            break
    append_jsonl(directory/'events.jsonl', {'event':'stopped' if stop else 'complete', 'reason':stop,
        'planned':len(order),'written':len(read_jsonl(directory/'runs.jsonl')),'technical_errors':errors,'error_case_ids':sorted(error_case_ids)})
    print(f'{args.mode}: {len(read_jsonl(directory / "runs.jsonl"))}/{len(order)} rows; output={directory}')
    return 2 if stop else 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['fixture','replay','fresh'], default='fixture')
    p.add_argument('--config', default='config/experiments.yaml')
    p.add_argument('--cases')
    p.add_argument('--claims', help='JSONL {case_id,claim}; prepared from public inputs before freeze, never gold')
    p.add_argument('--replay')
    p.add_argument('--owner-live-public', action='store_true', help='R1 only: D02/cost/public-input approval already recorded')
    p.add_argument('--output', required=True, help='New directory; existing path is refused')
    args=p.parse_args()
    try:
        return asyncio.run(run(args))
    except Exception:
        print('Eval stopped: inspect configuration/input/ledger locally. No raw exception or secret printed.')
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
