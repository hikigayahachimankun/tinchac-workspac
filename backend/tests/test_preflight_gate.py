"""Synthetic credentials/provider metadata only; tests never use the owner's secret."""
from pathlib import Path
import json
import os
import pytest
import httpx
from pydantic import SecretStr

from scripts.provider_check import load_key, model_metadata, readiness

SECRET='synthetic-secret-never-an-actual-key'


def write_secret(tmp_path, text=None,mode=0o600):
    path=tmp_path/'gemini.env'
    path.write_text(text if text is not None else 'GEMINI_API_KEY='+SECRET+'\n')
    path.chmod(mode)
    return path


def test_private_literal_key_loads_without_process_environment_or_repr_leak(tmp_path,monkeypatch):
    monkeypatch.delenv('GEMINI_API_KEY',raising=False)
    path=write_secret(tmp_path,'# secret\nexport GEMINI_API_KEY="'+SECRET+'"\n')
    key=load_key(path)
    assert key.get_secret_value()==SECRET and SECRET not in repr(key)
    assert 'GEMINI_API_KEY' not in os.environ


@pytest.mark.parametrize('text,mode',[(None,0o644),('GEMINI_API_KEY=$(touch should-not-exist)',0o600),
    ('GEMINI_API_KEY=`id`',0o600),('GEMINI_API_KEY=',0o600),
    ('GEMINI_API_KEY='+SECRET+'\nGEMINI_API_KEY=duplicate',0o600),('OTHER_CONFIG=unsafe',0o600)])
def test_unsafe_secret_is_rejected_without_value_in_error(tmp_path,text,mode):
    path=write_secret(tmp_path,text,mode)
    with pytest.raises(ValueError) as exc:load_key(path)
    assert SECRET not in str(exc.value)
    assert not (tmp_path/'should-not-exist').exists()


def test_secret_symlink_is_rejected(tmp_path):
    target=write_secret(tmp_path)
    path=tmp_path/'symlink.env';path.symlink_to(target)
    with pytest.raises(ValueError):load_key(path)


def test_metadata_get_has_header_auth_no_redirect_and_never_implies_billing(tmp_path):
    path=write_secret(tmp_path)
    calls=[]
    def respond(req):
        calls.append(req)
        assert req.method=='GET' and ':generateContent' not in str(req.url)
        assert req.headers['x-goog-api-key']==SECRET and SECRET not in str(req.url)
        return httpx.Response(200,json={'name':'models/gemini-3.5-flash-lite',
            'supportedGenerationMethods':['generateContent'],'inputTokenLimit':1048576,'outputTokenLimit':65536})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report=readiness(path,'gemini-3.5-flash-lite',client=client)
    assert len(calls)==1 and report['metadata']['accessible']
    assert not report['billing_verified'] and not report['quota_verified']
    assert report['generation_attempts']==0 and report['preflight_status']=='blocked'
    assert SECRET not in json.dumps(report)


@pytest.mark.parametrize('status',[302,401,403,404,429,500])
def test_metadata_errors_do_not_echo_response_or_follow_redirect(status):
    calls=[]
    def respond(req):
        calls.append(req)
        return httpx.Response(status,headers={'location':'http://127.0.0.1/private'},json={'error':SECRET})
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        report=model_metadata(SecretStr(SECRET),'gemini-3.5-flash-lite',client)
    assert len(calls)==1 and not report['accessible']
    assert SECRET not in json.dumps(report)


def test_other_env_assignments_are_ignored_not_loaded_or_executed(tmp_path,monkeypatch):
    monkeypatch.delenv('OTHER_CONFIG',raising=False)
    path=write_secret(tmp_path,'GEMINI_API_KEY='+SECRET+'\nOTHER_CONFIG=$(touch should-not-exist)\n')
    assert load_key(path).get_secret_value()==SECRET
    assert 'OTHER_CONFIG' not in os.environ and not (tmp_path/'should-not-exist').exists()


def test_run_budget_is_durable_and_unknown_reservations_count(tmp_path):
    from backend.app.config import Settings
    from backend.app.db import initialize
    from backend.app.services.budget import Budget, units
    from backend.app.services.errors import ServiceError
    from backend.app.services.llm import GeminiAdapter
    settings=Settings(_env_file=None,app_mode='live',gemini_api_key=SECRET,database_path=tmp_path/'ledger.db')
    initialize(settings.database_path)
    a=GeminiAdapter(settings,run_id='authorized-once',max_calls=3,run_budget_usd='.03')
    first=a.budget.reserve(units('.02'),'dev',{},run_id=a.run_id)
    a.budget.finish(first,outcome='timeout')
    restarted=GeminiAdapter(settings,run_id='authorized-once',max_calls=3,run_budget_usd='.03')
    with pytest.raises(ServiceError) as exc:
        restarted.budget.reserve(units('.011'),'dev',{},run_id=restarted.run_id)
    assert exc.value.detail.code=='BUDGET_EXCEEDED'
    # A separate run retains its own allowance without changing the global/stage ledger.
    other=GeminiAdapter(settings,run_id='separate-synthetic-authorization',max_calls=3,run_budget_usd='.03')
    other.budget.reserve(units('.02'),'dev',{},run_id=other.run_id)
    with restarted.budget.db() as db:
        assert db.execute('SELECT SUM(charged_nusd) FROM llm_attempts').fetchone()[0]==units('.04')


