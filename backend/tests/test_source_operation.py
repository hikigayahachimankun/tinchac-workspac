"""Local operation boundaries; no external network or real credentials."""
from pathlib import Path

from pydantic import SecretStr
import pytest

from backend.app.services.corpus import ROOT
from scripts.serve_live import live_settings
from scripts.source_sync_http import smoke


@pytest.mark.parametrize('mode',[None,'configured_rates'])
def test_live_launcher_rejects_stale_or_paid_readiness_before_secret_loading(tmp_path,monkeypatch,mode):
    monkeypatch.setattr('scripts.serve_live.account_mode',lambda *a:mode)
    monkeypatch.setattr('scripts.serve_live.load_key',lambda *a:pytest.fail('secret loaded without readiness'))
    with pytest.raises(ValueError,match='readiness'):
        live_settings(tmp_path/'readiness',tmp_path/'secret',tmp_path/'store',tmp_path/'state')


def test_live_launcher_uses_original_shared_ledger_and_safe_secret_loader(tmp_path,monkeypatch):
    monkeypatch.setattr('scripts.serve_live.account_mode',lambda *a:'free_tier')
    calls=[]
    monkeypatch.setattr('scripts.serve_live.load_key',lambda path:calls.append(path) or SecretStr('synthetic-only'))
    settings=live_settings(tmp_path/'readiness',tmp_path/'secret',tmp_path/'store',tmp_path/'state')
    assert calls==[tmp_path/'secret']
    assert settings.database_path==ROOT/'data/private/tinchac-live.sqlite3'
    assert settings.llm_billing_mode=='free_tier' and settings.llm_live_enabled
    assert settings.source_lookup_enabled and settings.app_mode=='live'


@pytest.mark.parametrize('url',['https://evil.test','http://localhost.evil.test','http://user@127.0.0.1:8000'])
def test_operational_http_smoke_cannot_send_input_to_remote_endpoint(tmp_path,url):
    with pytest.raises(ValueError,match='local_http_only'):
        smoke(url,tmp_path/'result','Synthetic public claim, never sent')
    assert not (tmp_path/'result').exists()


def test_production_context_supplies_verbatim_quote_with_original_span(tmp_path):
    from datetime import datetime,timezone
    import json
    from backend.app.models import Claim,SourceFact,NormalizedValue
    from backend.app.services.corpus import build_corpus
    from backend.app.services.retrieve import Retriever
    from backend.app.services.temporal import check_claim
    from backend.app.services.verify import context_text
    from backend.tests.test_source_publication import source_packet
    text='Giới thiệu học bổng Acme Scholarship. Hạn đăng ký được công bố riêng.'
    source,_=source_packet(tmp_path,text=text)
    source.scope.program='ACME SCHOLARSHIP'
    quote='Acme Scholarship';start=text.index(quote)
    source.facts=[SourceFact(field_type='program',normalized=NormalizedValue(text='ACME SCHOLARSHIP',money=None,date=None,url=None),
        scope=source.scope,quote=quote,span=dict(start=start,end=start+len(quote)))]
    chunks,manifest=build_corpus([source]);retriever=Retriever([source],chunks,manifest)
    claim=Claim(claim_id='public',field_type='program',statement='Có học bổng Acme Scholarship.',input_span=None,
        raw_value=quote,normalized=NormalizedValue(text=quote,money=None,date=None,url=None),scope=source.scope,ambiguities=[])
    stamp=datetime.now(timezone.utc);bundle=retriever.retrieve_claim(claim,retriever.corpus_version,stamp)
    context=json.loads(context_text([claim],[bundle],[check_claim(claim,bundle,stamp)]))
    fact=context['claims'][0]['hits'][0]['facts'][0]
    assert fact['quote']==quote
    assert fact['q']==[start,start+len(quote)]
    assert context['hits'][0]['version_id']==source.version_id


def test_old_smoke_capability_cannot_redirect_its_token_outside_local_api(tmp_path):
    import json
    from scripts.source_sync_http import unchanged
    (tmp_path/'capability.json').write_text(json.dumps(dict(url='https://evil.test/check',headers={'X-Resource-Token':'synthetic-private'})))
    (tmp_path/'record.json').write_text('{}')
    class Client:
        def get(self,*args,**kwargs):pytest.fail('capability sent outside the fixed local check path')
    with pytest.raises(ValueError,match='capability_path'):
        unchanged(Client(),tmp_path)
