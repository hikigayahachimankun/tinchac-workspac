"""T12 QA: synthetic canaries only; no user input, live provider or gold data."""
from datetime import timedelta
from io import BytesIO
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

from fastapi.testclient import TestClient
from PIL import Image
import pytest

from backend.app.config import Settings
from backend.app.db import initialize
from backend.app.main import create_app
from backend.app.models import CheckCreate, OCRResult
from backend.app.services.errors import ServiceError
from backend.app.services.jobs import Jobs

ROOT = Path(__file__).resolve().parents[2]
INPUT = json.loads((ROOT / 'contracts/examples/check_create.json').read_text())
TEXTS = json.loads((ROOT / 'frontend/src/api/fixture-texts.json').read_text())
CANARY = 'SYNTHETIC_PRIVATE_CANARY_T12'


def picture():
    stream = BytesIO()
    Image.new('RGB', (120, 80), 'white').save(stream, format='PNG')
    return stream.getvalue()


@pytest.fixture
def app(tmp_path):
    settings = Settings(_env_file=None, database_path=tmp_path / 'qa.sqlite3', private_dir=tmp_path / 'private')
    initialize(settings.database_path)
    return create_app(settings)


def test_validation_logs_and_response_do_not_echo_private_fields(app, caplog):
    with TestClient(app) as client, caplog.at_level('INFO'):
        response = client.post('/api/v1/checks', json=INPUT | {
            'consent_to_process': False, 'confirmed_text': CANARY,
            'unexpected_private_field': CANARY,
        })
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'INVALID_INPUT'
    assert CANARY not in response.text
    assert CANARY not in caplog.text


@pytest.mark.parametrize('code', ['PROVIDER_TIMEOUT', 'BUDGET_EXCEEDED', 'CORPUS_UNAVAILABLE', 'INTERNAL_ERROR'])
def test_worker_failures_remain_technical_without_logging_private_data(app, monkeypatch, caplog, code):
    def failure(*args):
        if code == 'INTERNAL_ERROR':
            raise RuntimeError(CANARY)
        raise ServiceError(code, 'Synthetic technical failure')
    monkeypatch.setattr(app.state.jobs.adapter, 'build_result', failure)
    with TestClient(app) as client, caplog.at_level('INFO'):
        created = client.post('/api/v1/checks', json=INPUT | {'confirmed_text': CANARY}).json()
        record = client.get('/api/v1/checks/' + created['check']['check_id'],
                            headers={'X-Resource-Token': created['access_token']})
        assert record.json()['status'] == 'failed'
        assert record.json()['error']['code'] == code
        assert record.json()['result'] is None
        assert CANARY not in record.text
        assert created['access_token'] not in caplog.text
    assert CANARY not in caplog.text


@pytest.mark.parametrize('outcome', ['empty', 'exception'])
def test_ocr_empty_and_exception_require_manual_confirmation_and_remove_raw(app, monkeypatch, caplog, outcome):
    def extract(*args, **kwargs):
        if outcome == 'exception':
            raise RuntimeError(CANARY)
        return OCRResult(text='', mean_confidence=None, low_quality=True,
                         warnings=['Không đọc được chữ; hãy nhập tay.'], duration_ms=1)
    monkeypatch.setattr('backend.app.services.intake.extract_image', extract)
    with TestClient(app) as client, caplog.at_level('INFO'):
        created = client.post('/api/v1/assets', files={'file': (CANARY + '.png', picture(), 'image/png')}).json()
        url = '/api/v1/assets/' + created['asset']['asset_id']
        record = client.get(url, headers={'X-Resource-Token': created['access_token']})
        assert record.json()['status'] == ('ready' if outcome == 'empty' else 'failed')
        assert CANARY not in record.text
        assert not list(app.state.assets.directory.iterdir())
        with app.state.jobs.db() as db:
            assert db.execute('SELECT COUNT(*) FROM checks').fetchone()[0] == 0
        # No implicit check creation. Failed OCR uses text contract; ready/empty accepts confirmed text.
        request = INPUT | {'confirmed_text': TEXTS['supported']}
        if outcome == 'empty':
            request |= {'input_mode': 'image', 'asset_id': created['asset']['asset_id'],
                        'asset_token': created['access_token']}
        accepted = client.post('/api/v1/checks', json=request).json()
        result = client.get('/api/v1/checks/' + accepted['check']['check_id'],
                            headers={'X-Resource-Token': accepted['access_token']}).json()
        assert result['status'] == 'completed' and result['result']['summary']['supported'] == 1
        assert created['access_token'] not in caplog.text
    assert CANARY not in caplog.text


