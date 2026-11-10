"""Prepare public Claim drafts and blank human worksheets; never reads gold or corpus."""
import argparse
import csv
import json
from pathlib import Path

from backend.app.models import Claim, NormalizedValue, Scope
from eval.harness import digest, prepare_claim, read_jsonl, temporal_subset
from eval.schema import EvalCase


def prepare(cases, output: Path, *, claims=None):
    ids = [c.case_id for c in cases]
    if not cases or len(ids) != len(set(ids)) or len({c.split for c in cases}) != 1:
        raise ValueError('Nonempty unique cases from one split required')
    if claims is not None:
        if set(claims) != set(ids):
            raise ValueError('Claim coverage differs from cases')
        claims = {c.case_id:prepare_claim(c, claims[c.case_id]) for c in cases}
    output.mkdir(mode=0o700)  # Refuse overwrite, including prior human edits.
    (output/'cases.jsonl').write_text(''.join(c.model_dump_json()+'\n' for c in cases))
    entries = []
    for case in cases:
        claim = claims[case.case_id] if claims is not None else Claim(
            claim_id=case.target_claim_id, statement=case.target_statement, field_type=case.field_type,
            input_span=None, raw_value='', scope=Scope(**dict.fromkeys(Scope.model_fields)),
            normalized=NormalizedValue(text=None,money=None,date=None,url=None), ambiguities=[])
        entries.append({'case_id':case.case_id, 'claim':claim.model_dump(mode='json')})
    name = 'claims.jsonl' if claims is not None else 'claims.draft.jsonl'
    (output/name).write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in entries))
    with (output/'annotation_worksheet.csv').open('x', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['case_id','family_id','input_text','target_statement','field_type','as_of',
            'label','reason_codes','acceptable_evidence_sets','reference_quotes','temporal_status',
            'rationale','annotator_1','annotator_2','agreement_before_adjudication','adjudication_note'])
        for c in cases:
            writer.writerow([c.case_id,c.family_id,c.input_text,c.target_statement,c.field_type.value,c.as_of.isoformat(),*['']*10])
    receipt = {'status':'validated_public_inputs_NOT_frozen' if claims is not None else 'draft_NOT_frozen',
        'human_gold_count':0, 'cases_hash':digest([c.model_dump(mode='json') for c in cases]),
        'claims_hash':digest({k:v.model_dump(mode='json') for k,v in claims.items()}) if claims is not None else None,
        'temporal_case_ids':temporal_subset(cases), 'seed':42,
        'note':'Draft scope/raw value are deliberately blank. A human checks input scope and atomicity, annotates against approved sources without model predictions, and retains gold privately. This is not a freeze receipt.'}
    (output/'preparation.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cases', default='data/dev/cases.jsonl')
    parser.add_argument('--claims', help='Input-only Claim sidecar completed and checked before freeze')
    parser.add_argument('--output', type=Path, required=True, help='New local directory, never overwritten')
    args = parser.parse_args()
    claims = None
    if args.claims:
        rows = read_jsonl(args.claims)
        claims = {r['case_id']:Claim.model_validate(r['claim']) for r in rows}
        if len(claims) != len(rows):
            raise ValueError('Duplicate Claim sidecar ID')
    receipt = prepare(read_jsonl(args.cases,EvalCase),args.output,claims=claims)
    print(json.dumps({'status':receipt['status'],'human_gold_count':0}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