@pytest.mark.parametrize('change',[{'max_calls':2},{'run_budget_usd':'.031'},{'run_budget_usd':'.025'}])
def test_registered_run_limits_cannot_be_changed_on_restart(tmp_path,change):
    from backend.app.config import Settings
    from backend.app.db import initialize
    from backend.app.services.llm import GeminiAdapter
    settings=Settings(_env_file=None,database_path=tmp_path/'ledger.db')
    initialize(settings.database_path)
    kwargs={'run_id':'immutable','max_calls':3,'run_budget_usd':'.03'}
    GeminiAdapter(settings,**kwargs)
    with pytest.raises(ValueError):GeminiAdapter(settings,**(kwargs|change))


def test_concurrent_run_reservations_cannot_exceed_three_cents(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from backend.app.config import Settings
    from backend.app.db import initialize
    from backend.app.services.budget import Budget,units
    from backend.app.services.errors import ServiceError
    from backend.app.services.llm import GeminiAdapter
    settings=Settings(_env_file=None,database_path=tmp_path/'ledger.db')
    initialize(settings.database_path)
    GeminiAdapter(settings,run_id='concurrent',max_calls=3,run_budget_usd='.03')
    barrier=Barrier(2)
    def reserve():
        budget=Budget(settings);barrier.wait()
        try:return budget.reserve(units('.02'),'dev',{},run_id='concurrent')
        except ServiceError as exc:return exc.detail.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:reserve(),range(2)))
    assert results.count('BUDGET_EXCEEDED')==1


def test_preflight_cli_blocks_before_secret_load_or_provider_on_unverified_billing(tmp_path,monkeypatch,capsys):
    from scripts import preflight
    report=tmp_path/'unverified.json'
    report.write_text(json.dumps({'billing_verified':False,'quota_verified':False,'model':'gemini-3.5-flash-lite'}))
    def forbidden(*args,**kwargs):
        pytest.fail('Unverified billing must stop before secret load/provider setup')
    monkeypatch.setattr(preflight,'run',forbidden)
    monkeypatch.setattr('scripts.provider_check.load_key',forbidden)
    monkeypatch.setattr('sys.argv',['preflight','--model-check','--secret-file',str(tmp_path/'secret'),
        '--readiness-report',str(report)])
    assert preflight.main()==2
    assert 'No generation attempted' in capsys.readouterr().out


def test_account_receipt_requires_current_matching_verified_account(tmp_path):
    from datetime import datetime,timedelta,timezone
    from scripts.preflight import account_ready
    path=tmp_path/'synthetic-account-receipt.json'
    receipt={'checked_at':datetime.now(timezone.utc).isoformat(),'model':'synthetic-test-model',
             'billing_verified':True,'quota_verified':True,'preflight_status':'ready'}
    path.write_text(json.dumps(receipt))
    assert account_ready(path,'synthetic-test-model')
    assert not account_ready(None,'synthetic-test-model')
    assert not account_ready(path,'different-model')
    for change in ({'billing_verified':False},{'quota_verified':False},{'preflight_status':'blocked'},
                   {'checked_at':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat()}):
        path.write_text(json.dumps(receipt|change))
        assert not account_ready(path,'synthetic-test-model')


def test_owner_free_tier_confirmation_does_not_fabricate_paid_billing_verification(tmp_path):
    from datetime import datetime,timezone
    from scripts.preflight import account_mode
    path=tmp_path/'owner-free.json'
    receipt={'checked_at':datetime.now(timezone.utc).isoformat(),'model':'gemini-3.5-flash-lite',
        'billing_mode':'free_tier','confirmation_source':'project_owner_in_chat',
        'quota_source':'owner_reported_ai_studio','paid_services_authorized':False,
        'max_generation_attempts':3,'preflight_status':'authorized_free_tier','billing_verified':False}
    path.write_text(json.dumps(receipt))
    assert account_mode(path,receipt['model'])=='free_tier'
    path.write_text(json.dumps(receipt|{'paid_services_authorized':True}))
    assert account_mode(path,receipt['model']) is None