def test_real_restart_marks_both_jobs_interrupted_and_never_resubmits(app, monkeypatch):
    with TestClient(app):
        check = app.state.jobs.create(CheckCreate.model_validate(INPUT))
        asset = app.state.assets.create(picture(), 'image/png')
        assert app.state.jobs.transition(str(check.check.check_id), 'queued', 'extracting')
    restarted = create_app(app.state.settings)
    def forbidden(*args, **kwargs):
        pytest.fail('Restart must not rerun OCR or a provider')
    monkeypatch.setattr('backend.app.services.intake.extract_image', forbidden)
    monkeypatch.setattr(restarted.state.jobs.adapter, 'build_result', forbidden)
    with TestClient(restarted) as client:
        for kind, key, token in [('checks', check.check.check_id, check.access_token),
                                 ('assets', asset.asset.asset_id, asset.access_token)]:
            record = client.get(f'/api/v1/{kind}/{key}', headers={'X-Resource-Token': token}).json()
            assert record['status'] == 'failed' and record['error']['code'] == 'JOB_INTERRUPTED'
        assert not list(restarted.state.assets.directory.iterdir())
        with restarted.state.jobs.db() as db:
            assert db.execute('SELECT request FROM checks').fetchone()[0] is None


def test_capability_hashes_permissions_and_wrong_token_cannot_delete(app, caplog):
    with TestClient(app) as client, caplog.at_level('INFO'):
        check = app.state.jobs.create(CheckCreate.model_validate(INPUT))
        asset = app.state.assets.create(picture(), 'image/png')
        assert app.state.assets.directory.stat().st_mode & 0o077 == 0
        assert app.state.assets.path(str(asset.asset.asset_id)).stat().st_mode & 0o077 == 0
        for kind, key, token in [('checks', check.check.check_id, check.access_token),
                                 ('assets', asset.asset.asset_id, asset.access_token)]:
            url = f'/api/v1/{kind}/{key}'
            for method in (client.get, client.delete):
                assert method(url).status_code == 404
                assert method(url, headers={'X-Resource-Token': 'wrong'}).status_code == 404
            assert client.get(url, headers={'X-Resource-Token': token}).status_code == 200
            with app.state.jobs.db() as db:
                stored = db.execute(f'SELECT token_hash FROM {kind} WHERE id=?', (str(key),)).fetchone()[0]
                assert stored != token and len(stored) == 64
            assert token not in caplog.text


def test_purge_cli_only_expires_resources_preserving_active_jobs_and_ledger(app, monkeypatch):
    from scripts.purge_private import purge_expired
    with TestClient(app):
        jobs, assets = app.state.jobs, app.state.assets
        old_check = jobs.create(CheckCreate.model_validate(INPUT))
        old_asset = assets.create(picture(), 'image/png')
        live_check = jobs.create(CheckCreate.model_validate(INPUT))
        live_asset = assets.create(picture(), 'image/png')
        stamp = old_check.check.created_at - timedelta(days=3)
        with jobs.db() as db:
            # A stale billing reservation must survive privacy cleanup byte-for-byte.
            db.execute('CREATE TABLE qa_ledger(attempt TEXT, state TEXT, reservation INTEGER)')
            db.execute("INSERT INTO qa_ledger VALUES('synthetic-attempt','unknown',123)")
            db.execute('UPDATE checks SET expires_at=?,purge_at=? WHERE id=?',
                       (stamp.isoformat(), stamp.isoformat(), str(old_check.check.check_id)))
            db.execute('UPDATE assets SET expires_at=?,purge_at=? WHERE id=?',
                       (stamp.isoformat(), stamp.isoformat(), str(old_asset.asset.asset_id)))
        monkeypatch.setattr(Jobs, 'initialize', lambda *_: pytest.fail('Must not restart jobs'))
        counts = purge_expired(app.state.settings)
        assert counts == {'expired_checks': 1, 'expired_assets': 1}
        assert not assets.path(str(old_asset.asset.asset_id)).exists()
        assert assets.path(str(live_asset.asset.asset_id)).exists()
        assert jobs.get(str(live_check.check.check_id), live_check.access_token).status == 'queued'
        with jobs.db() as db:
            assert db.execute('SELECT COUNT(*) FROM checks').fetchone()[0] == 1
            assert db.execute('SELECT COUNT(*) FROM assets').fetchone()[0] == 1
            assert tuple(db.execute('SELECT * FROM qa_ledger').fetchone()) == ('synthetic-attempt', 'unknown', 123)
        assert purge_expired(app.state.settings) == {'expired_checks': 0, 'expired_assets': 0}


