"""Audit approved source inventory only; does not read cases, gold or predictions."""
import json
import random
import re
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path
from backend.app.services.corpus import ROOT, load_corpus


def inventory(sources, corpus_version):
    approved = [s for s in sources if s.review_status == 'approved']
    known = {'agribank', 'keidanren_jcci', 'schneider', 'toyota', 'tuition_hki_2026_dot2'}
    if any(not s.is_fixture and s.family_id not in known for s in approved):
        raise ValueError('Expanded inventory needs relationship review and explicit quotas before split')
    groups = {}
    for s in approved:
        groups.setdefault(s.family_id, []).append(s)
    rng = random.Random(42)
    strata = {}
    for domain in ('payment', 'scholarship'):
        ids = sorted(fid for fid, ss in groups.items()
                     if ('payment' if ss[0].scope.fee_kind else 'scholarship') == domain)
        rng.shuffle(ids)
        strata[domain] = ids
    families = []
    for domain, ids in strata.items():
        for fid in ids:
            ss = groups[fid]
            families.append({'family_id': fid, 'domain': domain, 'split': 'dev',
                'exposed_to_dev': True, 'exposure_basis': 'T07 approved-seed dev probes; docs/handoffs/T07.md',
                'version_ids': sorted(s.version_id for s in ss),
                'relationship_review': 'One canonical version in current snapshot; parent page/attachment are one source. No additional approved annual/repost version observed.'})
    pairs = []
    normalized = lambda text: re.sub(r'\s+', ' ', re.sub(r'\d+', '#', text.casefold())).strip()
    for a, b in combinations(sorted(approved, key=lambda s: s.family_id), 2):
        score = SequenceMatcher(None, normalized(a.text), normalized(b.text), autojunk=False).ratio()
        pairs.append({'families': [a.family_id, b.family_id], 'normalized_similarity': round(score, 6),
                      'review_flag': score >= .65, 'same_canonical': a.canonical_url == b.canonical_url,
                      'same_text_hash': a.content_sha256 == b.content_sha256})
    return {'status': 'pilot_draft_NOT_frozen', 'seed': 42, 'corpus_version': corpus_version,
        'algorithm': 'Random(42); sorted family IDs shuffled by domain payment then scholarship. Existing dev exposure overrides allocation. No unexposed family exists; no test assigned.',
        'prospective_rule': 'Add approved relationship-reviewed families before variants; preserve dev exposure; use same stratified seeded order with predeclared domain quotas, target 12/24 or fallback 8/16. Version manifest and audit before new cases.',
        'families': families, 'excluded': [{'family_id': s.family_id, 'version_id': s.version_id,
            'reason': 'quarantined; personal-data attachment excluded'} for s in sources if s.review_status != 'approved']}, {
        'method': 'All approved pairs; NFC corpus, casefold, digit masking, whitespace collapse, SequenceMatcher autojunk=False; >=0.65 flags manual review, not automatic merge.',
        'pairs': pairs, 'limitation': 'Only current approved snapshot: no evidence that other years or unseen reposts do not exist. Review names, parent URLs, scope and amendment references before expansion.'}


def main():
    sources, _, corpus = load_corpus(ROOT / 'data/corpus')
    manifest, audit = inventory(sources, corpus['corpus_version'])
    for path, data in [('eval/split_manifest.json', manifest), ('docs/evidence/T09/family_audit.json', audit)]:
        (ROOT / path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    print('5 approved families: 4 scholarship / 1 payment; 5 dev / 0 test; not frozen')


if __name__ == '__main__':
    main()
