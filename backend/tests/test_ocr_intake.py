from datetime import timedelta
from io import BytesIO
import json
from pathlib import Path
from threading import Event, Thread

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.main import create_app
from backend.app.models import CheckCreate, OCRResult
from backend.app.services.errors import ServiceError
from backend.app.services.intake import decode_image
from backend.app.services.ocr import extract_image

ROOT = Path(__file__).resolve().parents[2]
TEXTS = json.loads((ROOT / 'frontend/src/api/fixture-texts.json').read_text())
INPUT = json.loads((ROOT / 'contracts/examples/check_create.json').read_text())


def picture(size=(120, 80), format='PNG'):
    out = BytesIO()
    Image.new('RGB', size, 'white').save(out, format=format)
    return out.getvalue()


def ocr(text=None):
    return OCRResult(text=TEXTS['mixed'] if text is None else text, mean_confidence=90,
                     low_quality=not bool(text), warnings=[], duration_ms=1)


@pytest.fixture
def app(tmp_path, monkeypatch):
    settings = Settings(_env_file=None, database_path=tmp_path/'db.sqlite3', private_dir=tmp_path/'private')
    initialize(settings.database_path)
    monkeypatch.setattr('backend.app.services.intake.extract_image', lambda *a, **k: ocr())
    return create_app(settings)


@pytest.mark.parametrize('fmt,mime', [('PNG','image/png'),('JPEG','image/jpeg')])
def test_decode_real_images(fmt, mime):
    data = picture(format=fmt)
    assert decode_image(data, mime, Settings(_env_file=None)) == data


@pytest.mark.parametrize('data,mime,status', [
    (b'<html>fake.png</html>', 'image/png', 415),
    (picture(), 'image/jpeg', 415), (picture(), 'image/gif', 415),
    (picture()[:45], 'image/png', 415), (picture(format='JPEG')[:-30], 'image/jpeg', 415),
    (b'x'*5242881, 'image/png', 413),
])
def test_invalid_uploads(app, data, mime, status):
    with TestClient(app) as client:
        response = client.post('/api/v1/assets', files={'file':('fake.png', data, mime)})
        assert response.status_code == status
        assert response.json()['schema_version'] == '1.0'
        assert not list(app.state.assets.directory.iterdir())
        with app.state.jobs.db() as db:
            assert db.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 0


def test_pixel_and_byte_limits(app):
    app.state.settings.max_image_pixels = 100
    app.state.settings.max_upload_bytes = 1000
    with TestClient(app) as client:
        for data in (picture(), b'x'*1001):
            response = client.post('/api/v1/assets', files={'file':('image.png', data, 'image/png')})
            assert response.status_code == 413
        assert not list(app.state.assets.directory.iterdir())
    settings = Settings(_env_file=None)
    with pytest.raises(ServiceError) as exc:
        decode_image(picture((4001,3000)), 'image/png', settings)
    assert exc.value.status == 413
    assert decode_image(picture((4000,3000)), 'image/png', settings)


def test_chunked_multipart_body_bound(app):
    with TestClient(app) as client:
        def chunks():
            yield b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="x.png"\r\nContent-Type: image/png\r\n\r\n'
            for _ in range(90):
                yield b'x'*65536
            yield b'\r\n--boundary--\r\n'
        response = client.post('/api/v1/assets', content=chunks(), headers={'Content-Type':'multipart/form-data; boundary=boundary'})
        assert response.status_code == 413
        assert response.json()['error']['code'] == 'INPUT_TOO_LARGE'


def upload(client):
    response = client.post('/api/v1/assets', files={'file':('../../fake.png', picture(), 'image/png')})
    assert response.status_code == 202
    created = response.json()
    return created, '/api/v1/assets/'+created['asset']['asset_id'], {'X-Resource-Token':created['access_token']}


