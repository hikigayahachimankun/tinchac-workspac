from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.main import create_app


def test_release_serves_ui_and_assets_but_preserves_api_and_private_boundary(tmp_path):
    dist = tmp_path/'dist'
    dist.mkdir(); (dist/'assets').mkdir()
    (dist/'index.html').write_text('<html>TinChắc release</html>')
    (dist/'assets/app.js').write_text('console.log("fixture")')
    (tmp_path/'secret.txt').write_text('private-secret')
    (dist/'leak.txt').symlink_to(tmp_path/'secret.txt')
    settings = Settings(_env_file=None, frontend_dist=dist, database_path=tmp_path/'db.sqlite3', private_dir=tmp_path/'private')
    initialize(settings.database_path)
    with TestClient(create_app(settings)) as client:
        assert client.get('/').text == '<html>TinChắc release</html>'
        assert client.get('/check/example').status_code == 200
        assert client.get('/assets/app.js').status_code == 200
        assert client.head('/assets/app.js').status_code == 200
        assert client.get('/api/v1/health').json()['run_mode'] == 'fixture'
        for path in ('/api/v1/missing','/api/v2/missing','/.env','/data/private/db.sqlite3',
                     '/leak.txt','/assets/missing.js','/assets/%2e%2e/%2e%2e/secret.txt'):
            response = client.get(path)
            assert response.status_code == 404, path
            assert 'private-secret' not in response.text
            assert response.json()['error']['code'] == 'RESOURCE_NOT_FOUND'


def test_static_release_must_be_explicit_and_built(tmp_path):
    settings = Settings(_env_file=None, frontend_dist=tmp_path/'missing-dist',database_path=tmp_path/'missing.db',private_dir=tmp_path/'private')
    with TestClient(create_app(settings)) as client:
        assert client.get('/').status_code == 404


def test_spa_fallback_cannot_follow_index_symlink_outside_dist(tmp_path):
    dist=tmp_path/'dist';dist.mkdir()
    (tmp_path/'private.html').write_text('private-page')
    (dist/'index.html').symlink_to(tmp_path/'private.html')
    with TestClient(create_app(Settings(_env_file=None,frontend_dist=dist,database_path=tmp_path/'missing.db',private_dir=tmp_path/'private'))) as client:
        assert client.get('/check/example').status_code==404
