"""Synthetic reviewed sources, atomic publication, HTTP version pinning and queue abuse."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from threading import Event, Thread

import pytest
from fastapi.testclient import TestClient
from google.genai import types

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.main import create_app
from backend.app.models import Claim, CheckCreate, SourceVersion
from backend.app.services.corpus import ROOT, sha256, load_corpus
from backend.app.services.corpus_store import (GATES, activate, active_directory, publish,
    publish_reviewed, validate_reviews)
from backend.app.services.jobs import Jobs
from backend.app.services.llm import GeminiAdapter
from backend.app.services.source_authority import AuthorityRegistry
from backend.app.services.source_lookup import LookupQueue, missing_authorities
from backend.tests.test_source_sync import NOTICE, run_sync


def source_packet(root, *, url=NOTICE, text='Học bổng Alpha 2026 cấp 5 triệu đồng.', retrieved=None):
    data=json.loads((ROOT/'contracts/examples/SourceVersion.json').read_text())
    digest=sha256(text); sid='dut_'+sha256(url)[:16]
    when=retrieved or datetime.now(timezone.utc).isoformat()
    scope=dict(program='Alpha',academic_year='2026',cohort=None,audience=None,fee_kind=None)
    fact=dict(field_type='award_amount',normalized=dict(text=None,money=dict(amount=5000000,currency='VND',basis='per_award'),
        date=None,url=None),scope=scope,quote=text,span=dict(start=0,end=len(text)))
    data.update(source_id=sid,version_id=sid+'_'+digest[:16],family_id='alpha',canonical_url=url,
        parent_url=None,title='Học bổng Alpha 2026',publisher=AuthorityRegistry().authorities['dut_ctsv']['publisher'],
        text=text,content_sha256=digest,is_fixture=False,review_status='approved',verified_by='synthetic-agent',
        facts=[fact],scope=scope,retrieved_at=when,available_at=when,available_basis='first_seen',
        published_at=None,published_precision='unknown',effective_from=None,effective_to=None,
        supersedes_version_id=None,outbound_links=[])
    s=SourceVersion.model_validate(data)
    raw=root/(s.version_id+'.html')
    from html import escape
    raw.write_text('<div class="wd-content-detail">'+escape(text)+'</div>')
    entry=dict(version_id=s.version_id,source_id=s.source_id,family_id=s.family_id,canonical_url=url,
        notice_url=url,notice_host='dut.udn.vn',notice_path=url.removeprefix('https://dut.udn.vn'),
        review_status='approved',content_selector='.wd-content-detail',ingest=dict(method='html',
        raw=dict(path=raw.name,sha256=sha256(raw.read_text())),normalized_sha256=digest,
        reviewed_by=s.verified_by,snapshot_retrieved_at=when))
    return s,entry


def inputs(root, sources, entries, suffix=''):
    snapshot=root/('snapshot'+suffix+'.json'); register=root/('register'+suffix+'.json')
    snapshot.write_text(json.dumps([s.model_dump(mode='json') for s in sources]))
    register.write_text(json.dumps({'sources':entries}))
    return snapshot,register


def test_atomic_publish_refresh_restart_rollback_and_old_citation(tmp_path):
    a,ea=source_packet(tmp_path)
    one,reg1=inputs(tmp_path,[a],[ea])
    store=tmp_path/'store'
    v1=publish(store,one,reg1,root=tmp_path)
    jobs=Jobs(Settings(_env_file=None,source_sync_store=store,corpus_dir=tmp_path/'no-fallback'))
    pinned=jobs.runtime()
    b,eb=source_packet(tmp_path,text='Học bổng Alpha 2026 gia hạn tới 30/11/2026.')
    two,reg2=inputs(tmp_path,[a,b],[ea,eb],'2')
    v2=publish(store,two,reg2,root=tmp_path)
    assert v1!=v2 and jobs.runtime().retriever.corpus_version==v2
    assert pinned.retriever.corpus_version==v1 and b.version_id not in pinned.sources
    assert jobs.source(a.version_id).text==a.text
    restarted=Jobs(jobs.settings)
    assert restarted.runtime().retriever.corpus_version==v2
    assert publish(store,two,reg2,root=tmp_path)==v2
    activate(store,v1)
    assert jobs.runtime().retriever.corpus_version==v1
    assert jobs.source(b.version_id).text==b.text  # old result survives rollback and restart
    assert Jobs(jobs.settings).source(b.version_id).text==b.text


def test_build_and_pointer_failure_leave_active_untouched(tmp_path,monkeypatch):
    a,ea=source_packet(tmp_path); one,reg1=inputs(tmp_path,[a],[ea])
    store=tmp_path/'store'; v1=publish(store,one,reg1,root=tmp_path)
    pointer=(store/'active.json').read_bytes()
    b,eb=source_packet(tmp_path,text='Học bổng Alpha 2026 phiên bản mới.')
    two,reg2=inputs(tmp_path,[a,b],[ea,eb],'2')
    eb['ingest']['normalized_sha256']='0'*64
    _,bad=inputs(tmp_path,[a,b],[ea,eb],'bad')
    with pytest.raises(ValueError): publish(store,two,bad,root=tmp_path)
    assert pointer==(store/'active.json').read_bytes()
    def fail(*a,**k): raise OSError('synthetic disk failure')
    monkeypatch.setattr('backend.app.services.corpus_store.replace_pointer',fail)
    with pytest.raises(OSError): publish(store,two,reg2,root=tmp_path)
    assert pointer==(store/'active.json').read_bytes()
    assert active_directory(store).name==v1
    # Malformed pointer keeps a running valid runtime serving its pinned snapshot.
    jobs=Jobs(Settings(_env_file=None,source_sync_store=store)); runtime=jobs.runtime()
    (store/'active.json').write_text('{invalid')
    assert jobs.runtime() is runtime


def test_publication_cannot_drop_old_versions_or_touch_frozen_corpus(tmp_path):
    a,ea=source_packet(tmp_path); one,reg1=inputs(tmp_path,[a],[ea])
    store=tmp_path/'store'; publish(store,one,reg1,root=tmp_path)
    b,eb=source_packet(tmp_path,text='Học bổng Alpha năm khác.')
    two,reg2=inputs(tmp_path,[b],[eb],'2')
    with pytest.raises(ValueError,match='history'): publish(store,two,reg2,root=tmp_path)
    with pytest.raises(ValueError,match='private'): publish(ROOT/'data/corpus',one,reg1,root=tmp_path)


def reviewed_candidate(root):
    state=root/'state'; result=run_sync(state)
    directory=state/result['notices'][0]['candidate_path']
    candidate=json.loads((directory/'receipt.json').read_text())
    s,entry=source_packet(root,retrieved=candidate['first_seen'])
    entry['ingest']['raw']=dict(path=str((directory/'sanitized.html').relative_to(root)),
        sha256=candidate['sanitized_html_sha256'])
    packet=dict(version_id=s.version_id,candidate_path=str(directory.relative_to(state)),
        candidate_receipt_sha256=hashlib.sha256((directory/'receipt.json').read_bytes()).hexdigest(),
        reviewer_identity=s.verified_by,reviewer_kind='agent',text_sha256=s.content_sha256,
        gates={k:dict(passed=True,evidence='Synthetic fixture evidence for '+k) for k in GATES},
        family_review=dict(family_id='alpha',evidence='Synthetic same-program chain reviewed'))
    return state,s,entry,packet


def test_candidate_requires_all_review_gates_then_new_checks_use_it(tmp_path):
    state,s,entry,packet=reviewed_candidate(tmp_path)
    snapshot,register=inputs(tmp_path,[s],[entry])
    reviews=tmp_path/'reviews.json'; reviews.write_text(json.dumps([packet]))
    # A candidate exists but no approved corpus/active pointer exists yet.
    store=tmp_path/'store'
    assert active_directory(store) is None
    packet['gates']['family']['passed']=False
    reviews.write_text(json.dumps([packet]))
    with pytest.raises(ValueError,match='review_gate_family'):
        publish_reviewed(store,snapshot,register,reviews,state,AuthorityRegistry(),root=tmp_path)
    assert active_directory(store) is None
    packet['gates']['family']['passed']=True; reviews.write_text(json.dumps([packet]))
    version=publish_reviewed(store,snapshot,register,reviews,state,AuthorityRegistry(),root=tmp_path)
    jobs=Jobs(Settings(_env_file=None,source_sync_store=store,corpus_dir=tmp_path/'absent'))
    runtime=jobs.runtime()
    c=claim_for(s)
    bundle=runtime.retriever.retrieve_claim(c,version,datetime.now(timezone.utc))
    assert [h.version_id for h in bundle.hits]==[s.version_id]


@pytest.mark.parametrize('mutation,reason',[
    (lambda s,e,p: p.update(candidate_receipt_sha256='0'*64),'candidate_hash'),
    (lambda s,e,p: p.update(reviewer_identity='pretend-human'),'reviewer_identity'),
    (lambda s,e,p: p.update(text_sha256='0'*64),'text_hash'),
    (lambda s,e,p: setattr(s,'available_at',datetime(2020,1,1,tzinfo=timezone.utc)),'backdated'),
    (lambda s,e,p: p.update(family_review={}), 'family_review'),
    (lambda s,e,p: setattr(s,'publisher','Unknown faculty'), 'authority'),
])
def test_review_hash_identity_family_time_and_publisher_enforced(tmp_path,mutation,reason):
    state,s,entry,packet=reviewed_candidate(tmp_path)
    mutation(s,entry,packet)
    with pytest.raises(ValueError,match=reason):
        validate_reviews([s],{'sources':[entry]},[packet],state,AuthorityRegistry(),root=tmp_path)


def claim_for(s):
    fact=s.facts[0]
    return Claim(claim_id='synthetic',field_type=fact.field_type,statement=fact.quote,input_span=None,
        raw_value='5 triệu đồng/suất',normalized=fact.normalized.model_copy(deep=True),scope=fact.scope.model_copy(deep=True),ambiguities=[])


def test_queue_coalesces_cools_down_caps_and_recovers_lease(tmp_path):
    timer=[1000]
    q=LookupQueue(tmp_path,clock=lambda:timer[0],cooldown=60)
    assert q.enqueue(['dut_ctsv'])
    assert not q.enqueue(['dut_ctsv'])
    assert q.take()=='dut_ctsv' and q.take() is None
    assert not q.enqueue(['dut_ctsv'])
    timer[0]+=301
    assert LookupQueue(tmp_path,clock=lambda:timer[0],cooldown=60).take()=='dut_ctsv'
    q.finish('dut_ctsv')
    assert not q.enqueue(['dut_ctsv'])
    timer[0]+=61
    assert q.enqueue(['dut_ctsv','dut_finance'])
    assert not q.enqueue(['dut_ctsv','dut_finance'])
    with pytest.raises(ValueError): q.enqueue(['https://evil.test/user-message'])
    with q.db() as db: assert db.execute('SELECT COUNT(*) FROM lookup').fetchone()[0]==2
    limited=LookupQueue(tmp_path/'limited',capacity=1)
    assert limited.enqueue(['dut_ctsv','dut_finance'])
    with limited.db() as db: assert db.execute('SELECT COUNT(*) FROM lookup').fetchone()[0]==1


def test_missing_scope_trigger_and_fixture_replay_isolation(tmp_path):
    from backend.app.services.corpus import build_corpus
    from backend.app.services.retrieve import Retriever
    s,entry=source_packet(tmp_path)
    chunks,manifest=build_corpus([s]); runtime=Retriever([s],chunks,manifest)
    c=claim_for(s); b=runtime.retrieve_claim(c,runtime.corpus_version,datetime.now(timezone.utc))
    assert missing_authorities([c],[b])==[]
    wrong=c.model_copy(deep=True); wrong.scope.program='Another public programme https://evil.test/private'
    assert missing_authorities([wrong],[b])==['dut_ctsv']
    jobs=Jobs(Settings(_env_file=None,app_mode='live',source_lookup_enabled=True,source_sync_state=tmp_path/'q'))
    assert jobs.discover_missing([wrong],[b])
    assert not jobs.discover_missing([wrong],[b])
    with jobs._lookup.db() as db:
        assert 'evil.test' not in str([dict(r) for r in db.execute('SELECT * FROM lookup')])
    for mode in ('fixture','replay'):
        jobs=Jobs(Settings(_env_file=None,app_mode=mode,source_lookup_enabled=True,source_sync_state=tmp_path/mode))
        assert not jobs.discover_missing([wrong],[b])
        assert not (tmp_path/mode).exists()


@pytest.mark.parametrize('missing',[False,True])
def test_concurrent_live_check_pins_snapshot_and_new_job_adopts_publication(tmp_path,monkeypatch,missing):
    a,ea=source_packet(tmp_path); one,reg1=inputs(tmp_path,[a],[ea]); store=tmp_path/'store'
    v1=publish(store,one,reg1,root=tmp_path)
    settings=Settings(_env_file=None,app_mode='live',llm_live_enabled=True,gemini_api_key='synthetic-only',
        source_sync_store=store,database_path=tmp_path/'db.sqlite3',private_dir=tmp_path/'private',
        source_lookup_enabled=True,source_sync_state=tmp_path/'queue')
    initialize(settings.database_path)
    jobs=Jobs(settings); jobs.initialize()
    c=claim_for(a)
    if missing: c.scope.program='Another public programme'
    entered,release=Event(),Event(); calls=[]
    async def invoke(self,contents,config):
        is_extract='claims' in config.response_json_schema['properties']
        calls.append(is_extract)
        if is_extract:
            entered.set(); assert release.wait(5)
            output=dict(claims=[c.model_dump(mode='json')],warnings=[])
        else:
            output=dict(drafts=[dict(claim_id=c.claim_id,label='insufficient_evidence',
                reason_codes=['PARTIAL_EVIDENCE'],explanation='Synthetic provider',temporal_status='unknown',evidence=[])])
        return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(
            parts=[types.Part(text=json.dumps(output))]),finish_reason='STOP')],
            usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=40,candidates_token_count=40,total_token_count=80))
    monkeypatch.setattr(GeminiAdapter,'_invoke',invoke)
    request=CheckCreate(schema_version='1.0',input_mode='text',confirmed_text=c.statement,
        asset_id=None,asset_token=None,as_of=datetime.now(timezone.utc),consent_to_process=True)
    created=jobs.create(request); key=str(created.check.check_id)
    worker=Thread(target=jobs.run,args=(key,)); worker.start()
    try:
        assert entered.wait(5)
        b,eb=source_packet(tmp_path,text='Học bổng Alpha 2026 phiên bản cập nhật.')
        two,reg2=inputs(tmp_path,[a,b],[ea,eb],'2'); v2=publish(store,two,reg2,root=tmp_path)
        assert jobs.runtime().retriever.corpus_version==v2
    finally:
        release.set(); worker.join(5)
    result=jobs.get(key,created.access_token)
    assert result.status=='completed',result.error
    assert result.result.corpus_version==v1 and len(calls)==2
    assert any('xếp hàng' in warning for warning in result.result.warnings)==missing
    if missing:
        assert result.result.claims[0].label=='insufficient_evidence'
        assert jobs._lookup.take()=='dut_ctsv'
    assert jobs.runtime().retriever.corpus_version==v2
    assert jobs.source(a.version_id).text==a.text
    # Stored result is immutable after publication.
    assert jobs.get(key,created.access_token).result.corpus_version==v1


def test_source_family_cannot_split_and_alias_cannot_duplicate_evidence(tmp_path):
    a,ea=source_packet(tmp_path)
    b,eb=source_packet(tmp_path,text='Học bổng Alpha gia hạn.')
    b.family_id='another-family'
    snapshot,register=inputs(tmp_path,[a,b],[ea,eb])
    with pytest.raises(ValueError,match='split_source_family'): publish(tmp_path/'store',snapshot,register,root=tmp_path)
    b,eb=source_packet(tmp_path,url=NOTICE[:-2]+'100')
    snapshot,register=inputs(tmp_path,[a,b],[ea,eb])
    with pytest.raises(ValueError,match='duplicate_canonical'): publish(tmp_path/'store',snapshot,register,root=tmp_path)


def test_fee_amendment_and_unread_attachment_require_actual_review_evidence(tmp_path):
    state,s,entry,packet=reviewed_candidate(tmp_path)
    path=state/packet['candidate_path']/'receipt.json'
    candidate=json.loads(path.read_text())
    candidate['review_reasons']=['unread_attachment','amendment_relationship_review']
    candidate['extraction_complete']=False
    path.write_text(json.dumps(candidate))
    packet['candidate_receipt_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError,match='human_review_required'):
        validate_reviews([s],{'sources':[entry]},[packet],state,AuthorityRegistry(),root=tmp_path)
    packet['human_review']=dict(identity='Synthetic human fixture, not a real reviewer',kind='human',
                               confirmed=True,evidence='Synthetic evidence only')
    with pytest.raises(ValueError,match='attachment_review_required'):
        validate_reviews([s],{'sources':[entry]},[packet],state,AuthorityRegistry(),root=tmp_path)


def test_scheduler_start_tick_stop_and_disabled_mode(tmp_path,monkeypatch):
    from scripts.sync_sources import daemon
    calls=[]
    def run(*a,**k):
        calls.append(k)
        return dict(run_id='synthetic-run',status='no_change',request_count=0)
    def stop(seconds): raise KeyboardInterrupt()
    monkeypatch.setattr('scripts.sync_sources.run_once',run)
    monkeypatch.setattr('scripts.sync_sources.time.sleep',stop)
    config=dict(interval_seconds=3600,poll_seconds=10)
    with pytest.raises(KeyboardInterrupt): daemon(tmp_path,AuthorityRegistry(),config)
    assert len(calls)==1
    assert json.loads((tmp_path/'scheduler.json').read_text())['status']=='stopped'
    # Restart respects the saved interval and does not perform a second periodic fetch.
    with pytest.raises(KeyboardInterrupt): daemon(tmp_path,AuthorityRegistry(),config)
    assert len(calls)==1
    q=LookupQueue(tmp_path); assert q.enqueue(['dut_ctsv'])
    with pytest.raises(KeyboardInterrupt): daemon(tmp_path,AuthorityRegistry(),config)
    assert calls[-1]['authority_ids']==['dut_ctsv']
    with q.db() as db: assert db.execute('SELECT state FROM lookup').fetchone()[0]=='done'


def test_queue_concurrent_enqueues_only_one_task(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    q=LookupQueue(tmp_path)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _:q.enqueue(['dut_ctsv']),range(20)))
    assert sum(results)==1


def test_source_api_retains_old_citation_after_rollback(tmp_path):
    a,ea=source_packet(tmp_path); one,reg1=inputs(tmp_path,[a],[ea]); store=tmp_path/'store'
    v1=publish(store,one,reg1,root=tmp_path)
    b,eb=source_packet(tmp_path,text='Học bổng Alpha gia hạn tới ngày khác.')
    two,reg2=inputs(tmp_path,[a,b],[ea,eb],'2'); publish(store,two,reg2,root=tmp_path)
    activate(store,v1)
    (store/'snapshots'/('corpus-'+'0'*64)).mkdir()  # Corrupt unrelated archive must not mask valid citation.
    settings=Settings(_env_file=None,app_mode='live',source_sync_store=store,database_path=tmp_path/'db.sqlite3')
    initialize(settings.database_path)
    with TestClient(create_app(settings)) as client:
        assert client.get('/api/v1/health').json()['corpus_version']==v1
        assert client.get('/api/v1/sources/'+b.version_id).json()['text']==b.text
        assert client.get('/api/v1/sources/../../private').status_code==404


def test_reviewed_same_family_amendment_can_publish_without_inferred_supersedes(tmp_path):
    from backend.tests.test_source_sync import site_reply, notice_html
    a,ea=source_packet(tmp_path); one,reg1=inputs(tmp_path,[a],[ea]); store=tmp_path/'store'
    publish(store,one,reg1,root=tmp_path)
    state=tmp_path/'state'
    text='Học bổng Alpha 2026 cấp 6 triệu đồng.'
    result=run_sync(state,lambda r:site_reply(r,notice_body=notice_html(text)))
    path=state/result['notices'][0]['candidate_path']
    candidate=json.loads((path/'receipt.json').read_text())
    b,eb=source_packet(tmp_path,text=text,retrieved=candidate['first_seen'])
    eb['ingest']['raw']=dict(path=str((path/'sanitized.html').relative_to(tmp_path)),sha256=candidate['sanitized_html_sha256'])
    packet=dict(version_id=b.version_id,candidate_path=str(path.relative_to(state)),
        candidate_receipt_sha256=hashlib.sha256((path/'receipt.json').read_bytes()).hexdigest(),
        reviewer_identity=b.verified_by,reviewer_kind='agent',text_sha256=b.content_sha256,
        gates={k:dict(passed=True,evidence='Synthetic evidence') for k in GATES},
        family_review=dict(family_id='alpha',evidence='Same public programme; no proven replacement'))
    two,reg2=inputs(tmp_path,[a,b],[ea,eb],'2'); reviews=tmp_path/'reviews.json'; reviews.write_text(json.dumps([packet]))
    with pytest.raises(ValueError,match='critical_update_human_review_required'):
        publish_reviewed(store,two,reg2,reviews,state,AuthorityRegistry(),root=tmp_path)
    packet['human_review']=dict(identity='Synthetic human fixture',kind='human',confirmed=True,evidence='Synthetic full update review')
    reviews.write_text(json.dumps([packet]))
    publish_reviewed(store,two,reg2,reviews,state,AuthorityRegistry(),root=tmp_path)
    sources,_,_=load_corpus(active_directory(store))
    assert len(sources)==2 and {s.family_id for s in sources}=={'alpha'}
    assert all(s.supersedes_version_id is None for s in sources)


def test_post_replace_failure_restores_previous_active_pointer(tmp_path,monkeypatch):
    from backend.app.services import corpus_store
    a,ea=source_packet(tmp_path); one,reg1=inputs(tmp_path,[a],[ea]); store=tmp_path/'store'
    publish(store,one,reg1,root=tmp_path); before=(store/'active.json').read_bytes()
    b,eb=source_packet(tmp_path,text='Học bổng Alpha cập nhật.')
    two,reg2=inputs(tmp_path,[a,b],[ea,eb],'2')
    sync_dir=corpus_store.sync_directory
    def fail_after_replace(path):
        if path==store: raise OSError('synthetic directory sync failure')
        return sync_dir(path)
    monkeypatch.setattr(corpus_store,'sync_directory',fail_after_replace)
    with pytest.raises(OSError): publish(store,two,reg2,root=tmp_path)
    assert (store/'active.json').read_bytes()==before


def test_approval_evidence_is_retained_in_manifest_bound_provenance(tmp_path):
    state,s,entry,packet=reviewed_candidate(tmp_path)
    snapshot,register=inputs(tmp_path,[s],[entry]); reviews=tmp_path/'reviews.json'
    reviews.write_text(json.dumps([packet])); store=tmp_path/'store'
    publish_reviewed(store,snapshot,register,reviews,state,AuthorityRegistry(),root=tmp_path)
    _,_,manifest=load_corpus(active_directory(store))
    provenance=manifest['provenance'][s.version_id]['source_sync_review']
    assert provenance['packet']==packet
    assert len(provenance['registry_sha256'])==64


def test_replaying_identical_review_publish_is_idempotent(tmp_path):
    state,s,entry,packet=reviewed_candidate(tmp_path)
    snapshot,register=inputs(tmp_path,[s],[entry]); reviews=tmp_path/'reviews.json'
    reviews.write_text(json.dumps([packet])); store=tmp_path/'store'
    first=publish_reviewed(store,snapshot,register,reviews,state,AuthorityRegistry(),root=tmp_path)
    before=(store/'active.json').read_bytes()
    assert publish_reviewed(store,snapshot,register,reviews,state,AuthorityRegistry(),root=tmp_path)==first
    assert (store/'active.json').read_bytes()==before
    packet['gates']['facts']['evidence']='Different review'
    reviews.write_text(json.dumps([packet]))
    with pytest.raises(ValueError,match='review_history'):
        publish_reviewed(store,snapshot,register,reviews,state,AuthorityRegistry(),root=tmp_path)


def test_concurrent_publication_lock_keeps_active_snapshot(tmp_path):
    from backend.app.services.source_sync import exclusive
    a,ea=source_packet(tmp_path); one,reg1=inputs(tmp_path,[a],[ea]); store=tmp_path/'store'
    first=publish(store,one,reg1,root=tmp_path)
    with exclusive(store,'publish.lock'):
        with pytest.raises(ValueError,match='sync_busy'): publish(store,one,reg1,root=tmp_path)
    assert active_directory(store).name==first
