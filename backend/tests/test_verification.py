import asyncio
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from google.genai import types

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.models import Claim, ExtractionResult, RetrievalBundle, VerificationOutput
from backend.app.services.corpus import sha256
from backend.app.services.errors import ServiceError
from backend.app.services.evidence import validate_verdicts
from backend.app.services.llm import GeminiAdapter
from backend.app.services.normalization import normalize_claim, normalize_url, money_from_raw
from backend.app.services.temporal import check_claim
from backend.app.services.verify import (PROMPT, context_text, limit_bundles, run_pipeline,
                                         verify_claims, verify_extraction)

ROOT = Path(__file__).resolve().parents[2]
CASES = json.loads((ROOT / 'data/fixtures/verification/cases.json').read_text())
ID = UUID('00000000-0000-4000-8000-000000000008')


def inputs(case):
    extraction = ExtractionResult.model_validate(case['extraction'])
    claims = [normalize_claim(c) for c in extraction.claims]
    bundles = [RetrievalBundle.model_validate(b) for b in case['bundles']]
    reports = [check_claim(c, b, b.as_of) for c, b in zip(claims, bundles)]
    output = VerificationOutput.model_validate(case['output'])
    return extraction, claims, bundles, reports, output


def guarded(case, audit=None):
    _, claims, bundles, reports, output = inputs(case)
    return validate_verdicts(output.drafts, claims, bundles, reports, audit=audit)[0]


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['case_id'])
def test_twelve_dev_cases_through_real_guard_and_render(case, caplog):
    extraction, _, bundles, _, output = inputs(case)
    adapter = SimpleNamespace(generate=AsyncMock(return_value=output))
    audit = []
    with caplog.at_level('INFO'):
        result = asyncio.run(verify_extraction(ID, extraction, bundles, llm=adapter, run_mode='fixture',
            corpus_updated_at=datetime.fromisoformat('2026-11-09T12:00:00Z'), audit=audit))
    verdict = result.claims[0]
    assert verdict.label == case['expected']['label']
    assert verdict.reason_codes == [case['expected']['reason']]
    assert verdict.temporal_status == case['expected']['temporal']
    assert getattr(result.summary, verdict.label) == 1
    assert result.summary.supported + result.summary.contradicted + result.summary.insufficient_evidence == 1
    assert adapter.generate.await_count == 1
    assert 'Untrusted draft explanation' not in result.model_dump_json()
    assert 'Untrusted draft explanation' not in caplog.text
    assert extraction.claims[0].statement not in caplog.text
    assert audit[0]['prediction'] == verdict.label
    assert 'claim_id' not in audit[0]
    assert all(e.version_id in {s.version_id for s in result.sources} for e in verdict.evidence)
    if case['case_id'] == 'source_conflict':
        assert len(result.sources) == 2


@pytest.mark.parametrize(('raw','amount','basis'), [
    ('5.000.000 đồng/suất',5000000,'per_award'), ('5 triệu/suất',5000000,'per_award'),
    ('1,5 triệu mỗi suất',1500000,'per_award'), ('300k mỗi sinh viên',300000,'per_student'),
    ('500 nghìn mỗi tín chỉ',500000,'per_credit'), ('5 triệu/năm',5000000,'per_year'),
])
def test_money_integer_units(raw, amount, basis):
    value = money_from_raw(raw)
    assert (value.amount,value.basis) == (amount,basis)


@pytest.mark.parametrize('raw', ['5 triệu', '1.5 đồng/suất', '5 triệu/suất/năm', '5 và 7 triệu/suất', '1,2345k/suất'])
def test_ambiguous_money(raw):
    assert money_from_raw(raw) is None


def test_missing_fee_kind_and_different_money_basis_do_not_contradict():
    case = deepcopy(CASES[1])
    case['extraction']['claims'][0]['scope']['fee_kind'] = None
    assert guarded(case).reason_codes == ['SCOPE_UNCLEAR']
    case = deepcopy(CASES[2])
    case['bundles'][0]['hits'][0]['source']['scope'] = deepcopy(case['extraction']['claims'][0]['scope'])
    case['bundles'][0]['hits'][0]['source']['facts'][0]['scope'] = deepcopy(case['extraction']['claims'][0]['scope'])
    case['extraction']['claims'][0]['raw_value'] = '7 triệu/năm'
    assert guarded(case).label == 'insufficient_evidence'


