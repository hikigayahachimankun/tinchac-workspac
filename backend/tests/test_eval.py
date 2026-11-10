"""T09 synthetic fixture only: no system predictions or real human gold."""
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import json

import pytest
from backend.app.models import SourceVersion
from backend.app.services.corpus import chunk_source
from eval.schema import EvalCase, GoldRecord
from scripts.validate_eval import validate, outside_workspace


@pytest.fixture
def sample():
    source = SourceVersion.model_validate_json(Path('data/fixtures/sources.jsonl').read_text().splitlines()[0])
    chunks = chunk_source(source)
    chunk = chunks[0]
    case = dict(case_id='fixture1', family_id=source.family_id, split='dev', origin='source_derived',
                domain='scholarship', input_text='Một claim fixture.', target_claim_id='claim1',
                target_statement='Một claim fixture.', field_type='award_amount',
                as_of=source.available_at.isoformat(), modification_type=None, input_image_path=None)
    gold = dict(case_id='fixture1', label='supported', reason_codes=['MATCHED'],
                acceptable_evidence_sets=[[chunk.chunk_id]], reference_quotes=[chunk.text],
                temporal_status='unknown', rationale='Fixture tổng hợp, không phải gold thật.',
                annotator_1='FIXTURE_ONLY', annotator_2=None, agreement_before_adjudication=None,
                adjudication_note=None, quote_spans=[dict(chunk_id=chunk.chunk_id, quote=chunk.text,
                    span=dict(start=0, end=len(chunk.text)))])
    manifest = dict(status='pilot_draft_NOT_frozen', seed=42, families=[dict(family_id=source.family_id,
                    domain='scholarship', split='dev', exposed_to_dev=True, version_ids=[source.version_id])])
    return case, gold, manifest, source, chunks


def run(sample, require_gold=True):
    case, gold, manifest, source, chunks = sample
    return validate([EvalCase.model_validate(case)], [GoldRecord.model_validate(gold)],
                    manifest, [source], chunks, require_gold=require_gold)


def test_valid_fixture_and_inclusive_cutoff(sample):
    assert run(sample)['gold_complete']


@pytest.mark.parametrize('field,value', [('label','supported'), ('rationale','leak'),
    ('acceptable_evidence_sets',[]), ('reference_quotes',[]), ('metadata', {'gold': 'leak'}),
    ('field_type','invented'), ('origin','real'), ('as_of','2026-11-10T00:00:00')])
def test_input_schema_leakage_and_enums(sample, field, value):
    sample[0][field] = value
    with pytest.raises(ValueError):
        run(sample)


def test_duplicate_case_and_gold(sample):
    c, g, m, s, chunks = sample
    c, g = EvalCase.model_validate(c), GoldRecord.model_validate(g)
    for cases, gold in [([c,c], [g]), ([c], [g,g])]:
        with pytest.raises(ValueError, match='Duplicate'):
            validate(cases, gold, m, [s], chunks)


@pytest.mark.parametrize('mutation', ['overlap','exposed_test','quarantine','missing_inventory',
    'quote','span','future','missing_quote','empty_evidence','fake_agreement','fake_second','wrong_family','wrong_domain','orphan'])
def test_rejects_invalid_data(sample, mutation):
    c,g,m,s,chunks = sample
    if mutation == 'overlap': m['families'].append(deepcopy(m['families'][0]))
    if mutation == 'exposed_test': m['families'][0]['split'] = 'test'
    if mutation == 'quarantine': s.review_status = 'quarantined'
    if mutation == 'missing_inventory': m['families'] = []
    if mutation == 'quote': g['reference_quotes'] = ['wrong']; g['quote_spans'][0]['quote'] = 'wrong'
    if mutation == 'span': g['quote_spans'][0]['span']['end'] += 1
    if mutation == 'future': c['as_of'] = (s.available_at - timedelta(seconds=1)).isoformat()
    if mutation == 'missing_quote': g['quote_spans'] = []; g['reference_quotes'] = []
    if mutation == 'empty_evidence': g['acceptable_evidence_sets'] = [[]]
    if mutation == 'fake_agreement': g['agreement_before_adjudication'] = True
    if mutation == 'fake_second': g['annotator_2'] = g['annotator_1']; g['agreement_before_adjudication'] = True
    if mutation == 'wrong_family': m['families'][0]['family_id'] = 'different'
    if mutation == 'wrong_domain': c['domain'] = 'payment'
    if mutation == 'orphan': g['case_id'] = 'absent'
    with pytest.raises((ValueError, KeyError)):
        run(sample)


def test_missing_gold_rejected_only_when_required(sample):
    c,_,m,s,chunks = sample
    c = EvalCase.model_validate(c)
    assert not validate([c], [], m, [s], chunks)['gold_complete']
    with pytest.raises(ValueError, match='Missing gold'):
        validate([c], [], m, [s], chunks, require_gold=True)


