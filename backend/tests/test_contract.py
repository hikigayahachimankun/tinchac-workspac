from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unicodedata

import pytest
from pydantic import ValidationError

from backend.app import models as m
from scripts.export_contracts import export_text, validate_examples

EXAMPLES = Path('contracts/examples')


def example(name):
    return json.loads((EXAMPLES / f'{name}.json').read_text())


def test_all_examples_and_schema():
    assert validate_examples() == len(m.CONTRACT_MODELS)
    schema = json.loads(export_text())
    for model in m.CONTRACT_MODELS:
        assert model.__name__ in schema['components']['schemas']
    assert export_text() == export_text()


@pytest.mark.parametrize('name', ['check_create', 'check_result', 'SourceVersion', 'Claim'])
def test_extra_fields(name):
    model = {'check_create': m.CheckCreate, 'check_result': m.CheckRecord}.get(name, getattr(m, name, None))
    data = example(name)
    data['unexpected'] = True
    with pytest.raises(ValidationError):
        model.model_validate(data)


@pytest.mark.parametrize('amount', [7.0, 7.5, True, '7000000', -1])
def test_money_strict(amount):
    with pytest.raises(ValidationError):
        m.MoneyValue(amount=amount, currency='VND', basis='per_award')


@pytest.mark.parametrize('change', [
    {'input_mode':'image'}, {'input_mode':'image','asset_id':'00000000-0000-4000-8000-000000000002'},
    {'asset_token':'token'}, {'consent_to_process':False}, {'consent_to_process':1},
    {'as_of':'2026-11-08T17:00:00'}, {'confirmed_text':'short'}, {'confirmed_text':'x'*6001},
])
def test_invalid_input(change):
    with pytest.raises(ValidationError):
        m.CheckCreate.model_validate(example('check_create') | change)


def test_image_and_time():
    data = example('check_create')
    m.CheckCreate.model_validate(data | {'input_mode':'image', 'asset_id': example('asset_ready')['asset_id'], 'asset_token':'fixture-token'})
    future = (datetime.now(timezone.utc) + timedelta(minutes=6)).isoformat()
    with pytest.raises(ValidationError):
        m.CheckCreate.model_validate(data | {'as_of':future})
    assert m.CheckCreate.model_validate(data).as_of.utcoffset() == timedelta(0)


@pytest.mark.parametrize('label,relation', [('supported','supports'), ('contradicted','contradicts')])
def test_final_verdict_evidence(label, relation):
    data = example('ClaimVerdict') | {'label':label, 'evidence':[]}
    # Draft may be invalid; final result must reject it.
    m.VerdictDraft.model_validate({k:v for k,v in data.items() if k in m.VerdictDraft.model_fields})
    with pytest.raises(ValidationError):
        m.ClaimVerdict.model_validate(data)
    data['evidence'] = [example('EvidenceRef') | {'relation':relation}]
    m.ClaimVerdict.model_validate(data)
    data['evidence'][0]['relation'] = 'context'
    with pytest.raises(ValidationError):
        m.ClaimVerdict.model_validate(data)


def test_unicode_quote():
    text = '🎓 Học bổng: 5.000.000 đồng/suất.'
    quote = '5.000.000 đồng/suất.'
    start = text.index(quote)
    chunk_data = example('SourceChunk') | {'text':text, 'source_span':{'start':0,'end':len(text)}}
    chunk = m.SourceChunk.model_validate(chunk_data)
    context = {'chunks':{chunk.chunk_id:chunk}}
    data = example('EvidenceRef') | {'quote_span':{'start':start,'end':start+len(quote)}}
    m.EvidenceRef.model_validate(data, context=context)
    for bad in [
        {'quote_span':{'start':start+1,'end':len(text)}},
        {'quote_span':{'start':start,'end':len(text)+1}},
        {'quote':unicodedata.normalize('NFD',quote)},
        {'chunk_id':'absent'}, {'version_id':'wrong'},
    ]:
        with pytest.raises(ValidationError):
            m.EvidenceRef.model_validate(data | bad, context=context)


@pytest.mark.parametrize('span', [{'start':-1,'end':1}, {'start':1,'end':1}, {'start':2,'end':1}])
def test_bad_span(span):
    with pytest.raises(ValidationError):
        m.TextSpan.model_validate(span)


@pytest.mark.parametrize('status', ['queued','extracting','retrieving','verifying','failed'])
def test_check_status(status):
    data = example('check_result') | {'status':status}
    with pytest.raises(ValidationError):
        m.CheckRecord.model_validate(data)
    data['result'] = None
    data['error'] = example('ErrorDetail') if status == 'failed' else None
    m.CheckRecord.model_validate(data)


def test_result_relations():
    data = example('CheckResult')
    for change in [
        {'summary':data['summary'] | {'supported':1}}, {'claims':data['claims']*2}, {'sources':[]},
    ]:
        with pytest.raises(ValidationError):
            m.CheckResult.model_validate(data | change)
    record = example('check_result')
    with pytest.raises(ValidationError):
        m.CheckRecord.model_validate(record | {'check_id':'00000000-0000-4000-8000-000000000009'})


def test_normalization_dates_and_usage():
    data = example('NormalizedValue') | {'text':'also set'}
    with pytest.raises(ValidationError):
        m.NormalizedValue.model_validate(data)
    for change in [{'value':None}, {'precision':'unknown'}, {'value':'2026-11-08T00:00:00','precision':'datetime'}]:
        with pytest.raises(ValidationError):
            m.DateValue.model_validate(example('DateValue') | change)
    for cost in [float('nan'),float('inf'),-1]:
        with pytest.raises(ValidationError):
            m.Usage.model_validate(example('Usage') | {'cost_usd':cost})


def test_extraction_and_sources():
    data = example('ExtractionResult')
    for claims in [data['claims']*2, data['claims']*9]:
        with pytest.raises(ValidationError):
            m.ExtractionResult.model_validate(data | {'claims':claims})
    m.ExtractionResult.model_validate(data | {'claims':[]})
    source = example('SourceVersion')
    source['facts'][0]['quote'] = 'wrong'
    with pytest.raises(ValidationError):
        m.SourceVersion.model_validate(source)
    public = example('SourcePublic')
    public['chunks'][0]['version_id'] = 'wrong'
    with pytest.raises(ValidationError):
        m.SourcePublic.model_validate(public)


def test_nullable_fields_are_required_and_not_empty():
    data = example('Scope')
    with pytest.raises(ValidationError):
        m.Scope.model_validate(data | {'cohort':''})
    del data['cohort']
    with pytest.raises(ValidationError):
        m.Scope.model_validate(data)
    m.OCRResult.model_validate(example('OCRResult') | {'text':''})


@pytest.mark.parametrize('value', [0, 1.0, True, '0', '2026-11-08', '2026-11-08T10:00:00'])
def test_timestamp_requires_iso_offset(value):
    with pytest.raises(ValidationError):
        m.CheckCreate.model_validate(example('check_create') | {'as_of':value})
    with pytest.raises(ValidationError):
        m.AssetRecord.model_validate(example('asset_ready') | {'created_at':value})


def test_asset_state_and_expiry():
    data = example('asset_ready')
    for change in [{'ocr':None}, {'error':example('ErrorDetail')}, {'expires_at':data['created_at']}]:
        with pytest.raises(ValidationError):
            m.AssetRecord.model_validate(data | change)
    for status in ['queued', 'ocr']:
        m.AssetRecord.model_validate(data | {'status':status, 'ocr':None})
    m.AssetRecord.model_validate(data | {'status':'failed', 'ocr':None, 'error':example('ErrorDetail')})
