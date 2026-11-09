import sqlite3

from fastapi import Body
from fastapi.testclient import TestClient
import pytest
from pydantic import ValidationError

from backend.app.config import Settings
from backend.app.db import check_ready, initialize
from backend.app.main import create_app
from backend.app.models import CheckCreate, ErrorEnvelope, HealthResponse


def settings_for(tmp_path):
    return Settings(_env_file=None, database_path=tmp_path/'test.sqlite3', app_mode='fixture', gemini_api_key='')


def test_health_and_init(tmp_path):
    settings = settings_for(tmp_path)
    client = TestClient(create_app(settings))
    response = client.get('/api/v1/health')
    assert response.status_code == 503
    assert ErrorEnvelope.model_validate(response.json()).error.code == 'CORPUS_UNAVAILABLE'
    assert not settings.database_path.exists()
    initialize(settings.database_path)
    initialize(settings.database_path)
    check_ready(settings.database_path)
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    result = HealthResponse.model_validate(response.json())
    assert result.status == 'ok' and result.provider_configured is False
    with sqlite3.connect(settings.database_path) as db:
        assert db.execute('PRAGMA journal_mode').fetchone() == ('wal',)


def test_health_fts_failure(tmp_path, monkeypatch):
    settings = settings_for(tmp_path)
    initialize(settings.database_path)

    def failed_probe(db):
        raise sqlite3.OperationalError('fixture FTS5 unavailable')

    monkeypatch.setattr('backend.app.db.probe_fts', failed_probe)
    response = TestClient(create_app(settings)).get('/api/v1/health')
    assert response.status_code == 503
    ErrorEnvelope.model_validate(response.json())


def test_errors_do_not_echo_input(tmp_path):
    app = create_app(settings_for(tmp_path))

    @app.post('/test-only-validation')
    def validate(body: CheckCreate = Body()):
        return body

    @app.get('/test-only-failure')
    def fail():
        raise RuntimeError('private test text')

    client = TestClient(app, raise_server_exceptions=False)
    response = client.post('/test-only-validation', json={'confirmed_text':'private test text'})
    assert response.status_code == 422
    ErrorEnvelope.model_validate(response.json())
    assert 'private test text' not in response.text
    response = client.get('/test-only-failure')
    assert response.status_code == 500
    assert ErrorEnvelope.model_validate(response.json()).error.code == 'INTERNAL_ERROR'
    assert 'private test text' not in response.text
    assert client.get('/api/v1/checks/missing').status_code == 404
    ErrorEnvelope.model_validate(client.get('/missing').json())


@pytest.mark.parametrize('change', [
    {'app_mode':'invalid'}, {'llm_timeout_seconds':0}, {'llm_budget_usd':-1},
    {'llm_budget_usd':float('inf')}, {'llm_max_retries':2}, {'max_concurrent_jobs':0},
    {'max_upload_bytes':0}, {'resource_ttl_hours':0}, {'max_input_chars':6001},
    {'app_timezone':'UTC'},
])
def test_config_validation(change):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **change)


def test_env_template_and_secret_repr():
    Settings(_env_file='.env.example')
    settings = Settings(_env_file=None, gemini_api_key='fixture-secret-value')
    assert 'fixture-secret-value' not in repr(settings)
