import asyncio
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from google.genai import types

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.models import VerificationOutput, VerdictDraft
from backend.app.services.errors import ServiceError
from backend.app.services.llm import GeminiAdapter
from eval.harness import (append_jsonl, context, digest, infer, no_time_guard,
                          prepare_claim, schedule, shared_bundle, zero_usage)
from scripts.run_eval import fixture_inputs, main, validate_config


def call_one(case,claim,bundle,system,adapter,mode='fixture'):
    return asyncio.run(infer(case,claim,bundle,system,adapter,batch_id='test-batch',
        config_hash='cfg',model='fixture-v1',mode=mode))


def test_same_bundle_metadata_schema_and_one_call_no_gold():
    cases,claims,bundles,outputs=fixture_inputs()
    case=cases[1]; claim=prepare_claim(case,claims[case.case_id]); bundle=shared_bundle(claim,bundles[case.case_id])
    calls=[]
    async def generate(**kw):
        calls.append(kw)
        out=outputs[case.case_id].model_copy(deep=True)
        kw['validate'](out)
        return out
    adapter=SimpleNamespace(generate=generate)
    for system in ('B','C','C_NO_TIME'):
        env=call_one(case,claim,bundle,system,adapter)
        assert env['row']['technical_error'] is None
        assert env['bundle_hash']==digest(bundle.model_dump(mode='json'))
    contexts=[json.loads(c['text']) for c in calls]
    assert contexts[0]['bundle']==contexts[1]['bundle']==contexts[2]['bundle']
    source=contexts[0]['bundle']['hits'][0]['source']
    assert all(k in source for k in ('title','scope','facts','available_at','published_at'))
    assert len(calls)==3
    assert {c['output_type'] for c in calls}=={VerificationOutput}
    assert all(c['max_output_tokens']==1200 and not c['public'] for c in calls)
    assert all('gold' not in c['text'] for c in calls)
    assert 'bundle' not in json.loads(context(case,claim,bundle,'A'))
    assert 'code_checks' not in contexts[0]
    assert contexts[2]['code_checks']=={'checks_passed':['source_release_cutoff']}


def test_b_preserves_bad_citation_and_c_records_guard_changes():
    cases,claims,bundles,outputs=fixture_inputs()
    case=cases[7]; claim=prepare_claim(case,claims[case.case_id]); bundle=shared_bundle(claim,bundles[case.case_id])
    adapter=SimpleNamespace(generate=AsyncMock(return_value=outputs[case.case_id]))
    b=call_one(case,claim,bundle,'B',adapter)['row']
    c=call_one(case,claim,bundle,'C',adapter)['row']
    assert b['raw_prediction']==b['prediction']
    assert b['prediction']['label']=='contradicted'
    assert c['prediction']['label']=='insufficient_evidence'
    assert 'label' in c['guard_changes']


def test_no_time_removes_date_semantics_but_keeps_future_cutoff():
    cases,claims,bundles,outputs=fixture_inputs()
    case=cases[4]  # missing year: date ambiguity C rejects, no-time delegates to model
    claim=prepare_claim(case,claims[case.case_id]); bundle=shared_bundle(claim,bundles[case.case_id])
    adapter=SimpleNamespace(generate=AsyncMock(return_value=outputs[case.case_id]))
    c=call_one(case,claim,bundle,'C',adapter)['row']
    no=call_one(case,claim,bundle,'C_NO_TIME',adapter)['row']
    assert c['prediction']['label']=='insufficient_evidence'
    assert no['prediction']['label']=='supported'
    future=bundle.model_copy(deep=True)
    for h in future.hits:
        h.source.available_at=case.as_of+timedelta(days=1)
    future=shared_bundle(claim,future)
    assert future.hits==[]
    assert call_one(case,claim,future,'C_NO_TIME',adapter)['row']['prediction']['label']=='insufficient_evidence'


def test_api_error_never_becomes_nei_and_unknown_attempt_cost_is_retained(tmp_path):
    cases,claims,bundles,_=fixture_inputs()
    case=cases[1]; claim=prepare_claim(case,claims[case.case_id]); bundle=shared_bundle(claim,bundles[case.case_id])
    settings=Settings(_env_file=None,app_mode='live',gemini_api_key='offline-test',
        database_path=tmp_path/'ledger.db',llm_max_retries=0)
    initialize(settings.database_path)
    adapter=GeminiAdapter(settings,run_id='unknown-attempt',max_calls=1)
    # Make a real reservation and settle unknown, without calling SDK or network.
    async def generate(**kw):
        aid=adapter.budget.reserve(10000,'evaluation',{},run_id=adapter.run_id)
        adapter.budget.finish(aid,outcome='timeout')
        raise ServiceError('PROVIDER_TIMEOUT','offline timeout')
    adapter.generate=generate
    env=call_one(case,claim,bundle,'B',adapter)
    assert env['row']['technical_error']=='PROVIDER_TIMEOUT'
    assert env['row']['prediction'] is None
    assert env['accounting']['known_subtotal_only'] is True
    assert env['accounting']['charged_usd']==.00001
    assert env['row']['usage']['attempts']==1