@pytest.mark.parametrize('mutation', ['version','span','id','future','quarantine'])
def test_invalid_citation_never_supports(mutation):
    case = deepcopy(CASES[0])
    draft = case['output']['drafts'][0]
    draft['label'] = 'supported'
    ref = draft['evidence'][0]
    if mutation == 'version': ref['version_id'] = 'foreign'
    elif mutation == 'span': ref['quote_span']['start'] = 1
    elif mutation == 'id': ref['chunk_id'] = 'foreign'
    elif mutation == 'future': case['bundles'][0]['hits'][0]['source']['available_at'] = '2026-11-10T00:00:00Z'
    else: case['bundles'][0]['hits'][0]['source']['review_status'] = 'quarantined'
    result = guarded(case)
    assert result.label == 'insufficient_evidence' and not result.evidence


def test_matching_quote_without_matching_fact_is_not_entailment():
    case = deepcopy(CASES[1])
    case['output']['drafts'][0]['label'] = 'supported'
    case['output']['drafts'][0]['evidence'][0]['relation'] = 'supports'
    assert guarded(case).label == 'insufficient_evidence'


def test_guard_does_not_upgrade_nei_or_allow_empty_evidence():
    case = deepcopy(CASES[1])
    case['output']['drafts'][0]['label'] = 'insufficient_evidence'
    assert guarded(case).label == 'insufficient_evidence'
    case['output']['drafts'][0]['label'] = 'contradicted'
    case['output']['drafts'][0]['evidence'] = []
    assert guarded(case).label == 'insufficient_evidence'


def test_url_preserves_meaningful_parts_and_unconfirmed_link_is_nei():
    original = 'HTTPS://APPLY.EXAMPLE/Apply?q=2&x=1#Section'
    assert normalize_url(original) == 'https://apply.example/Apply?q=2&x=1#Section'
    assert normalize_url('javascript:alert(1)') is None
    assert normalize_url('https://user:pass@apply.example/') is None
    case = deepcopy(CASES[8])
    case['extraction']['claims'][0]['raw_value'] += '&changed=1'
    assert guarded(case).reason_codes == ['LINK_NOT_CONFIRMED']


def test_bundle_and_draft_ids_must_join_and_snapshot_must_be_consistent():
    extraction, claims, bundles, reports, output = inputs(CASES[1])
    for bad in [[], output.drafts * 2, [output.drafts[0].model_copy(update={'claim_id':'other'})]]:
        with pytest.raises(ServiceError,match='claim ID'):
            validate_verdicts(bad, claims, bundles, reports)
    bundles[0].hits[0].version_id = 'wrong'
    with pytest.raises(ServiceError) as caught:
        validate_verdicts(output.drafts, claims, bundles, reports)
    assert caught.value.detail.code == 'CORPUS_UNAVAILABLE'


def test_provider_failure_stays_technical():
    extraction, _, bundles, _, _ = inputs(CASES[1])
    llm = SimpleNamespace(generate=AsyncMock(side_effect=ServiceError('PROVIDER_TIMEOUT','Mock timeout')))
    with pytest.raises(ServiceError) as caught:
        asyncio.run(verify_extraction(ID, extraction, bundles, llm=llm, run_mode='fixture', corpus_updated_at=bundles[0].as_of))
    assert caught.value.detail.code == 'PROVIDER_TIMEOUT'


