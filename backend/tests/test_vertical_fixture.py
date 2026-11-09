from datetime import timedelta
import json
from pathlib import Path
import sqlite3
from threading import Event, Thread

from fastapi.testclient import TestClient
import pytest

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.main import create_app
from backend.app.models import CheckCreate, CheckCreated, CheckRecord, ErrorEnvelope, SourcePublic
from backend.app.services.jobs import Jobs, now

ROOT = Path(__file__).resolve().parents[2]
CASES = [json.loads(line) for line in (ROOT / 'data/fixtures/cases.jsonl').read_text().splitlines()]
INPUT = json.loads((ROOT / 'contracts/examples/check_create.json').read_text())


@pytest.fixture
def app(tmp_path):
    settings = Settings(_env_file=None, database_path=tmp_path / 'jobs.sqlite3')
    initialize(settings.database_path)
    return create_app(settings)


@pytest.mark.parametrize('case', CASES, ids=lambda c: c['case_id'])
def test_create_poll_source_delete(app, case):
    with TestClient(app) as client:
        response = client.post('/api/v1/checks', json=INPUT | {'confirmed_text': case['confirmed_text']})
        assert response.status_code == 202
        created = CheckCreated.model_validate(response.json())
        assert created.check.status == 'queued'
        url = f'/api/v1/checks/{created.check.check_id}'
        headers = {'X-Resource-Token': created.access_token}
        assert client.get(url).status_code == 404
        assert client.get(url, headers={'X-Resource-Token': 'wrong'}).status_code == 404
        assert client.delete(url, headers={'X-Resource-Token': 'wrong'}).status_code == 404
        response = client.get(url, headers=headers)
        assert response.status_code == 200
        record = CheckRecord.model_validate(response.json())
        assert created.access_token not in response.text
        if case['error']:
            assert record.status == 'failed' and record.result is None
            assert record.error.code == case['error']
        else:
            assert record.status == 'completed'
            assert record.result.run_mode == 'fixture'
            for summary in record.result.sources:
                source = SourcePublic.model_validate(client.get('/api/v1/sources/' + summary.version_id).json())
                assert source.is_fixture
                for claim in record.result.claims:
                    for evidence in claim.evidence:
                        chunk = next(c for c in source.chunks if c.chunk_id == evidence.chunk_id)
                        assert chunk.text[evidence.quote_span.start:evidence.quote_span.end] == evidence.quote
        with sqlite3.connect(app.state.settings.database_path) as db:
            stored = db.execute('SELECT token_hash,request FROM checks').fetchone()
            assert stored[0] != created.access_token and stored[1] is None
        assert client.delete(url, headers=headers).status_code == 204
        assert client.get(url, headers=headers).status_code == 404
        assert client.delete(url, headers=headers).status_code == 404
        assert client.get('/api/v1/sources/missing').status_code == 404


def test_transitions_expiry_and_restart(app, monkeypatch):
    jobs = app.state.jobs
    jobs.initialize()
    created = jobs.create(CheckCreate.model_validate(INPUT))
    key = str(created.check.check_id)
    assert jobs.transition(key, 'queued', 'extracting')
    assert not jobs.transition(key, 'queued', 'retrieving')
    restarted = Jobs(app.state.settings)
    restarted.initialize()
    record = restarted.get(key, created.access_token)
    assert record.status == 'failed' and record.error.code == 'JOB_INTERRUPTED'
    restarted.run(key)
    assert restarted.get(key, created.access_token) == record
    monkeypatch.setattr('backend.app.services.jobs.now', lambda: created.check.expires_at)
    with TestClient(app) as client:
        url = '/api/v1/checks/' + key
        assert client.get(url, headers={'X-Resource-Token':'wrong'}).status_code == 404
        response = client.get(url, headers={'X-Resource-Token': created.access_token})
        assert response.status_code == 410
        assert ErrorEnvelope.model_validate(response.json()).error.code == 'RESOURCE_EXPIRED'
        assert not jobs.transition(key, 'failed', 'extracting')
        with jobs.db() as db:
            row = db.execute('SELECT request,record,canceled FROM checks WHERE id=?', (key,)).fetchone()
            assert tuple(row) == (None, None, 1)
        assert client.delete(url, headers={'X-Resource-Token':created.access_token}).status_code == 204
    monkeypatch.setattr('backend.app.services.jobs.now', lambda: created.check.expires_at + timedelta(hours=24))
    with jobs.db() as db:
        jobs.purge(db)
        assert db.execute('SELECT COUNT(*) FROM checks').fetchone()[0] == 0


@pytest.mark.parametrize('expire', [False, True])
def test_late_worker_cannot_restore_deleted_or_expired(app, monkeypatch, expire):
    jobs = app.state.jobs
    jobs.initialize()
    created = jobs.create(CheckCreate.model_validate(INPUT))
    key = str(created.check.check_id)
    entered, release = Event(), Event()
    build = jobs.adapter.build_result
    def pause(*args):
        entered.set()
        assert release.wait(5)
        return build(*args)
    monkeypatch.setattr(jobs.adapter, 'build_result', pause)
    worker = Thread(target=jobs.run, args=(key,))
    worker.start()
    try:
        assert entered.wait(5)
        assert jobs.get(key, created.access_token).status == 'verifying'
        if expire:
            monkeypatch.setattr('backend.app.services.jobs.now', lambda: created.check.expires_at)
        else:
            jobs.delete(key, created.access_token)
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive()
    with jobs.db() as db:
        row = db.execute('SELECT record,request FROM checks WHERE id=?', (key,)).fetchone()
        assert (tuple(row) == (None, None)) if expire else row is None