def test_real_adapter_mock_usage_cap_and_budget_stop_before_io(tmp_path):
    cases,claims,bundles,outputs=fixture_inputs()
    case=cases[1]; claim=prepare_claim(case,claims[case.case_id]); bundle=shared_bundle(claim,bundles[case.case_id])
    settings=Settings(_env_file=None,app_mode='live',gemini_api_key='offline-test',database_path=tmp_path/'ledger.db')
    initialize(settings.database_path)
    adapter=GeminiAdapter(settings,run_id='one-attempt',max_calls=1)
    seen=[]
    async def invoke(text,config):
        seen.append(config)
        return types.GenerateContentResponse(candidates=[types.Candidate(finish_reason='STOP',
            content=types.Content(parts=[types.Part(text=json.dumps({'drafts':[outputs[case.case_id].drafts[0].model_dump(mode='json')]}))]))],
            usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=100,candidates_token_count=100,total_token_count=200),
            model_version='offline-v1')
    adapter._invoke=invoke
    one=call_one(case,claim,bundle,'B',adapter,mode='fresh')
    assert one['row']['technical_error'] is None
    assert one['row']['usage']['input_tokens']==100
    assert one['row']['model_version']=='offline-v1'
    assert seen[0].max_output_tokens==1200 and seen[0].thinking_config.thinking_budget==0
    two=call_one(case,claim,bundle,'B',adapter,mode='fresh')
    assert two['row']['technical_error']=='BUDGET_EXCEEDED'
    assert len(seen)==1


def test_schedule_seed_append_and_existing_run_refused(tmp_path,monkeypatch):
    cases,*_=fixture_inputs()
    assert schedule(cases,set())==schedule(list(reversed(cases)),set())
    path=tmp_path/'append.jsonl'
    append_jsonl(path,{'a':1}); before=path.read_bytes()
    append_jsonl(path,{'b':2})
    assert path.read_bytes().startswith(before)
    output=tmp_path/'run'
    monkeypatch.setattr('sys.argv',['run_eval','--mode','fixture','--output',str(output)])
    assert main()==0
    before=(output/'runs.jsonl').read_bytes()
    assert main()==2
    assert (output/'runs.jsonl').read_bytes()==before


def test_claim_sidecar_and_fresh_placeholders_rejected():
    cases,claims,_,_=fixture_inputs()
    with pytest.raises(ValueError,match='sidecar required'):
        prepare_claim(cases[0])
    wrong=claims[cases[0].case_id].model_copy(update={'statement':'different'})
    with pytest.raises(ValueError,match='differs'):
        prepare_claim(cases[0],wrong)
    config=json.loads(Path('config/experiments.yaml').read_text())
    validate_config(config)
    with pytest.raises(ValueError,match='D02'):
        validate_config(config,fresh=True)


def test_fixture_contexts_fit_same_provider_cap_without_dropping_sources():
    from backend.app.services.llm import provider_schema
    from eval.harness import prompt_for
    cases,claims,bundles,_=fixture_inputs()
    for c in cases:
        cl=prepare_claim(c,claims[c.case_id]); bu=shared_bundle(cl,bundles[c.case_id])
        for system in ('A','B','C','C_NO_TIME'):
            text=context(c,cl,bu,system)
            bound=len((text+prompt_for(system)+json.dumps(provider_schema(VerificationOutput))).encode())+1024
            assert bound<=6000,(c.case_id,system,bound)
            if system!='A':
                assert len(json.loads(text)['bundle']['hits'])==len(bu.hits)