def test_adapter_verification_schema_cap_usage_and_budget_gate(tmp_path):
    _, claims, bundles, reports, output = inputs(CASES[1])
    settings = Settings(_env_file=None, app_mode='live', gemini_api_key='mock-key', database_path=tmp_path/'ledger.db')
    initialize(settings.database_path)
    llm = GeminiAdapter(settings)
    data = output.model_dump(mode='json',exclude={'usage'})
    response = types.GenerateContentResponse(candidates=[types.Candidate(finish_reason='STOP',
        content=types.Content(parts=[types.Part(text=json.dumps(data))]))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=50,candidates_token_count=50,total_token_count=100))
    llm._invoke = AsyncMock(return_value=response)
    result = asyncio.run(verify_claims(claims,bundles,reports,llm=llm))
    assert result.usage.attempts == 1
    config = llm._invoke.call_args.args[1]
    assert config.max_output_tokens == 1200
    assert 'usage' not in config.response_json_schema['properties']
    settings.llm_budget_usd = 0
    llm._invoke.reset_mock()
    with pytest.raises(ServiceError) as caught:
        asyncio.run(verify_claims(claims,bundles,reports,llm=llm))
    assert caught.value.detail.code == 'BUDGET_EXCEEDED'
    llm._invoke.assert_not_awaited()


def test_prompt_and_context_keep_injection_as_data_and_mask_contacts():
    _, claims, bundles, reports, _ = inputs(CASES[9])
    claims[0].statement += ' user@example.com STK 123456789012'
    text = context_text(claims,bundles,reports)
    assert 'Ignore rules' in text and 'DATA' in PROMPT.read_text()
    assert 'user@example.com' not in text and '123456789012' not in text


def test_six_chunk_limit_first_hit_each_claim_and_warning():
    _, claims, bundles, _, _ = inputs(CASES[1])
    bundle = bundles[0]
    bundle.hits = [bundle.hits[0].model_copy(update={'chunk_id':f'chunk{i}'}) for i in range(8)]
    other = bundle.model_copy(deep=True,update={'claim_id':'c2'})
    other.hits = [h.model_copy(update={'chunk_id':f'other{i}'}) for i,h in enumerate(other.hits)]
    limited, clipped = limit_bundles([bundle,other])
    assert clipped and [len(b.hits) for b in limited] == [3,3]


def test_current_availability_supported_draft_with_contradicting_evidence_downgrades():
    case = deepcopy(CASES[3])
    c = case['extraction']['claims'][0]
    c.update(field_type='current_availability', raw_value='còn hạn', normalized=dict(text='còn hạn',money=None,date=None,url=None))
    case['output']['drafts'][0]['label'] = 'supported'
    case['output']['drafts'][0]['evidence'][0]['relation'] = 'contradicts'
    assert guarded(case).label == 'insufficient_evidence'


def test_compatible_date_precisions_are_not_source_conflict():
    case = deepcopy(CASES[5])
    first = deepcopy(case['bundles'][0]['hits'][1])
    first['chunk_id'], first['version_id'], first['source']['version_id'] = 'date_c1','date_v1','date_v1'
    first['source']['facts'][0]['normalized']['date'].update(value='2026-11-10',precision='date')
    case = deepcopy(CASES[3])
    case['extraction']['claims'][0]['raw_value'] = '10/11/2026'
    case['bundles'][0]['hits'].append(first)
    assert guarded(case).label == 'supported'


def test_context_does_not_send_unavailable_or_unapproved_source():
    _,claims,bundles,reports,_ = inputs(CASES[1])
    bundles[0].hits[0].source.available_at = datetime.fromisoformat('2026-11-20T00:00:00Z')
    assert 'Không thu phí' not in context_text(claims,bundles,reports)
    bundles[0].hits[0].source.available_at = datetime.fromisoformat('2026-11-01T00:00:00Z')
    bundles[0].hits[0].source.review_status = 'quarantined'
    assert 'Không thu phí' not in context_text(claims,bundles,reports)


def test_each_final_citation_relation_is_checked_not_only_one():
    case = deepcopy(CASES[1])
    extra = deepcopy(CASES[0]['bundles'][0]['hits'][0])
    extra['chunk_id'],extra['version_id'],extra['source']['version_id'] = 'award_c1','award_v1','award_v1'
    case['bundles'][0]['hits'].append(extra)
    ref = deepcopy(CASES[0]['output']['drafts'][0]['evidence'][0])
    ref['chunk_id'],ref['version_id'],ref['relation'] = 'award_c1','award_v1','contradicts'
    case['output']['drafts'][0]['evidence'].append(ref)
    verdict = guarded(case)
    assert verdict.label == 'contradicted'
    assert all(e.relation == 'context' for e in verdict.evidence if e.chunk_id=='award_c1')