def test_tokens_confirmed_text_and_delete(app):
    with TestClient(app) as client:
        created, url, headers = upload(client)
        assert created['asset']['status'] == 'queued'
        ready = client.get(url, headers=headers).json()
        assert ready['status'] == 'ready' and ready['ocr']['text'] == TEXTS['mixed']
        assert created['access_token'] not in client.get(url, headers=headers).text
        assert client.get(url, params={'token':created['access_token']}).status_code == 404
        for method in (client.get, client.delete):
            assert method(url).status_code == 404
            assert method(url, headers={'X-Resource-Token':'wrong'}).status_code == 404
        request = INPUT | dict(input_mode='image', asset_id=created['asset']['asset_id'], asset_token='wrong')
        assert client.post('/api/v1/checks', json=request).status_code == 404
        request['asset_token'] = created['access_token']
        for modified, text in [(1,TEXTS['supported']), (0,TEXTS['mixed'])]:
            accepted = client.post('/api/v1/checks', json=request | {'confirmed_text':text}).json()
            record = client.get('/api/v1/checks/'+accepted['check']['check_id'], headers={'X-Resource-Token':accepted['access_token']}).json()
            assert record['status'] == 'completed'
            assert record['result']['summary']['contradicted'] == (0 if modified else 1)
            with app.state.jobs.db() as db:
                assert db.execute('SELECT text_modified FROM checks WHERE id=?', (accepted['check']['check_id'],)).fetchone()[0] == modified
                assert created['access_token'] not in str([tuple(row) for row in db.execute('SELECT * FROM checks')])
        assert not list(app.state.assets.directory.iterdir())
        assert client.delete(url, headers=headers).status_code == 204
        assert client.get(url, headers=headers).status_code == 404
        assert client.post('/api/v1/checks', json=request).status_code == 404
        with app.state.jobs.db() as db:
            assert db.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 0


@pytest.mark.parametrize('failure', ['error','timeout','empty'])
def test_worker_failure_cleanup_and_manual_text(app, monkeypatch, failure):
    paths = []
    def extract(path, **kwargs):
        paths.append(path)
        assert path.exists() and kwargs == {'languages':'vie+eng','timeout':20}
        if failure != 'empty':
            raise RuntimeError('private contents' if failure=='error' else 'Tesseract process timeout')
        return ocr('')
    monkeypatch.setattr('backend.app.services.intake.extract_image', extract)
    with TestClient(app) as client:
        created, url, headers = upload(client)
        record = client.get(url, headers=headers).json()
        assert record['status'] == ('ready' if failure=='empty' else 'failed')
        if failure!='empty':
            assert record['error']['code'] == 'OCR_FAILED' and 'private' not in str(record)
            image = INPUT | dict(input_mode='image',asset_id=created['asset']['asset_id'],asset_token=created['access_token'])
            assert client.post('/api/v1/checks', json=image).status_code == 409
        else:
            assert record['ocr']['text'] == ''
        assert paths and all(not path.exists() for path in paths)
        accepted = client.post('/api/v1/checks', json=INPUT).json()
        assert client.get('/api/v1/checks/'+accepted['check']['check_id'], headers={'X-Resource-Token':accepted['access_token']}).json()['status']=='completed'