def test_nei_without_evidence_and_no_interannotator_agreement(sample):
    g=sample[1]
    g.update(label='insufficient_evidence', reason_codes=['SOURCE_SILENT'], acceptable_evidence_sets=[],
             reference_quotes=[], quote_spans=[], rationale='Fixture source inspected; payment fee not stated.')
    assert run(sample)['gold_complete']


def test_private_paths_rejected_inside_workspace():
    with pytest.raises(ValueError, match='outside'):
        outside_workspace(Path('data/private/gold.jsonl'))


def test_inventory_reproducible_and_preserves_dev_exposure(sample):
    from scripts.eval_inventory import inventory
    source = sample[3]
    first = inventory([source], 'fixture')
    assert inventory([source], 'fixture') == first
    assert first[0]['families'][0]['split'] == 'dev'


def test_owner_receipt_with_synthetic_private_files(sample, tmp_path, monkeypatch):
    """Exercise receipt hashes without reading any real private data or committing."""
    import sys
    from backend.app.services.corpus import build_corpus, sha256
    from scripts import validate_eval as cli
    c,g,m,s,chunks = sample
    second = s.model_copy(deep=True)
    second.family_id += '_holdout'
    second.source_id += '_holdout'
    second.version_id += '_holdout'
    second.canonical_url += '?fixture=holdout'
    second.text += '\nFixture holdout source.'
    second.content_sha256 = sha256(second.text)
    new_chunks, corpus = build_corpus([s, second], is_fixture=True)
    directory = tmp_path / 'corpus'
    directory.mkdir()
    for name, value in [('sources', [x.model_dump(mode='json') for x in [s,second]]),
                        ('chunks', [x.model_dump(mode='json') for x in new_chunks]), ('manifest', corpus)]:
        (directory / f'{name}.json').write_text(json.dumps(value))
    holdout_case = deepcopy(c)
    holdout_case.update(case_id='fixture_test', family_id=second.family_id, split='test')
    holdout_gold = deepcopy(g)
    holdout_gold['case_id'] = 'fixture_test'
    second_chunk = next(x for x in new_chunks if x.version_id == second.version_id)
    holdout_gold['acceptable_evidence_sets'] = [[second_chunk.chunk_id]]
    holdout_gold['reference_quotes'] = [second_chunk.text]
    holdout_gold['quote_spans'] = [dict(chunk_id=second_chunk.chunk_id, quote=second_chunk.text,
                                      span=dict(start=0,end=len(second_chunk.text)))]
    m['corpus_version'] = corpus['corpus_version']
    m['families'].append(dict(family_id=second.family_id, domain='scholarship', split='test',
                              exposed_to_dev=False,version_ids=[second.version_id]))
    values = {'dev_cases':c, 'dev_gold':g, 'test_cases':holdout_case, 'test_gold':holdout_gold,
              'manifest':m, 'config': {'model':'FIXTURE_ONLY', 'temporal_subset':[]},
              'attestation': {k:True for k in ('human_gold_reviewed','one_claim_per_case',
                'scope_entailment_reviewed','source_spotcheck_complete','test_sealed_until_T13',
                'no_test_tuning','temporal_subset_selected','config_resolved','pilot_limits_accepted')}}
    arguments = ['validate_eval', '--corpus', str(directory)]
    for name, value in values.items():
        path = tmp_path / f'{name}.json'
        path.write_text(json.dumps(value)+'\n')
        arguments.extend(['--'+name.replace('_','-'), str(path)])
    prompt = tmp_path / 'prompt.txt'
    prompt.write_text('SYNTHETIC FIXTURE PROMPT ONLY')
    receipt = tmp_path / 'receipt.json'
    arguments.extend(['--prompt', str(prompt), '--receipt', str(receipt)])
    monkeypatch.setattr(sys, 'argv', arguments)
    monkeypatch.setattr(cli.subprocess, 'check_output', lambda cmd, **kwargs:
                        b' M dirty' if cmd[1] == 'status' else 'fixture_commit')
    with pytest.raises(ValueError, match='dirty'):
        cli.main()
    assert not receipt.exists()
    monkeypatch.setattr(cli.subprocess, 'check_output', lambda cmd, **kwargs:
                        b'' if cmd[1] == 'status' else 'fixture_commit')
    cli.main()
    result = json.loads(receipt.read_text())
    assert result['status'] == 'validated_candidate_NOT_frozen'
    assert result['commit'] == 'fixture_commit'
    assert result['sha256'][str(prompt)] == cli.digest(prompt)
    assert result['checks']['gold_complete']
    with pytest.raises(FileExistsError):
        cli.main()


def test_empty_cannot_pass_complete(sample):
    _,_,m,s,chunks = sample
    with pytest.raises(ValueError, match='Empty'):
        validate([], [], m, [s], chunks, require_gold=True)
