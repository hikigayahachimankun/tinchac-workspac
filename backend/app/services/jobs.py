"""Single-process demo jobs. SQLite transactions never span provider work."""
import asyncio
from contextlib import closing, contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import sqlite3
from threading import Lock, Semaphore
from uuid import UUID, uuid4

from ..config import Settings
from ..models import CheckCreate, CheckCreated, CheckRecord, CheckStatus, ErrorDetail
from .errors import ServiceError
from .fixture import FixtureAdapter


def now():
    return datetime.now(timezone.utc)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Jobs:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.slots = Semaphore(min(settings.max_concurrent_jobs, 2))
        self.adapter = FixtureAdapter()
        self._runtime = None
        self._runtime_lock = Lock()

    def runtime(self):
        from .runtime import LiveRuntime
        with self._runtime_lock:
            if self._runtime is None:
                self._runtime = LiveRuntime(self.settings.corpus_dir)
            return self._runtime

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.settings.database_path, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            yield db

    def initialize(self):
        with self.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS checks (
                id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, request TEXT,
                record TEXT, expires_at TEXT NOT NULL, purge_at TEXT NOT NULL, canceled INTEGER NOT NULL DEFAULT 0
            )''')
            if 'text_modified' not in {row[1] for row in db.execute('PRAGMA table_info(checks)')}:
                db.execute('ALTER TABLE checks ADD COLUMN text_modified INTEGER')
            self.purge(db)
            for row in db.execute('SELECT id, record FROM checks WHERE canceled=0').fetchall():
                record = CheckRecord.model_validate_json(row['record'])
                if record.status not in ('completed', 'failed'):
                    record.status = CheckStatus.failed
                    record.error = ErrorDetail(code='JOB_INTERRUPTED', message='Job bị gián đoạn khi khởi động lại.',
                                               retryable=True, details={})
                    record.updated_at = now()
                    db.execute('UPDATE checks SET record=?, request=NULL WHERE id=?',
                               (record.model_dump_json(), row['id']))

    def purge(self, db):
        stamp = now().isoformat()
        # Keep a hash-only tombstone for one more TTL, then remove it.
        db.execute('DELETE FROM checks WHERE purge_at<=?', (stamp,))
        db.execute('UPDATE checks SET canceled=1, request=NULL, record=NULL, text_modified=NULL WHERE expires_at<=?', (stamp,))

    def create(self, request: CheckCreate) -> CheckCreated:
        if self.settings.app_mode == 'live':
            if not self.settings.llm_live_enabled or not self.settings.gemini_api_key.get_secret_value():
                raise ServiceError('CORPUS_UNAVAILABLE', 'Live chưa được bật sau preflight và xác nhận ngân sách.', status=503)
            self.runtime()  # Validate the immutable corpus before accepting or charging a job.
        elif self.settings.app_mode != 'fixture':
            raise ServiceError('CORPUS_UNAVAILABLE', 'HTTP replay chưa có phiên ghi được cấu hình; dùng eval replay CLI.', status=503)
        text_modified = None
        if request.input_mode == 'image':
            asset = self.assets.get(str(request.asset_id), request.asset_token)
            if asset.status != 'ready':
                raise ServiceError('ASSET_NOT_READY', 'Ảnh chưa OCR xong; có thể nhập tay qua văn bản.', status=409)
            text_modified = request.confirmed_text != asset.ocr.text
            # Authorization is complete. Do not persist the raw asset capability.
            request = request.model_copy(update={'asset_token': '[validated]'})
        if len(request.confirmed_text) > self.settings.max_input_chars:
            raise ServiceError('INPUT_TOO_LARGE', 'Văn bản vượt giới hạn cấu hình.', status=413)
        stamp = now()
        expiry = stamp + timedelta(hours=self.settings.resource_ttl_hours)
        record = CheckRecord(schema_version='1.0', check_id=uuid4(), status='queued', result=None,
                             error=None, created_at=stamp, updated_at=stamp, expires_at=expiry)
        token = secrets.token_urlsafe(32)
        with self.db() as db:
            self.purge(db)
            db.execute('INSERT INTO checks(id,token_hash,request,record,expires_at,purge_at,text_modified) VALUES(?,?,?,?,?,?,?)',
                       (str(record.check_id), token_hash(token), request.model_dump_json(), record.model_dump_json(),
                        expiry.isoformat(), (expiry + timedelta(hours=self.settings.resource_ttl_hours)).isoformat(), text_modified))
        return CheckCreated(schema_version='1.0', check=record, access_token=token)

    def authorized(self, db, check_id: str, token: str):
        self.purge(db)
        row = db.execute('SELECT * FROM checks WHERE id=?', (check_id,)).fetchone()
        if row is None or not secrets.compare_digest(row['token_hash'], token_hash(token)):
            raise ServiceError('RESOURCE_NOT_FOUND', 'Không tìm thấy phiên kiểm tra.', status=404)
        return row

    def get(self, check_id: str, token: str) -> CheckRecord:
        if not token:
            raise ServiceError('RESOURCE_NOT_FOUND', 'Không tìm thấy phiên kiểm tra.', status=404)
        # Commit expiry cleanup even when returning a 410.
        with self.db() as db:
            row = self.authorized(db, check_id, token)
        if row['record'] is None:
            raise ServiceError('RESOURCE_EXPIRED', 'Phiên kiểm tra đã hết hạn.', status=410)
        return CheckRecord.model_validate_json(row['record'])

    def delete(self, check_id: str, token: str):
        if not token:
            raise ServiceError('RESOURCE_NOT_FOUND', 'Không tìm thấy phiên kiểm tra.', status=404)
        with self.db() as db:
            self.authorized(db, check_id, token)
            # Absence is also the cancellation flag; all worker writes are conditional.
            db.execute('DELETE FROM checks WHERE id=?', (check_id,))

    def transition(self, check_id: str, expected: str, status: str, *, result=None, error=None) -> bool:
        with self.db() as db:
            self.purge(db)
            row = db.execute('SELECT record FROM checks WHERE id=? AND canceled=0', (check_id,)).fetchone()
            if row is None:
                return False
            record = CheckRecord.model_validate_json(row['record'])
            if record.status != expected:
                return False
            data = record.model_dump() | dict(status=status, updated_at=now(), result=result, error=error)
            updated = CheckRecord.model_validate(data)
            terminal = status in ('completed', 'failed')
            changed = db.execute('''UPDATE checks SET record=?, request=CASE WHEN ? THEN NULL ELSE request END
                WHERE id=? AND canceled=0 AND record=?''',
                (updated.model_dump_json(), terminal, check_id, row['record'])).rowcount
            return changed == 1

    def run(self, check_id: str):
        with self.slots:
            stage = 'queued'
            try:
                if not self.transition(check_id, stage, 'extracting'):
                    return
                stage = 'extracting'
                with self.db() as db:
                    self.purge(db)
                    row = db.execute('SELECT request FROM checks WHERE id=? AND canceled=0', (check_id,)).fetchone()
                if row is None:
                    return
                request = CheckCreate.model_validate_json(row['request'])
                if self.settings.app_mode == 'live':
                    asyncio.run(self.run_live(check_id, request))
                    return
                for target in ('retrieving', 'verifying'):
                    if not self.transition(check_id, stage, target):
                        return
                    stage = target
                result = self.adapter.build_result(UUID(check_id), request)
                self.transition(check_id, stage, 'completed', result=result)
            except Exception as exc:
                detail = exc.detail if isinstance(exc, ServiceError) else ErrorDetail(
                    code='INTERNAL_ERROR', message='Lỗi kỹ thuật khi xử lý phiên kiểm tra.', retryable=True, details={})
                self.transition(check_id, stage, 'failed', error=detail)

    async def run_live(self, check_id: str, request: CheckCreate):
        from .extract import extract_claims
        from .llm import GeminiAdapter
        from .verify import limit_bundles, verify_extraction

        stage = 'extracting'
        try:
            runtime = self.runtime()
            llm = GeminiAdapter(self.settings, run_id=check_id)
            extraction = await extract_claims(request, llm=llm, corpus_version=runtime.retriever.corpus_version,
                                               stage='demo', public=False)
            if not self.transition(check_id, stage, 'retrieving'):
                return
            stage = 'retrieving'
            bundles = [runtime.retriever.retrieve_claim(c, runtime.retriever.corpus_version, request.as_of)
                       for c in extraction.claims]
            bundles, clipped = limit_bundles(bundles)
            if clipped:
                extraction.warnings.append('Context giới hạn 6 chunks; có hit bị cắt.')
            if not self.transition(check_id, stage, 'verifying'):
                return
            stage = 'verifying'
            result = await verify_extraction(UUID(check_id), extraction, bundles, llm=llm,
                run_mode='live', corpus_updated_at=runtime.updated_at, stage='demo', public=False)
            self.transition(check_id, stage, 'completed', result=result)
        except Exception as exc:
            detail = exc.detail if isinstance(exc, ServiceError) else ErrorDetail(
                code='INTERNAL_ERROR', message='Lỗi kỹ thuật khi xử lý phiên kiểm tra.', retryable=True, details={})
            self.transition(check_id, stage, 'failed', error=detail)