def test_cli_fixture_replay_and_scoring_are_reproducible(tmp_path,monkeypatch):
    from eval.harness import read_jsonl,prompt_for
    from eval.tests.test_metrics import known_data
    from scripts.score_eval import main as score_main
    source=tmp_path/'source'; replay=tmp_path/'replay'
    monkeypatch.setattr('sys.argv',['run_eval','--mode','fixture','--output',str(source)])
    assert main()==0
    monkeypatch.setattr('sys.argv',['run_eval','--mode','replay','--cases',str(source/'cases.jsonl'),
        '--replay',str(source/'runs.jsonl'),'--output',str(replay)])
    assert main()==0
    original=read_jsonl(source/'runs.jsonl'); copied=read_jsonl(replay/'runs.jsonl')
    assert len(original)==len(copied)==27
    assert [e['row']['prediction'] for e in original]==[e['row']['prediction'] for e in copied]
    assert all(e['origin']['run_id'] and e['row']['usage']['attempts']==0 and e['row']['stage_ms']=={} for e in copied)
    # An independent, synthetic vector exercises the actual scoring CLI with
    # owner-local fake gold/reviews. This is never DUT gold.
    cases,gold,envs,reviews=known_data()
    vector=tmp_path/'vector'; vector.mkdir()
    config={'model':'test-model'}
    config_hash=digest(config)
    for e in envs:
        e['mode']='fixture'
        e['row']['config_hash']=config_hash
    manifest={'batch_id':'known','mode':'fixture','config':config,'config_hash':config_hash,
        'cases_hash':digest([c.model_dump(mode='json') for c in cases]),
        'prompts':{s:s for s in ['A','B','C']},'temporal_case_ids':[],
        'schedule':[[c.case_id,s] for c,s in schedule(cases,set())]}
    (vector/'manifest.json').write_text(json.dumps(manifest))
    for name,items in [('cases',cases),('gold',gold),('evidence',reviews)]:
        (vector/f'{name}.jsonl').write_text(''.join(x.model_dump_json()+'\n' for x in items))
    for e in envs:
        append_jsonl(vector/'runs.jsonl',e)
    for name in ('metrics1','metrics2'):
        monkeypatch.setattr('sys.argv',['score_eval','--run',str(vector),'--gold',str(vector/'gold.jsonl'),
            '--evidence',str(vector/'evidence.jsonl'),'--output',str(vector/f'{name}.json')])
        assert score_main()==0
    assert (vector/'metrics1.json').read_bytes()==(vector/'metrics2.json').read_bytes()
    result=json.loads((vector/'metrics1.json').read_text())
    assert result['systems']['B']['accuracy']['value']==3/8
    assert result['systems']['B']['ecv']['family_macro']==pytest.approx(11/30)


def test_fresh_mock_records_retrieval_failure_and_stops_without_provider_io(tmp_path,monkeypatch):
    from backend.app.services.retrieve import Retriever
    cases,claims,_,_=fixture_inputs()
    c=cases[1]
    (tmp_path/'cases.jsonl').write_text(c.model_dump_json()+'\n')
    (tmp_path/'claims.jsonl').write_text(json.dumps({'case_id':c.case_id,'claim':claims[c.case_id].model_dump(mode='json')})+'\n')
    (tmp_path/'split.json').write_text(json.dumps({'status':'draft','families':[{'family_id':c.family_id,'split':'dev'}]}))
    config=json.loads(Path('config/experiments.yaml').read_text())
    config['model_verified']=True
    config['data']['corpus_version']='mock-corpus'
    config['data']['split_manifest']=str(tmp_path/'split.json')
    (tmp_path/'config.yaml').write_text(json.dumps(config))
    db=tmp_path/'ledger.db'; initialize(db)
    monkeypatch.setenv('APP_MODE','live')
    monkeypatch.setenv('DATABASE_PATH',str(db))
    monkeypatch.setenv('GEMINI_API_KEY','offline-never-used')
    monkeypatch.setenv('LLM_MODEL',config['model'])
    def retrieve(*args,**kwargs):
        raise ServiceError('CORPUS_UNAVAILABLE','offline retrieval failure')
    monkeypatch.setattr(Retriever,'from_directory',lambda _:SimpleNamespace(corpus_version='mock-corpus',retrieve_claim=retrieve))
    async def forbidden(*args,**kwargs):
        pytest.fail('Provider must not be called for the first scheduled B retrieval error')
    monkeypatch.setattr(GeminiAdapter,'_invoke',forbidden)
    # This seeded case schedules B first; error is 1/1 planned cases (>10%).
    assert schedule([c],set())[0][1]=='B'
    output=tmp_path/'fresh-mock'
    monkeypatch.setattr('sys.argv',['run_eval','--mode','fresh','--owner-live-public',
        '--config',str(tmp_path/'config.yaml'),'--cases',str(tmp_path/'cases.jsonl'),
        '--claims',str(tmp_path/'claims.jsonl'),'--output',str(output)])
    from scripts.run_eval import run
    assert asyncio.run(run(SimpleNamespace(mode='fresh',owner_live_public=True,
        config=tmp_path/'config.yaml',cases=tmp_path/'cases.jsonl',claims=tmp_path/'claims.jsonl',
        replay=None,output=output)))==2
    rows=[json.loads(l) for l in (output/'runs.jsonl').read_text().splitlines()]
    assert len(rows)==1
    assert rows[0]['row']['technical_error']=='CORPUS_UNAVAILABLE'
    assert rows[0]['row']['prediction'] is None
    event=json.loads((output/'events.jsonl').read_text())
    assert event['planned']==3 and event['written']==1
