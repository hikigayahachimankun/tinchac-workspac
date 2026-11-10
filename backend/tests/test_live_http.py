"""Production HTTP flow with local corpus and scripted provider, never live API."""
import json
from pathlib import Path
from threading import Event, Thread

from fastapi.testclient import TestClient
import pytest
from google.genai import types

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.main import create_app
from backend.app.models import CheckCreate, CheckRecord, SourcePublic
from backend.app.services.llm import GeminiAdapter

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def live(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, app_mode='live', llm_live_enabled=True,
        gemini_api_key='test-only', database_path=tmp_path/'db.sqlite3', private_dir=tmp_path/'private')
    initialize(settings.database_path)
    source = next(s for s in json.loads((ROOT/'data/corpus/sources.json').read_text())
                  if s['review_status'] == 'approved' and s['facts'])
    fact = source['facts'][0]
    claim = dict(claim_id='http-target', statement=fact['quote'], input_span=None,
        field_type=fact['field_type'], raw_value=fact['quote'], normalized=fact['normalized'],
        scope=fact['scope'], ambiguities=[])
    request = dict(schema_version='1.0', input_mode='text', confirmed_text=fact['quote'],
        asset_id=None, asset_token=None, as_of='2026-11-10T00:00:00+07:00', consent_to_process=True)
    calls = []

    async def invoke(self, contents, config):
        calls.append((contents, config))
        if 'claims' in config.response_json_schema['properties']:
            output = dict(claims=[claim], warnings=[])
        else:
            output = dict(drafts=[dict(claim_id='http-target', label='insufficient_evidence',
                reason_codes=['PARTIAL_EVIDENCE'], explanation='Scripted offline response', temporal_status='unknown', evidence=[])])
        return types.GenerateContentResponse(candidates=[types.Candidate(
            content=types.Content(parts=[types.Part(text=json.dumps(output))]), finish_reason='STOP')],
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=40, candidates_token_count=40, total_token_count=80),
            model_version='scripted-http')
    monkeypatch.setattr(GeminiAdapter, '_invoke', invoke)
    return create_app(settings), request, source, calls


def test_live_http_runs_production_stages_and_ledger(live):
    app, request, source, calls = live
    with TestClient(app) as client:
        health = client.get('/api/v1/health').json()
        assert health['run_mode'] == 'live'
        assert health['corpus_version'].startswith('corpus-')
        created = client.post('/api/v1/checks', json=request)
        assert created.status_code == 202, created.text
        body = created.json()
        url = '/api/v1/checks/' + body['check']['check_id']
        headers = {'X-Resource-Token':body['access_token']}
        assert client.get(url).status_code == 404
        record = CheckRecord.model_validate(client.get(url, headers=headers).json())
        assert record.status == 'completed', record.error
        assert record.result.run_mode == 'live'
        assert record.result.corpus_version == health['corpus_version']
        assert len(calls) == 2
        assert record.result.usage.attempts == 2
        with app.state.jobs.db() as db:
            attempts = db.execute('SELECT stage, state, metadata FROM llm_attempts').fetchall()
            assert len(attempts) == 2
            assert all(r['stage'] == 'demo' and r['state'] == 'settled' for r in attempts)
            assert all(json.loads(r['metadata'])['run_id'] == body['check']['check_id'] for r in attempts)
            assert db.execute('SELECT request FROM checks').fetchone()[0] is None
        public = client.get('/api/v1/sources/' + source['version_id'])
        assert public.status_code == 200
        snapshot = SourcePublic.model_validate(public.json())
        assert not snapshot.is_fixture and snapshot.text == source['text']
        assert snapshot.chunks
        quarantined = next(s for s in json.loads((ROOT/'data/corpus/sources.json').read_text())
                           if s['review_status'] != 'approved')
        assert client.get('/api/v1/sources/'+quarantined['version_id']).status_code == 404
        assert client.delete(url, headers=headers).status_code == 204


def test_live_requires_explicit_enable_and_valid_corpus(live):
    app, request, source, calls = live
    with TestClient(app) as client:
        app.state.settings.llm_live_enabled = False
        assert client.post('/api/v1/checks', json=request).status_code == 503
        assert calls == []
    other = app.state.settings.model_copy(update={'llm_live_enabled':True,'corpus_dir':Path('/missing-corpus')})
    with TestClient(create_app(other)) as client:
        assert client.get('/api/v1/health').status_code == 503
        assert client.post('/api/v1/checks', json=request).status_code == 503
        assert calls == []


def test_live_provider_failure_remains_technical(live, monkeypatch):
    app, request, source, calls = live
    async def fail(*args):
        raise RuntimeError('private provider text')
    monkeypatch.setattr(GeminiAdapter, '_invoke', fail)
    with TestClient(app) as client:
        body = client.post('/api/v1/checks', json=request).json()
        response = client.get('/api/v1/checks/'+body['check']['check_id'],
            headers={'X-Resource-Token':body['access_token']})
        record = CheckRecord.model_validate(response.json())
        assert record.status == 'failed' and record.result is None
        assert 'private provider text' not in response.text
        with app.state.jobs.db() as db:
            assert db.execute('SELECT state FROM llm_attempts').fetchone()[0] == 'unknown'


@pytest.mark.parametrize('expire', [False, True])
def test_cancel_during_extraction_skips_verification(live, monkeypatch, expire):
    app, request, source, calls = live
    jobs = app.state.jobs
    jobs.initialize()
    entered, release = Event(), Event()
    invoke = GeminiAdapter._invoke
    async def pause(self, *args):
        entered.set()
        assert release.wait(5)
        return await invoke(self, *args)
    monkeypatch.setattr(GeminiAdapter, '_invoke', pause)
    created = jobs.create(CheckCreate.model_validate(request))
    key = str(created.check.check_id)
    worker = Thread(target=jobs.run, args=(key,))
    worker.start()
    try:
        assert entered.wait(5)
        if expire:
            monkeypatch.setattr('backend.app.services.jobs.now', lambda: created.check.expires_at)
        else:
            jobs.delete(key, created.access_token)
    finally:
        release.set()
        worker.join(5)
    assert not worker.is_alive()
    assert len(calls) == 1
    with jobs.db() as db:
        row = db.execute('SELECT record,request FROM checks WHERE id=?', (key,)).fetchone()
        assert (tuple(row) == (None, None)) if expire else row is None