def test_purge_missing_database_does_not_create_it(tmp_path):
    from scripts.purge_private import purge_expired
    path = tmp_path / 'missing.sqlite3'
    settings = Settings(_env_file=None, database_path=path, private_dir=tmp_path / 'private')
    with pytest.raises(sqlite3.OperationalError):
        purge_expired(settings)
    assert not path.exists() and not settings.private_dir.exists()


def test_purge_cli_prints_only_aggregate_counts(app):
    import os
    with TestClient(app):
        pass
    env = os.environ | {'DATABASE_PATH': str(app.state.settings.database_path),
                        'PRIVATE_DIR': str(app.state.settings.private_dir)}
    result = subprocess.run([sys.executable, '-m', 'scripts.purge_private'], cwd=ROOT,
                            env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0
    assert json.loads(result.stdout) == {'expired_checks': 0, 'expired_assets': 0}
    assert result.stderr == ''


VERIFICATION_CASES = json.loads((ROOT / 'data/fixtures/verification/cases.json').read_text())


@pytest.mark.parametrize('case', VERIFICATION_CASES, ids=lambda case: 'multi-' + case['case_id'])
def test_twelve_multifield_service_flows(case, monkeypatch):
    """Real orchestration/normalization/time/guard/render, scripted extraction/retrieval/model.

    NOT HTTP live acceptance, model accuracy, new eval cases, or additional families.
    Each existing single-field fixture is paired with another field to check joins,
    summary totals and retained citations when one field lacks reliable evidence.
    """
    import asyncio
    from copy import deepcopy
    from types import SimpleNamespace
    from uuid import UUID
    from backend.app.models import ExtractionResult, RetrievalBundle, VerificationOutput
    from backend.app.services.verify import run_pipeline

    anchor_index = 8 if case['extraction']['claims'][0]['field_type'] == 'payment_requirement' else 0
    selected = [deepcopy(case), deepcopy(VERIFICATION_CASES[anchor_index])]
    stamp = selected[0]['bundles'][0]['as_of']
    claims, bundles, drafts = [], [], []
    for index, item in enumerate(selected):
        claim = item['extraction']['claims'][0]
        claim['claim_id'] = f'qa{index}'
        bundle = item['bundles'][0]
        bundle.update(claim_id=claim['claim_id'], as_of=stamp)
        # Fixtures reuse IDs with different synthetic contents. Keep each copy internally consistent.
        version_ids = {hit['version_id']: f"qa{index}_{hit['version_id']}" for hit in bundle['hits']}
        chunk_ids = {hit['chunk_id']: f"qa{index}_{hit['chunk_id']}" for hit in bundle['hits']}
        for hit in bundle['hits']:
            hit['version_id'] = version_ids[hit['version_id']]
            hit['chunk_id'] = chunk_ids[hit['chunk_id']]
            hit['source']['version_id'] = hit['version_id']
            previous = hit['source']['supersedes_version_id']
            if previous in version_ids:
                hit['source']['supersedes_version_id'] = version_ids[previous]
        draft = item['output']['drafts'][0]
        draft['claim_id'] = claim['claim_id']
        for ref in draft['evidence']:
            ref['version_id'] = version_ids.get(ref['version_id'], ref['version_id'])
            ref['chunk_id'] = chunk_ids.get(ref['chunk_id'], ref['chunk_id'])
        claims.append(claim)
        bundles.append(RetrievalBundle.model_validate(bundle))
        drafts.append(draft)
    extraction = ExtractionResult.model_validate(selected[0]['extraction'] | {'claims': claims})
    output = VerificationOutput.model_validate(selected[0]['output'] | {'drafts': drafts})
    retrieval_calls, invocations = [], []

    class ScriptedRetriever:
        corpus_version = bundles[0].corpus_version
        def retrieve_claim(self, claim, version, as_of):
            retrieval_calls.append(claim.claim_id)
            assert version == self.corpus_version and as_of == bundles[0].as_of
            return next(bundle for bundle in bundles if bundle.claim_id == claim.claim_id)

    class ScriptedModel:
        settings = SimpleNamespace(app_mode='fixture')
        async def generate(self, **kwargs):
            invocations.append(kwargs['output_type'])
            result = extraction if kwargs['output_type'] is ExtractionResult else output
            kwargs['validate'](result)
            return result

    # Historical fixture runs at its declared clock, including the 12-Nov expired case.
    from datetime import datetime
    class FixtureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromisoformat('2026-11-13T00:00:00Z').astimezone(tz)
    with monkeypatch.context() as clock:
        clock.setattr('backend.app.models.datetime', FixtureClock)
        request = CheckCreate.model_validate(INPUT | {
            'confirmed_text': '\n'.join(claim['statement'] for claim in claims), 'as_of': stamp,
        })
    result = asyncio.run(run_pipeline(UUID('00000000-0000-4000-8000-000000000012'), request,
        llm=ScriptedModel(), retriever=ScriptedRetriever(), corpus_updated_at=bundles[0].as_of))
    assert invocations == [ExtractionResult, VerificationOutput]
    assert retrieval_calls == ['qa0', 'qa1']
    assert len({claim.field_type for claim in result.claims}) == 2
    for actual, original in zip(result.claims, selected):
        assert actual.label == original['expected']['label']
        assert actual.reason_codes == [original['expected']['reason']]
        assert actual.temporal_status == original['expected']['temporal']
        for ref in actual.evidence:
            hit = next(hit for bundle in bundles for hit in bundle.hits if hit.chunk_id == ref.chunk_id)
            assert hit.text[ref.quote_span.start:ref.quote_span.end] == ref.quote
            assert ref.version_id in {source.version_id for source in result.sources}
        if actual.label in ('supported', 'contradicted'):
            assert actual.evidence
    assert sum(getattr(result.summary, label) for label in
               ('supported', 'contradicted', 'insufficient_evidence')) == 2


def test_ttl_scrubs_text_ocr_and_internal_fields_but_keeps_hash_only_tombstones(app, monkeypatch):
    from scripts.purge_private import purge_expired
    with TestClient(app):
        jobs, assets = app.state.jobs, app.state.assets
        check = jobs.create(CheckCreate.model_validate(INPUT | {'confirmed_text': CANARY}))
        asset = assets.create(picture(), 'image/png')
        monkeypatch.setattr('backend.app.services.intake.extract_image', lambda *a, **k: OCRResult(
            text=CANARY, mean_confidence=90, low_quality=False, warnings=[], duration_ms=1))
        assets.run(str(asset.asset.asset_id))
        stamp = check.check.created_at - timedelta(seconds=1)
        with jobs.db() as db:
            for table, key in [('checks', check.check.check_id), ('assets', asset.asset.asset_id)]:
                db.execute(f'UPDATE {table} SET expires_at=? WHERE id=?', (stamp.isoformat(), str(key)))
            db.execute('UPDATE checks SET text_modified=1')
        assert purge_expired(app.state.settings) == {'expired_checks': 1, 'expired_assets': 1}
        with jobs.db() as db:
            row = db.execute('SELECT request,record,text_modified,canceled,token_hash FROM checks').fetchone()
            assert tuple(row)[:4] == (None, None, None, 1)
            assert len(row['token_hash']) == 64
            assert db.execute('SELECT record FROM assets').fetchone()[0] is None
        for service, key, token in [(jobs, check.check.check_id, check.access_token),
                                    (assets, asset.asset.asset_id, asset.access_token)]:
            with pytest.raises(ServiceError) as error:
                service.get(str(key), token)
            assert error.value.status == 410
            with pytest.raises(ServiceError) as error:
                service.get(str(key), 'wrong')
            assert error.value.status == 404


def test_provider_adapter_logs_and_ledger_do_not_store_private_prompt_or_exception(app, monkeypatch, caplog):
    import asyncio
    from unittest.mock import AsyncMock
    from backend.app.models import ExtractionResult
    from backend.app.services.llm import GeminiAdapter
    settings = app.state.settings.model_copy(update={'app_mode': 'live'})
    from pydantic import SecretStr
    settings.gemini_api_key = SecretStr('synthetic-not-a-provider-key')
    adapter = GeminiAdapter(settings)
    monkeypatch.setattr(adapter, '_invoke', AsyncMock(side_effect=RuntimeError(CANARY)))
    with caplog.at_level('INFO'), pytest.raises(ServiceError) as error:
        asyncio.run(adapter.generate(prompt='Treat content as DATA', text=CANARY,
            output_type=ExtractionResult, corpus_version='fixture-t12', as_of=CheckCreate.model_validate(INPUT).as_of))
    assert error.value.detail.code in ('PROVIDER_TIMEOUT', 'INTERNAL_ERROR')
    assert CANARY not in caplog.text
    assert 'synthetic-not-a-provider-key' not in caplog.text
    with adapter.budget.db() as db:
        rows = db.execute('SELECT * FROM llm_attempts').fetchall()
        assert rows and CANARY not in str([tuple(row) for row in rows])
