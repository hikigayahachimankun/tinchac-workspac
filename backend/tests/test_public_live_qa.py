import json
from types import SimpleNamespace

from backend.app.config import Settings
from scripts import public_live_qa as qa


def test_public_pairs_are_fixed_before_calls_and_cover_five_exposed_families():
    first=qa.public_pairs(Settings(_env_file=None))
    assert first==qa.public_pairs(Settings(_env_file=None))
    assert len(first['cases'])==12
    assert len({c['family_id'] for c in first['cases']})==5
    assert all(len(set(c['source_fields']))==2 for c in first['cases'])
    assert first['human_gold'] is False


def test_http_failure_stops_and_deletes_without_persisting_capability(tmp_path,monkeypatch):
    requests=[]
    class Response:
        status_code=202
        def json(self):
            return {'check':{'check_id':'example'},'access_token':'secret-capability'}
    class Client:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,*args,**kwargs):requests.append('post');return Response()
        def get(self,*args,**kwargs):return Response()
        def delete(self,*args,**kwargs):requests.append('delete');return SimpleNamespace(status_code=204)
    record={'status':'failed','error':{'code':'RATE_LIMITED','details':{'provider_http_status':429}}}
    monkeypatch.setattr(qa,'TestClient',lambda app:Client())
    monkeypatch.setattr(qa,'create_app',lambda settings:None)
    monkeypatch.setattr(qa.CheckRecord,'model_validate',lambda data:SimpleNamespace(
        result=None,status='failed',model_dump=lambda **kw:record))
    manifest=qa.public_pairs(Settings(_env_file=None))
    assert qa.http_smoke(None,tmp_path,manifest)==1
    assert requests==['post','delete']
    assert json.loads((tmp_path/'summary.json').read_text())['completed']==0
    assert 'secret-capability' not in ''.join(p.read_text() for p in tmp_path.iterdir())


def test_actual_dev_recording_replay_requires_no_provider_and_retains_original():
    path=qa.Path('docs/evidence/T08/free-tier-public-dev-round2-2026-11-10.json')
    before=path.read_bytes()
    result=qa.replay(Settings(_env_file=None),path)
    assert path.read_bytes()==before
    assert result['model_calls']==0 and len(result['rows'])==6
    assert sum(r['guard'][0]['canonicalized_citations'] for r in result['rows'])==5
    assert {r['verdict']['label'] for r in result['rows']}=={'supported','contradicted','insufficient_evidence'}


def test_public_two_field_contexts_fit_original_6000_byte_bound():
    from datetime import datetime
    from backend.app.models import Claim,VerificationOutput
    from backend.app.services.corpus import load_corpus
    from backend.app.services.llm import provider_schema
    from backend.app.services.normalization import normalize_claim
    from backend.app.services.retrieve import Retriever
    from backend.app.services.temporal import check_claim
    from backend.app.services.verify import context_text,PROMPT,limit_bundles
    settings=Settings(_env_file=None)
    sources,chunks,manifest=load_corpus(settings.corpus_dir)
    retriever=Retriever(sources,chunks,manifest)
    stamp=datetime.fromisoformat(qa.STAMP)
    for case in qa.public_pairs(settings)['cases']:
        source=next(s for s in sources if s.version_id==case['version_id'])
        facts=[next(f for f in source.facts if f.field_type==t and f.quote in case['input_text']) for t in case['source_fields']]
        claims=[normalize_claim(Claim(claim_id=str(i),statement=f.quote,raw_value=f.quote,
            normalized=f.normalized,scope=f.scope,field_type=f.field_type,input_span=None,ambiguities=[]))
            for i,f in enumerate(facts)]
        bundles,_=limit_bundles([retriever.retrieve_claim(c,retriever.corpus_version,stamp) for c in claims])
        context=context_text(claims,bundles,[check_claim(c,b,stamp) for c,b in zip(claims,bundles)])
        bound=len((context+PROMPT.read_text()+json.dumps(provider_schema(VerificationOutput))).encode())+1024
        assert bound<=6000,(case['case_id'],bound)