def test_unrelated_field_on_another_program_does_not_change_source_silence():
    case = deepcopy(CASES[0])
    extra = deepcopy(CASES[1]['bundles'][0]['hits'][0])
    extra['chunk_id'],extra['version_id'],extra['source']['version_id'] = 'other_c1','other_v1','other_v1'
    extra['source']['scope']['program'] = 'Other'
    extra['source']['facts'][0]['scope']['program'] = 'Other'
    case['bundles'][0]['hits'].append(extra)
    assert guarded(case).reason_codes == ['SOURCE_SILENT']


def test_pipeline_four_fields_one_extraction_and_one_verification():
    from backend.app.models import CheckCreate, SourceFact, Usage
    from backend.app.services.evidence import FactMatch
    extraction, _, bundles, _, _ = inputs(CASES[2])
    source = bundles[0].hits[0].source.model_copy(deep=True)
    scope = extraction.claims[0].scope
    records = [deepcopy(CASES[2]['extraction']['claims'][0]), deepcopy(CASES[3]['extraction']['claims'][0]),
               deepcopy(CASES[0]['extraction']['claims'][0])]
    records.insert(0, records[0] | {'field_type':'program','raw_value':scope.program,
        'statement':scope.program,'normalized':dict(text=scope.program,money=None,date=None,url=None)})
    claims = [normalize_claim(Claim.model_validate(c | {'claim_id':f'c{i}'})) for i,c in enumerate(records)]
    values = [claims[0].normalized, normalize_claim(Claim.model_validate(deepcopy(CASES[2]['extraction']['claims'][0]) | {'raw_value':'5 triệu/suất'})).normalized,
              claims[2].normalized]
    quotes = [scope.program,'5.000.000 đồng/suất','Hạn 10/11/2026 lúc 16h00']
    source.text = '\n'.join(quotes)
    source.content_sha256 = sha256(source.text)
    source.scope = scope
    source.facts = [SourceFact(field_type=c.field_type,normalized=v,scope=scope,quote=q,
        span={'start':source.text.index(q),'end':source.text.index(q)+len(q)}) for c,v,q in zip(claims,values,quotes)]
    hit = bundles[0].hits[0].model_copy(update={'source':source,'text':source.text})
    stamp = bundles[0].as_of
    retrieval_calls = []
    class Retriever:
        corpus_version = 'fixture-t08-v1'
        def retrieve_claim(self, claim, version, as_of):
            retrieval_calls.append(claim.claim_id)
            return RetrievalBundle(claim_id=claim.claim_id,query=claim.statement,hits=[hit],corpus_version=version,as_of=as_of,reason='found')
    extraction.claims = claims
    usage = extraction.usage.model_copy(update={'input_tokens':2,'output_tokens':3,'attempts':1})
    extraction.usage = usage
    drafts = []
    for i,c in enumerate(claims):
        label = ['supported','contradicted','supported','insufficient_evidence'][i]
        refs = [FactMatch(hit,source.facts[i],source.facts[i].span.start).citation('contradicts' if i==1 else 'supports')] if i<3 else []
        drafts.append(dict(claim_id=c.claim_id,label=label,reason_codes=['MATCHED'],explanation='mock',evidence=refs,temporal_status='unknown'))
    verification = VerificationOutput(drafts=drafts,usage=usage)
    invocations = []
    class Mock:
        settings = SimpleNamespace(app_mode='fixture')
        async def generate(self, **kwargs):
            invocations.append(kwargs['output_type'])
            if kwargs['output_type'] is VerificationOutput:
                from backend.app.services.llm import provider_schema
                bound = len((kwargs['text'] + kwargs['prompt'] + json.dumps(provider_schema(VerificationOutput))).encode()) + 1024
                assert bound <= 6000
            output = extraction if kwargs['output_type'] is ExtractionResult else verification
            kwargs['validate'](output)
            return output
    request = CheckCreate(schema_version='1.0',input_mode='text',confirmed_text='Học bổng Minh Họa có 7 triệu/suất, hạn 10/11/2026 lúc 16h00 và phí giữ suất.',
        asset_id=None,asset_token=None,as_of=stamp,consent_to_process=True)
    result = asyncio.run(run_pipeline(ID,request,llm=Mock(),retriever=Retriever(),corpus_updated_at=stamp))
    assert invocations == [ExtractionResult,VerificationOutput]
    assert retrieval_calls == ['c0','c1','c2','c3']
    assert [v.label for v in result.claims] == ['supported','contradicted','supported','insufficient_evidence']
    assert result.usage.input_tokens == 4 and result.usage.output_tokens == 6 and result.usage.attempts == 2


