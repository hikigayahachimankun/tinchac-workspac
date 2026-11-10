"""Private local assets for a single-process demo; raw files never enter SQLite."""
from datetime import timedelta
from io import BytesIO
from pathlib import Path
import secrets
from tempfile import NamedTemporaryFile
from threading import BoundedSemaphore
from uuid import uuid4
import warnings

from PIL import Image, UnidentifiedImageError

from ..models import AssetCreated, AssetRecord, ErrorDetail
from .errors import ServiceError
from .jobs import now, token_hash
from .ocr import extract_image


def decode_image(data: bytes, media_type: str, settings) -> bytes:
    if len(data) > min(settings.max_upload_bytes, 5242880):
        raise ServiceError('INPUT_TOO_LARGE', 'Ảnh vượt giới hạn byte.', status=413)
    formats = {'image/png': 'PNG', 'image/jpeg': 'JPEG'}
    if media_type not in formats:
        raise ServiceError('UNSUPPORTED_MEDIA', 'Chỉ nhận PNG/JPEG.', status=415)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as image:
                if image.format != formats[media_type]:
                    raise ServiceError('UNSUPPORTED_MEDIA', 'Định dạng ảnh không khớp MIME.', status=415)
                if image.width * image.height > min(settings.max_image_pixels, 12000000):
                    raise ServiceError('INPUT_TOO_LARGE', 'Ảnh vượt giới hạn pixel.', status=413)
                image.verify()
            with Image.open(BytesIO(data)) as image:
                image.load()  # Force a real decode, including truncated JPEG/PNG data.
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ServiceError('INPUT_TOO_LARGE', 'Ảnh vượt giới hạn pixel.', status=413) from None
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ServiceError('UNSUPPORTED_MEDIA', 'Ảnh hỏng hoặc không phải PNG/JPEG.', status=415) from None
    return data


class Assets:
    def __init__(self, jobs):
        self.jobs = jobs
        self.settings = jobs.settings
        self.directory = self.settings.private_dir / 'uploads'
        self.slots = BoundedSemaphore(min(self.settings.max_concurrent_jobs, 2))

    def path(self, asset_id: str) -> Path:
        return self.directory / asset_id

    def initialize(self):
        self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        with self.jobs.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS assets (
                id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, record TEXT,
                expires_at TEXT NOT NULL, purge_at TEXT NOT NULL)''')
            self.purge(db)
            for row in db.execute('SELECT id,record FROM assets WHERE record IS NOT NULL').fetchall():
                record = AssetRecord.model_validate_json(row['record'])
                if record.status in ('queued', 'ocr'):
                    record.status = 'failed'
                    record.error = ErrorDetail(code='JOB_INTERRUPTED', message='OCR bị gián đoạn; hãy nhập tay.',
                                               retryable=True, details={})
                    db.execute('UPDATE assets SET record=? WHERE id=?', (record.model_dump_json(), row['id']))
        # A single server process owns this directory. Restart never resumes raw images.
        for path in self.directory.iterdir():
            if path.is_file():
                path.unlink(missing_ok=True)

    def purge(self, db):
        stamp = now().isoformat()
        for row in db.execute('SELECT id FROM assets WHERE expires_at<=?', (stamp,)).fetchall():
            self.path(row['id']).unlink(missing_ok=True)
        db.execute('UPDATE assets SET record=NULL WHERE expires_at<=?', (stamp,))
        db.execute('DELETE FROM assets WHERE purge_at<=?', (stamp,))

    def create(self, data: bytes, media_type: str) -> AssetCreated:
        decode_image(data, media_type, self.settings)
        stamp = now()
        expiry = stamp + timedelta(hours=self.settings.resource_ttl_hours)
        record = AssetRecord(schema_version='1.0', asset_id=uuid4(), status='queued', ocr=None, error=None,
                             created_at=stamp, expires_at=expiry)
        key = str(record.asset_id)
        token = secrets.token_urlsafe(32)
        # NamedTemporaryFile provides owner-only permissions, and rename uses only a server UUID.
        try:
            with NamedTemporaryFile(dir=self.directory, delete=False) as temporary:
                temporary.write(data)
            Path(temporary.name).replace(self.path(key))
            with self.jobs.db() as db:
                self.purge(db)
                db.execute('INSERT INTO assets VALUES(?,?,?,?,?)', (key, token_hash(token), record.model_dump_json(),
                           expiry.isoformat(), (expiry + timedelta(hours=self.settings.resource_ttl_hours)).isoformat()))
        except BaseException:
            self.path(key).unlink(missing_ok=True)
            if 'temporary' in locals():
                Path(temporary.name).unlink(missing_ok=True)
            raise
        return AssetCreated(schema_version='1.0', asset=record, access_token=token)

    def authorized(self, db, key: str, token: str):
        self.purge(db)
        row = db.execute('SELECT * FROM assets WHERE id=?', (key,)).fetchone()
        if row is None or not token or not secrets.compare_digest(row['token_hash'], token_hash(token)):
            raise ServiceError('RESOURCE_NOT_FOUND', 'Không tìm thấy ảnh.', status=404)
        return row

    def get(self, key: str, token: str) -> AssetRecord:
        with self.jobs.db() as db:
            row = self.authorized(db, key, token)
        if row['record'] is None:
            raise ServiceError('RESOURCE_EXPIRED', 'Ảnh đã hết hạn.', status=410)
        return AssetRecord.model_validate_json(row['record'])

    def delete(self, key: str, token: str):
        with self.jobs.db() as db:
            self.authorized(db, key, token)
            self.path(key).unlink(missing_ok=True)
            db.execute('DELETE FROM assets WHERE id=?', (key,))

    def run(self, key: str):
        with self.slots:
            try:
                with self.jobs.db() as db:
                    self.purge(db)
                    row = db.execute('SELECT record FROM assets WHERE id=?', (key,)).fetchone()
                    if row is None or row['record'] is None:
                        return
                    record = AssetRecord.model_validate_json(row['record'])
                    if record.status != 'queued':
                        return
                    record.status = 'ocr'
                    db.execute('UPDATE assets SET record=? WHERE id=?', (record.model_dump_json(), key))
                try:
                    record.ocr = extract_image(self.path(key), languages=self.settings.ocr_languages,
                                               timeout=self.settings.ocr_timeout_seconds)
                    record.status = 'ready'
                except Exception:
                    record.status = 'failed'
                    record.error = ErrorDetail(code='OCR_FAILED', message='Không đọc được ảnh; hãy nhập tay.',
                                               retryable=True, details={})
                finally:
                    self.path(key).unlink(missing_ok=True)
                with self.jobs.db() as db:
                    self.purge(db)
                    # DELETE/TTL cannot be undone by a late OCR worker.
                    db.execute('UPDATE assets SET record=? WHERE id=? AND record IS NOT NULL',
                               (record.model_dump_json(), key))
            finally:
                self.path(key).unlink(missing_ok=True)
