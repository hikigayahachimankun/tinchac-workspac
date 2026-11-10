"""Offline T09 checks. Never runs inference; private inputs are owner-only arguments."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from backend.app.models import check_quote
from backend.app.services.corpus import ROOT, load_corpus
from eval.schema import EvalCase, GoldRecord


def read_jsonl(path, model):
    return [model.model_validate_json(line) for line in path.read_text().splitlines() if line.strip()]


def unique(rows, key):
    values = [getattr(r, key) for r in rows]
    if len(values) != len(set(values)):
        raise ValueError(f'Duplicate {key}')


def validate_manifest(manifest, sources):
    if manifest['status'] == 'frozen':
        raise ValueError('T09 tool does not certify frozen status')
    if manifest['seed'] != 42:
        raise ValueError('Expected seed 42')
    by_version = {s.version_id: s for s in sources}
    families, versions, url_splits = {}, set(), {}
    for f in manifest['families']:
        fid = f['family_id']
        if fid in families or f['split'] not in ('dev', 'test') or f['domain'] not in ('payment', 'scholarship'):
            raise ValueError('Family overlap or invalid domain/split')
        if f['exposed_to_dev'] and f['split'] != 'dev':
            raise ValueError('Dev-exposed family cannot be test')
        if not f['version_ids']:
            raise ValueError('Family has no source')
        families[fid] = f
        for vid in f['version_ids']:
            s = by_version[vid]
            if vid in versions or s.review_status != 'approved' or s.family_id != fid:
                raise ValueError('Version overlap, quarantine or family mismatch')
            versions.add(vid)
            for key in (s.canonical_url, s.content_sha256):
                if key in url_splits and url_splits[key] != f['split']:
                    raise ValueError('Duplicate source crosses split')
                url_splits[key] = f['split']
    if versions != {s.version_id for s in sources if s.review_status == 'approved'}:
        raise ValueError('Approved inventory incomplete')
    for s in sources:
        if s.supersedes_version_id and s.review_status == 'approved':
            old = by_version[s.supersedes_version_id]
            if old.family_id != s.family_id:
                raise ValueError('Supersession crosses family')
    return families


def validate(cases, gold, manifest, sources, chunks, *, require_gold=False):
    families = validate_manifest(manifest, sources)
    if require_gold and not cases:
        raise ValueError('Empty evaluation cannot be complete')
    unique(cases, 'case_id')
    unique(gold, 'case_id')
    by_case = {c.case_id: c for c in cases}
    by_chunk = {c.chunk_id: c for c in chunks}
    by_source = {s.version_id: s for s in sources}
    for c in cases:
        f = families[c.family_id]
        if (c.split, c.domain) != (f['split'], f['domain']):
            raise ValueError('Case split/domain differs from manifest')
    if {g.case_id for g in gold} - by_case.keys():
        raise ValueError('Orphan gold')
    if require_gold and {g.case_id for g in gold} != by_case.keys():
        raise ValueError('Missing gold')
    for g in gold:
        c = by_case[g.case_id]
        quoted_ids = {q.chunk_id for q in g.quote_spans}
        evidence_ids = {cid for group in g.acceptable_evidence_sets for cid in group}
        if not evidence_ids <= quoted_ids:
            raise ValueError('Evidence set has no exact quote')
        for q in g.quote_spans:
            chunk = by_chunk[q.chunk_id]
            source = by_source[chunk.version_id]
            if source.review_status != 'approved' or source.available_at > c.as_of:
                raise ValueError('Evidence unavailable at as_of')
            check_quote(chunk.text, q.span, q.quote)
            # Cross-family citations may be context, but cannot silently prove S/C.
            if q.chunk_id in evidence_ids and source.family_id != c.family_id:
                raise ValueError('Evidence family differs from target')
    return {'cases': len(cases), 'gold': len(gold), 'families': len(families),
            'gold_complete': bool(cases) and len(gold) == len(cases)}


def outside_workspace(path):
    if path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Test input/gold must remain outside agent workspace until T13')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--corpus', type=Path, default=ROOT / 'data/corpus')
    p.add_argument('--manifest', type=Path, default=ROOT / 'eval/split_manifest.json')
    p.add_argument('--dev-cases', type=Path, default=ROOT / 'data/dev/cases.jsonl')
    p.add_argument('--dev-gold', type=Path)
    p.add_argument('--test-cases', type=Path)
    p.add_argument('--test-gold', type=Path)
    p.add_argument('--require-gold', action='store_true')
    p.add_argument('--receipt', type=Path)
    p.add_argument('--attestation', type=Path)
    p.add_argument('--config', type=Path)
    p.add_argument('--prompt', type=Path, action='append', default=[])
    args = p.parse_args()
    for path in (args.test_cases, args.test_gold):
        if path:
            outside_workspace(path)
    sources, chunks, corpus = load_corpus(args.corpus)
    manifest = json.loads(args.manifest.read_text())
    if manifest['corpus_version'] != corpus['corpus_version']:
        raise ValueError('Corpus version differs from split manifest')
    cases, gold = [], []
    for split, cp, gp in [('dev', args.dev_cases, args.dev_gold), ('test', args.test_cases, args.test_gold)]:
        batch = read_jsonl(cp, EvalCase) if cp else []
        if any(c.split != split for c in batch):
            raise ValueError('Wrong split file')
        labels = read_jsonl(gp, GoldRecord) if gp else []
        if {g.case_id for g in labels} - {c.case_id for c in batch}:
            raise ValueError('Gold in wrong split file')
        cases.extend(batch)
        gold.extend(labels)
    result = validate(cases, gold, manifest, sources, chunks, require_gold=args.require_gold or bool(args.receipt))
    if args.receipt:
        outside_workspace(args.receipt)
        if not all((args.dev_gold, args.test_cases, args.test_gold, args.config, args.prompt, args.attestation)):
            raise ValueError('Receipt requires both inputs/golds, config, prompts, human attestation')
        if not any(c.split == 'test' for c in cases) or not any(c.split == 'dev' for c in cases):
            raise ValueError('No nonempty dev/test evaluation')
        if {c.family_id for c in cases} != {f['family_id'] for f in manifest['families']}:
            raise ValueError('Manifest families missing cases')
        attest = json.loads(args.attestation.read_text())
        for key in ('human_gold_reviewed', 'one_claim_per_case', 'scope_entailment_reviewed',
                    'source_spotcheck_complete', 'test_sealed_until_T13', 'no_test_tuning',
                    'temporal_subset_selected', 'config_resolved', 'pilot_limits_accepted'):
            if attest.get(key) is not True:
                raise ValueError(f'Owner attestation missing: {key}')
        dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip())
        if dirty:
            raise ValueError('Commit does not describe dirty workspace; owner must commit before receipt')
        paths = [args.dev_cases, args.dev_gold, args.test_cases, args.test_gold, args.manifest,
                 ROOT / 'eval/protocol.md', ROOT / 'eval/annotation_guide.md', ROOT / 'eval/schema.py',
                 ROOT / 'scripts/validate_eval.py', args.config, args.attestation, *args.prompt,
                 *(args.corpus / name for name in ('sources.json', 'chunks.json', 'manifest.json'))]
        receipt = {'status': 'validated_candidate_NOT_frozen', 'checks': result,
                   'corpus_version': corpus['corpus_version'],
                   'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                   'sha256': {str(path): digest(path) for path in paths}}
        # Exclusive creation: never overwrite a previous lock receipt.
        with args.receipt.open('x') as output:
            json.dump(receipt, output, ensure_ascii=False, indent=2)
    print(json.dumps(result | {'status': 'validated_NOT_frozen'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