def test_six_public_cases_through_adapter_with_mock_and_no_network(tmp_path, monkeypatch):
    from scripts.verification_dev import run_public_cases
    from google import genai
    def forbidden(*args,**kwargs):
        raise AssertionError('Network client must not be created')
    monkeypatch.setattr(genai,'Client',forbidden)
    settings = Settings(_env_file=None,app_mode='live',gemini_api_key='mock-only',database_path=tmp_path/'mock.db')
    initialize(settings.database_path)
    rows = asyncio.run(run_public_cases(settings))
    assert len(rows)==6 and not any('error' in r for r in rows)
    assert [r['label'] for r in rows] == ['supported','contradicted','insufficient_evidence','supported','supported','supported']
    assert rows[2]['reasons']==['SOURCE_SILENT']
    assert rows[4]['temporal_status']=='expired'
    assert all(r['usage']['attempts']==1 and r['input_bound']<=6000 for r in rows)
    with GeminiAdapter(settings).budget.db() as db:
        assert db.execute('SELECT COUNT(*) FROM llm_attempts').fetchone()[0]==6


def test_redacted_context_is_not_cached_as_public():
    _,claims,bundles,reports,output = inputs(CASES[1])
    claims[0].statement += ' user@example.com'
    llm = SimpleNamespace(generate=AsyncMock(return_value=output))
    asyncio.run(verify_claims(claims,bundles,reports,llm=llm,public=True))
    assert llm.generate.call_args.kwargs['public'] is False


def test_changed_fact_span_or_text_is_a_snapshot_error():
    _,claims,bundles,reports,output = inputs(CASES[1])
    bundles[0].hits[0].source.facts[0].span.start = 1
    with pytest.raises(ServiceError) as caught:
        validate_verdicts(output.drafts,claims,bundles,reports)
    assert caught.value.detail.code=='CORPUS_UNAVAILABLE'


def test_vietnamese_grouping_also_applies_before_magnitude_units():
    assert money_from_raw('5.000 triệu/suất').amount == 5000000000
    assert money_from_raw('1.500 nghìn mỗi sinh viên').amount == 1500000


def test_six_public_cases_leave_room_for_t05_schema_repair(tmp_path, monkeypatch):
    from scripts import verification_dev
    original = verification_dev.mock_response
    calls = []
    def first_bad_then_valid(drafts):
        calls.append(1)
        if len(calls)%2:
            drafts = [drafts[0].model_copy(update={'claim_id':'unknown-claim'})]
        return original(drafts)
    monkeypatch.setattr(verification_dev,'mock_response',first_bad_then_valid)
    settings = Settings(_env_file=None,app_mode='live',gemini_api_key='mock-only',database_path=tmp_path/'repair.db')
    initialize(settings.database_path)
    rows = asyncio.run(verification_dev.run_public_cases(settings))
    assert len(rows)==6 and not any('error' in row for row in rows)
    assert all(row['usage']['attempts']==2 for row in rows)
    with GeminiAdapter(settings).budget.db() as db:
        assert db.execute('SELECT COUNT(*) FROM llm_attempts').fetchone()[0]==12
