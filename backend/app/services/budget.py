"""Durable per-attempt accounting. Amounts are integer nano-USD, rounded up."""
from contextlib import closing, contextmanager
from decimal import Decimal, ROUND_CEILING
import json
import sqlite3
from uuid import uuid4

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

    @contextmanager
    def db(self):
        with closing(sqlite3.connect(self.settings.database_path, timeout=5)) as db, db:
            db.row_factory = sqlite3.Row
            yield db

    def cost(self, input_tokens: int, output_tokens: int) -> int:
        return units((Decimal(input_tokens) * Decimal(str(self.settings.llm_input_price_per_million_usd))
                      + Decimal(output_tokens) * Decimal(str(self.settings.llm_output_price_per_million_usd)))
                     / 1_000_000)

    def reserve(self, amount: int, stage: str, metadata: dict, *, run_id: str | None = None,
                max_calls: int | None = None) -> str:
        if stage not in STAGE_CAPS or amount <= 0:
            raise ValueError('Invalid stage or reservation')
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            total = db.execute('SELECT COALESCE(SUM(charged_nusd),0) FROM llm_attempts').fetchone()[0]
            staged = db.execute('SELECT COALESCE(SUM(charged_nusd),0) FROM llm_attempts WHERE stage=?',
                                (stage,)).fetchone()[0]
            calls = db.execute("SELECT COUNT(*) FROM llm_attempts WHERE json_extract(metadata,'$.run_id')=?",
                               (run_id,)).fetchone()[0] if max_calls is not None else 0
            if (total + amount > units(min(self.settings.llm_budget_usd, 3))
                    or staged + amount > units(STAGE_CAPS[stage])
                    or (max_calls is not None and calls >= max_calls)):
                raise ServiceError('BUDGET_EXCEEDED', 'Đã hết ngân sách hoặc số lần gọi nội bộ.', status=429)
            attempt_id = str(uuid4())
            db.execute('''INSERT INTO llm_attempts(id,stage,metadata,reserved_nusd,charged_nusd,state)
                VALUES(?,?,?,?,?,'reserved')''',
                       (attempt_id, stage, json.dumps(metadata | {'run_id': run_id}, sort_keys=True), amount, amount))
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
