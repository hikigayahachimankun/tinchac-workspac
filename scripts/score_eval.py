"""Offline scoring, separated from inference so gold is never sent to a provider."""
import argparse
import json
from pathlib import Path
from eval.harness import digest, read_jsonl, schedule, temporal_subset
from eval.metrics import score
from eval.run_schema import EvidenceScore
from eval.schema import EvalCase, GoldRecord


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',required=True,help='Run directory containing manifest/cases/runs')
    p.add_argument('--gold',required=True,help='Owner-local gold JSONL; never used by run_eval')
    p.add_argument('--evidence',help='Human EvidenceScore JSONL; absent means ECV N/A')
    p.add_argument('--output',required=True)
    p.add_argument('--usd-vnd-rate',type=float,default=27000)
    args=p.parse_args()
    directory=Path(args.run)
    manifest=json.loads((directory/'manifest.json').read_text())
    cases=read_jsonl(directory/'cases.jsonl',EvalCase)
    if digest([c.model_dump(mode='json') for c in cases]) != manifest['cases_hash']:
        raise ValueError('Cases hash drift')
    if digest(manifest['config']) != manifest['config_hash']:
        raise ValueError('Config hash drift')
    temporal_subset(cases, expected=manifest['temporal_case_ids'])
    if manifest['schedule'] != [[c.case_id,s] for c,s in schedule(cases,set(manifest['temporal_case_ids']))]:
        raise ValueError('Schedule drift')
    envelopes=read_jsonl(directory/'runs.jsonl')
    for env in envelopes:
        r=env['row']
        if r['config_hash'] != manifest['config_hash'] or r['prompt_hash'] != manifest['prompts'][r['system']]:
            raise ValueError('Row configuration or prompt drift')
        if r['model'] != manifest['config']['model']:
            raise ValueError('Row model drift')
        if r['run_id'] != manifest['batch_id']+':'+r['system']:
            raise ValueError('Foreign batch')
        if env['mode'] != manifest['mode']:
            raise ValueError('Mode differs from manifest')
        expected_cache = 'replay' if env['mode'] == 'replay' else 'fresh'
        if r['cache_mode'] != expected_cache:
            raise ValueError('Cache mode differs from manifest')
        if env['mode'] == 'fresh' and r['corpus_version'] != manifest['config']['data']['corpus_version']:
            raise ValueError('Row corpus differs from frozen config')
    systems=['A','B','C']+(['C_NO_TIME'] if manifest['temporal_case_ids'] else [])
    result=score(cases,read_jsonl(args.gold,GoldRecord),envelopes,
        read_jsonl(args.evidence,EvidenceScore) if args.evidence else [],
        temporal_ids=manifest['temporal_case_ids'],systems=systems,rate=args.usd_vnd_rate)
    result['completion']={'planned':len(manifest['schedule']),'written':len(envelopes),
        'complete':len(envelopes)==len(manifest['schedule'])}
    result['provenance']={name:digest(Path(path).read_text()) for name,path in
        [('manifest',directory/'manifest.json'),('runs',directory/'runs.jsonl'),('gold',args.gold)]}
    if args.evidence:
        result['provenance']['evidence']=digest(Path(args.evidence).read_text())
    with Path(args.output).open('x') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    print(f'Offline metrics written to {args.output}')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
