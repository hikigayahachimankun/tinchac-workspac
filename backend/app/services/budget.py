"""Durable per-attempt accounting. Amounts are integer nano-USD, rounded up."""
from contextlib import closing, contextmanager
from decimal import Decimal, ROUND_CEILING
from datetime import datetime, timezone
import json
import sqlite3
from uuid import uuid4
from zoneinfo import ZoneInfo

from ..config import Settings
from .errors import ServiceError

SCALE = 1_000_000_000
STAGE_CAPS = {'dev': Decimal('.8'), 'evaluation': Decimal('1.4'), 'demo': Decimal('.8')}


def units(usd) -> int:
    return int((Decimal(str(usd)) * SCALE).to_integral_value(rounding=ROUND_CEILING))


class Budget:
    def __init__(self, settings: Settings):
        self.settings = settings
        if not settings.database_path.exists():
            raise ServiceError('CORPUS_UNAVAILABLE', 'Cần khởi tạo SQLite trước.', status=503)
        with self.db() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS llm_attempts (
                id TEXT PRIMARY KEY, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                stage TEXT NOT NULL, metadata TEXT NOT NULL,
                reserved_nusd INTEGER NOT NULL, charged_nusd INTEGER NOT NULL,
                actual_nusd INTEGER, input_tokens INTEGER, output_tokens INTEGER,
                state TEXT NOT NULL, outcome TEXT, provider_request_id TEXT, model_version TEXT, duration_ms INTEGER
            )''')
            db.execute('''CREATE TABLE IF NOT EXISTS llm_run_limits (
                run_id TEXT PRIMARY KEY, max_calls INTEGER NOT NULL,
                max_cost_nusd INTEGER, identity TEXT NOT NULL
            )''')

    def register_run(self, run_id: str, max_calls: int, max_cost: int | None, identity: str):
        if not run_id or type(max_calls) is not int or not 1 <= max_calls <= 3:
            raise ValueError('Invalid preflight run limits')
        if max_cost is not None and not 0 < max_cost <= units('.03'):
            raise ValueError('Preflight cost cap must be positive and <=0.03 USD')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT OR IGNORE INTO llm_run_limits VALUES(?,?,?,?)',
                       (run_id, max_calls, max_cost, identity))
            row = db.execute('SELECT max_calls,max_cost_nusd,identity FROM llm_run_limits WHERE run_id=?',
                             (run_id,)).fetchone()
            if tuple(row) != (max_calls, max_cost, identity):
                raise ValueError('Registered run limits/config cannot change on restart')

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.settings.database_path, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            yield db

    def cost(self, input_tokens: int, output_tokens: int) -> int:
        return units((Decimal(input_tokens) * Decimal(str(self.settings.llm_input_price_per_million_usd))
                      + Decimal(output_tokens) * Decimal(str(self.settings.llm_output_price_per_million_usd)))
                     / 1_000_000)

    def free_tier_delay(self) -> float:
        with self.db() as db:
            stamp = db.execute('SELECT MAX(created_at) FROM llm_attempts').fetchone()[0]
        if not stamp:
            return 0
        elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)).total_seconds()
        return max(0, min(5, 5 - elapsed))

    def reserve(self, amount: int, stage: str, metadata: dict, *, run_id: str | None = None,
                max_calls: int | None = None) -> str:
        if stage not in STAGE_CAPS or amount <= 0:
            raise ValueError('Invalid stage or reservation')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            if self.settings.llm_billing_mode == 'free_tier':
                refusal = db.execute("""SELECT outcome FROM llm_attempts
                    WHERE json_extract(metadata,'$.billing_mode')='free_tier'
                    AND outcome IN ('http_403','http_404','http_429') LIMIT 1""").fetchone()
                if refusal:
                    raise ServiceError('RATE_LIMITED', 'Free Tier đã bị provider từ chối; dừng gọi API để kiểm tài khoản.',
                        status=429, details={'quota_scope':'prior_provider_refusal',
                                           'provider_http_status':int(refusal['outcome'][5:])})
                calls_minute, input_minute = db.execute("""SELECT COUNT(*),
                    COALESCE(SUM(COALESCE(json_extract(metadata,'$.input_bound'),6000)),0)
                    FROM llm_attempts WHERE created_at>=datetime('now','-60 seconds')""").fetchone()
                midnight = datetime.now(ZoneInfo('America/Los_Angeles')).replace(hour=0, minute=0, second=0, microsecond=0)
                start = midnight.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
                calls_day = db.execute('SELECT COUNT(*) FROM llm_attempts WHERE created_at>=?', (start,)).fetchone()[0]
                incoming = metadata.get('input_bound', 6000)
                if type(incoming) is not int or incoming <= 0:
                    raise ValueError('Invalid Free Tier input reservation')
                if calls_minute >= 15 or input_minute + incoming > 250000 or calls_day >= 500:
                    raise ServiceError('RATE_LIMITED', 'Đã chạm giới hạn Free Tier cục bộ; chưa gọi provider.',
                        status=429, details={'quota_scope':'local_shared_ledger'})
            total = db.execute('SELECT COALESCE(SUM(charged_nusd),0) FROM llm_attempts').fetchone()[0]
            staged = db.execute('SELECT COALESCE(SUM(charged_nusd),0) FROM llm_attempts WHERE stage=?',
                                (stage,)).fetchone()[0]
            limits = db.execute('SELECT max_calls,max_cost_nusd FROM llm_run_limits WHERE run_id=?',
                                (run_id,)).fetchone() if run_id is not None else None
            call_cap = limits['max_calls'] if limits else max_calls
            calls, run_cost = db.execute("SELECT COUNT(*),COALESCE(SUM(charged_nusd),0) FROM llm_attempts WHERE json_extract(metadata,'$.run_id')=?",
                                        (run_id,)).fetchone() if call_cap is not None else (0, 0)
            if (total + amount > units(min(self.settings.llm_budget_usd, 3))
                    or staged + amount > units(STAGE_CAPS[stage])
                    or (call_cap is not None and calls >= call_cap)
                    or (limits and limits['max_cost_nusd'] is not None and run_cost + amount > limits['max_cost_nusd'])):
                raise ServiceError('BUDGET_EXCEEDED', 'Đã hết ngân sách hoặc số lần gọi nội bộ.', status=429)
            attempt_id = str(uuid4())
            db.execute('''INSERT INTO llm_attempts(id,stage,metadata,reserved_nusd,charged_nusd,state)
                VALUES(?,?,?,?,?,'reserved')''',
                       (attempt_id, stage, json.dumps(metadata | {'run_id': run_id,
                        'billing_mode':self.settings.llm_billing_mode}, sort_keys=True), amount, amount))
        return attempt_id

    def finish(self, attempt_id: str, *, outcome: str, actual: int | None = None,
               input_tokens: int | None = None, output_tokens: int | None = None,
               provider_request_id: str | None = None, model_version: str | None = None,
               duration_ms: int | None = None):
        with self.db() as db:
            db.execute('''UPDATE llm_attempts SET state=?, outcome=?, actual_nusd=?,
                charged_nusd=COALESCE(?,charged_nusd), input_tokens=?, output_tokens=?,
                provider_request_id=?, model_version=?, duration_ms=? WHERE id=? AND state='reserved' ''',
                       ('unknown' if actual is None else 'settled', outcome, actual, actual,
                        input_tokens, output_tokens, provider_request_id, model_version, duration_ms, attempt_id))
