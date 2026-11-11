"""Real local process lifecycle with a future schedule: no DUT or model network."""
import json
import time

import pytest

from backend.app.services.corpus import ROOT
from backend.app.services.source_scheduler import start_scheduler, stop_scheduler, scheduler_status


def test_real_scheduler_process_lock_heartbeat_stop_restart_retains_schedule(tmp_path):
    state=tmp_path/'state';state.mkdir()
    due=time.time()+86400
    (state/'schedule.json').write_text(json.dumps({'next_run':due}))
    config=tmp_path/'config.json'
    config.write_text(json.dumps(dict(interval_seconds=3600,poll_seconds=1,
        max_pages=1,max_notices=1,max_requests=4,max_seconds=5)))
    registry=ROOT/'config/source_authorities.json'
    try:
        first=start_scheduler(state,tmp_path/'store',config,registry)
        assert first['process_alive'] and first['lock_held']
        assert first['receipt']['cycle_count']==0
        assert first['heartbeat_age_seconds']<5
        with pytest.raises(ValueError,match='already_running'):
            start_scheduler(state,tmp_path/'store',config,registry)
        stopped=stop_scheduler(state)
        assert not stopped['process_alive'] and not stopped['lock_held']
        assert stopped['receipt']['status']=='stopped'
        second=start_scheduler(state,tmp_path/'store',config,registry)
        assert second['process_alive'] and second['receipt']['restart_count']==1
        assert second['receipt']['pid']!=first['receipt']['pid']
        assert json.loads((state/'schedule.json').read_text())['next_run']==due
        assert second['receipt']['cycle_count']==0
    finally:
        stop_scheduler(state)


def test_stale_receipt_cannot_claim_running_or_kill_reused_pid(tmp_path):
    import os
    (tmp_path/'scheduler.json').write_text(json.dumps(dict(pid=os.getpid(),
        process_identity='old-boot:wrong-tick',status='running',heartbeat_unix=time.time())))
    status=scheduler_status(tmp_path)
    assert not status['process_alive']
    assert not stop_scheduler(tmp_path)['process_alive']


def test_run_once_drains_real_collector_result_into_review_only_with_policy(tmp_path,monkeypatch):
    from scripts.sync_sources import run_once
    from backend.app.services.source_authority import AuthorityRegistry
    from backend.tests.test_source_sync import fetcher,site_reply
    calls=[]
    monkeypatch.setattr('scripts.sync_sources.SafeFetcher',lambda *a,**k:fetcher(site_reply))
    monkeypatch.setattr('backend.app.services.source_review.review_candidates',
        lambda state,store,registry,policy:calls.append((state,store,policy)) or dict(approved=[],pending=[]))
    policy=tmp_path/'policy.json';policy.write_text(json.dumps({'synthetic':True}))
    config=dict(max_requests=10,max_seconds=10,max_pages=1,max_notices=1,
        review_policy_path=str(policy),store=str(tmp_path/'store'))
    receipt=run_once(tmp_path/'state',AuthorityRegistry(),config)
    assert calls==[(tmp_path/'state',tmp_path/'store',{'synthetic':True})]
    assert 'review' in receipt
    calls.clear()
    run_once(tmp_path/'state',AuthorityRegistry(),config,dry_run=True)
    assert not calls


def test_interrupted_on_demand_cycle_preserves_lease_for_restart(tmp_path,monkeypatch):
    from scripts.sync_sources import daemon
    from backend.app.services.source_authority import AuthorityRegistry
    from backend.app.services.source_lookup import LookupQueue
    state=tmp_path/'state';state.mkdir()
    (state/'schedule.json').write_text(json.dumps({'next_run':time.time()+86400}))
    q=LookupQueue(state);assert q.enqueue(['dut_ctsv'])
    def interrupt(*a,**k): raise KeyboardInterrupt()
    monkeypatch.setattr('scripts.sync_sources.run_once',interrupt)
    with pytest.raises(KeyboardInterrupt):
        daemon(state,AuthorityRegistry(),dict(interval_seconds=3600,poll_seconds=1))
    with q.db() as db:
        row=db.execute('SELECT state,lease_until FROM lookup').fetchone()
        assert row['state']=='running' and row['lease_until']>time.time()


def test_review_failure_is_visible_without_losing_collection_checkpoint(tmp_path,monkeypatch):
    from scripts.sync_sources import run_once
    from backend.app.services.source_authority import AuthorityRegistry
    from backend.tests.test_source_sync import fetcher,site_reply
    monkeypatch.setattr('scripts.sync_sources.SafeFetcher',lambda *a,**k:fetcher(site_reply))
    def fail(*a,**k): raise ValueError('synthetic_publication_failure')
    monkeypatch.setattr('backend.app.services.source_review.review_candidates',fail)
    policy=tmp_path/'policy.json';policy.write_text('{}')
    state=tmp_path/'state'
    receipt=run_once(state,AuthorityRegistry(),dict(max_requests=10,max_seconds=10,max_pages=1,max_notices=1,
        review_policy_path=str(policy)))
    assert receipt['fetched']==1 and receipt['review']==dict(status='failed',reason='synthetic_publication_failure')
    assert json.loads((state/'runs'/(receipt['run_id']+'.json')).read_text())['review']==receipt['review']


def test_restart_retains_last_cycle_receipt_in_heartbeat(tmp_path,monkeypatch):
    from scripts.sync_sources import daemon
    from backend.app.services.source_authority import AuthorityRegistry
    (tmp_path/'schedule.json').write_text(json.dumps({'next_run':time.time()+86400}))
    (tmp_path/'scheduler.json').write_text(json.dumps(dict(cycle_count=3,restart_count=1,
        last_run_id='synthetic-history',last_run_status='partial',last_authority_ids=['dut_ctsv'])))
    def stop(*a): raise KeyboardInterrupt()
    monkeypatch.setattr('scripts.sync_sources.time.sleep',stop)
    with pytest.raises(KeyboardInterrupt):daemon(tmp_path,AuthorityRegistry(),dict(interval_seconds=3600,poll_seconds=1))
    receipt=json.loads((tmp_path/'scheduler.json').read_text())
    assert receipt['last_run_id']=='synthetic-history' and receipt['last_authority_ids']==['dut_ctsv']
    assert receipt['cycle_count']==3 and receipt['restart_count']==2