def test_unexpected_worker_exception_is_safe(app, monkeypatch):
    def fail(*args):
        raise RuntimeError('private text and token must never leak')
    monkeypatch.setattr(app.state.jobs.adapter, 'build_result', fail)
    with TestClient(app) as client:
        created = client.post('/api/v1/checks', json=INPUT).json()
        response = client.get('/api/v1/checks/' + created['check']['check_id'],
                              headers={'X-Resource-Token':created['access_token']})
        record = CheckRecord.model_validate(response.json())
        assert record.status == 'failed' and record.error.code == 'INTERNAL_ERROR'
        assert record.result is None and 'private text' not in response.text


def test_no_live_fallback_and_unknown_fixture(app):
    with TestClient(app) as client:
        app.state.settings.app_mode = 'live'
        assert client.post('/api/v1/checks', json=INPUT).status_code == 503
        assert client.get('/api/v1/sources/' + app.state.jobs.adapter.public.version_id).status_code == 404
        app.state.settings.app_mode = 'fixture'
        response = client.post('/api/v1/checks', json=INPUT | {'confirmed_text':'Văn bản không thuộc mẫu định danh fixture.'})
        created = response.json()
        record = client.get('/api/v1/checks/' + created['check']['check_id'], headers={'X-Resource-Token':created['access_token']}).json()
        assert record['error']['code'] == 'NO_CHECKABLE_CLAIM' and record['result'] is None
        response = client.post('/api/v1/checks', json=INPUT | {'consent_to_process':False})
        assert response.status_code == 422
        ErrorEnvelope.model_validate(response.json())


def test_historical_source_absence_is_completed_nei(app):
    with TestClient(app) as client:
        created = client.post('/api/v1/checks', json=INPUT | {'as_of':'2026-10-31T00:00:00Z'}).json()
        response = client.get('/api/v1/checks/' + created['check']['check_id'],
                              headers={'X-Resource-Token':created['access_token']})
        record = CheckRecord.model_validate(response.json())
        assert record.status == 'completed' and record.error is None
        assert record.result.sources == []
        assert record.result.summary.insufficient_evidence == 1
        assert record.result.claims[0].reason_codes == ['NO_SOURCE']
        assert record.result.claims[0].evidence == []


def test_fixture_catalog_matches_http_selector_texts():
    texts = json.loads((ROOT / 'frontend/src/api/fixture-texts.json').read_text())
    assert {c['case_id'] for c in CASES} == {'mixed','original','supported','nei','failed'}
    for case in CASES:
        assert texts[case['case_id']] == case['confirmed_text']


def test_three_jobs_use_at_most_two_workers(app, monkeypatch):
    from threading import Condition
    jobs = app.state.jobs
    jobs.initialize()
    created = [jobs.create(CheckCreate.model_validate(INPUT)) for _ in range(3)]
    condition, release = Condition(), Event()
    count = 0
    build = jobs.adapter.build_result
    def pause(*args):
        nonlocal count
        with condition:
            count += 1
            condition.notify_all()
        assert release.wait(5)
        return build(*args)
    monkeypatch.setattr(jobs.adapter, 'build_result', pause)
    workers = [Thread(target=jobs.run, args=(str(c.check.check_id),)) for c in created]
    for worker in workers:
        worker.start()
    try:
        with condition:
            assert condition.wait_for(lambda: count == 2, timeout=5)
        statuses = [jobs.get(str(c.check.check_id),c.access_token).status for c in created]
        assert sorted(statuses) == ['queued','verifying','verifying']
    finally:
        release.set()
        for worker in workers:
            worker.join(5)
    assert not any(worker.is_alive() for worker in workers)
    assert all(jobs.get(str(c.check.check_id),c.access_token).status == 'completed' for c in created)


def test_queued_token_header_and_tombstone_cleanup(app, monkeypatch):
    jobs = app.state.jobs
    with TestClient(app) as client:
        created = jobs.create(CheckCreate.model_validate(INPUT))
        key = str(created.check.check_id)
        url = '/api/v1/checks/' + key
        headers = {'X-Resource-Token':created.access_token}
        assert client.get(url, headers=headers).json()['status'] == 'queued'
        assert client.get(url, params={'token':created.access_token}).status_code == 404
        with jobs.db() as db:
            row = db.execute('SELECT * FROM checks WHERE id=?', (key,)).fetchone()
            assert created.access_token not in str(tuple(row))
        monkeypatch.setattr('backend.app.services.jobs.now', lambda: created.check.expires_at)
        assert client.get(url, headers=headers).status_code == 410
        monkeypatch.setattr('backend.app.services.jobs.now', lambda: created.check.expires_at + timedelta(hours=24))
        assert client.get(url, headers=headers).status_code == 404
        with jobs.db() as db:
            # The lookup returning 404 rolled back no sensitive data; sweep owns physical cleanup.
            jobs.purge(db)
            assert db.execute('SELECT COUNT(*) FROM checks').fetchone()[0] == 0
