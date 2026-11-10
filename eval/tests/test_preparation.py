"""Public preparation and provenance regressions; synthetic data only."""
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from eval.harness import prepare_claim
from scripts.run_eval import fixture_inputs


def test_claim_raw_value_must_be_traceable_to_public_input():
    cases, claims, _, _ = fixture_inputs()
    c = cases[1]
    supplied = claims[c.case_id].model_copy(update={'raw_value':'secret from gold'})
    with pytest.raises(ValueError, match='public input'):
        prepare_claim(c, supplied)


def test_temporal_subset_is_pinned_and_rejects_drift():
    from eval.harness import temporal_subset
    cases, *_ = fixture_inputs()
    ids = temporal_subset(cases)
    assert set(ids) == {c.case_id for c in cases if c.field_type in ('deadline','current_availability')}
    assert temporal_subset(list(reversed(cases))) == ids
    assert temporal_subset(cases, expected=ids) == ids
    with pytest.raises(ValueError, match='Temporal subset'):
        temporal_subset(cases, expected=[])


def test_preparation_creates_no_gold_and_roundtrips_public_claims(tmp_path):
    from scripts.prepare_eval import prepare
    cases, claims, _, _ = fixture_inputs()
    output = tmp_path/'prepared'
    prepare(cases, output)
    receipt = json.loads((output/'preparation.json').read_text())
    assert receipt['status'] == 'draft_NOT_frozen'
    assert receipt['human_gold_count'] == 0
    assert not list(output.glob('*gold*'))
    rows = [json.loads(line) for line in (output/'claims.draft.jsonl').read_text().splitlines()]
    assert len(rows) == len(cases)
    assert all(r['claim']['scope']['program'] is None for r in rows)
    assert all(r['claim']['raw_value'] == '' for r in rows)
    with pytest.raises(FileExistsError):
        prepare(cases, output)
    reviewed = tmp_path/'reviewed'
    prepare(cases, reviewed, claims=claims)
    assert json.loads((reviewed/'preparation.json').read_text())['claims_hash']