@pytest.mark.parametrize('expire', [False, True])
def test_delete_or_expire_during_ocr_cannot_restore(app, monkeypatch, expire):
    with TestClient(app):
        assets=app.state.assets
        created=assets.create(picture(), 'image/png')
        key=str(created.asset.asset_id)
        entered, release = Event(), Event()
        def extract(path, **kwargs):
            entered.set()
            assert release.wait(5)
            return ocr()
        monkeypatch.setattr('backend.app.services.intake.extract_image', extract)
        worker=Thread(target=assets.run,args=(key,));worker.start()
        try:
            assert entered.wait(5)
            assert assets.get(key, created.access_token).status=='ocr'
            with pytest.raises(ServiceError) as exc:
                app.state.jobs.create(CheckCreate.model_validate(INPUT | dict(input_mode='image',asset_id=key,asset_token=created.access_token)))
            assert exc.value.status==409
            if expire:
                monkeypatch.setattr('backend.app.services.intake.now',lambda:created.asset.expires_at)
            else:
                assets.delete(key,created.access_token)
        finally:
            release.set();worker.join(5)
        assert not worker.is_alive() and not assets.path(key).exists()
        with pytest.raises(ServiceError) as exc:
            assets.get(key,created.access_token)
        assert exc.value.status==(410 if expire else 404)
        with assets.jobs.db() as db:
            row=db.execute('SELECT record FROM assets WHERE id=?',(key,)).fetchone()
            assert (row['record'] is None) if expire else row is None
        if expire:
            with pytest.raises(ServiceError) as exc:
                assets.get(key,'wrong')
            assert exc.value.status==404
            monkeypatch.setattr('backend.app.services.intake.now',lambda:created.asset.expires_at+timedelta(hours=24))
            with assets.jobs.db() as db:
                assets.purge(db)
                assert db.execute('SELECT COUNT(*) FROM assets').fetchone()[0]==0


def test_restart_removes_raw_and_interrupts_queued(app):
    with TestClient(app):
        assets=app.state.assets
        created=assets.create(picture(),'image/png')
        key=str(created.asset.asset_id)
        assert assets.path(key).exists()
        assets.initialize()
        assert not assets.path(key).exists()
        assert assets.get(key,created.access_token).error.code=='JOB_INTERRUPTED'
        assets.run(key)
        assert assets.get(key,created.access_token).status=='failed'


def test_ocr_word_lines_confidence_and_timeout(tmp_path, monkeypatch):
    captured=[]
    def data(path, **kwargs):
        captured.append(kwargs)
        return dict(text=['','Học','bổng','Ngày'], conf=[-1,60,70,80], page_num=[1]*4,block_num=[1]*4,par_num=[1]*4,line_num=[1,1,1,2])
    monkeypatch.setattr('backend.app.services.ocr.pytesseract.image_to_data',data)
    result=extract_image(tmp_path/'local',timeout=2)
    assert result.text=='Học bổng\nNgày' and result.mean_confidence==70
    assert not result.low_quality and captured[0]['timeout']==2 and captured[0]['lang']=='vie+eng'
    monkeypatch.setattr('backend.app.services.ocr.pytesseract.image_to_data',lambda *a,**k:dict(text=[],conf=[],page_num=[],block_num=[],par_num=[],line_num=[]))
    assert extract_image(tmp_path/'local').low_quality


def test_streaming_limit_closes_multipart_spool_files(app, monkeypatch):
    import asyncio
    import httpx
    import starlette.formparsers
    files=[]
    original=starlette.formparsers.SpooledTemporaryFile
    def track(*args, **kwargs):
        file=original(*args, **kwargs)
        files.append(file)
        return file
    monkeypatch.setattr(starlette.formparsers,'SpooledTemporaryFile',track)
    async def run():
        async def chunks():
            yield b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="x.png"\r\nContent-Type: image/png\r\n\r\n'
            for _ in range(90):
                yield b'x'*65536
            yield b'\r\n--boundary--\r\n'
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            return await client.post('/api/v1/assets',content=chunks(),headers={'Content-Type':'multipart/form-data; boundary=boundary'})
    with TestClient(app):
        response=asyncio.run(run())
        assert response.status_code==413
        assert files and all(file.closed for file in files)


def test_storage_failure_removes_raw_upload(app, monkeypatch):
    from contextlib import contextmanager
    with TestClient(app):
        @contextmanager
        def broken():
            raise RuntimeError('simulated storage failure')
            yield
        monkeypatch.setattr(app.state.jobs,'db',broken)
        with pytest.raises(RuntimeError):
            app.state.assets.create(picture(),'image/png')
        assert not list(app.state.assets.directory.iterdir())
