"""T01 database bootstrap. Resource/job tables are owned by later tasks."""
from contextlib import closing
from pathlib import Path
import sqlite3

DB_VERSION = '1'


def probe_fts(db: sqlite3.Connection) -> None:
    db.execute('CREATE VIRTUAL TABLE temp.fts_probe USING fts5(content)')
    db.execute("INSERT INTO temp.fts_probe VALUES ('tinchac')")
    row = db.execute("SELECT content FROM temp.fts_probe WHERE fts_probe MATCH 'tinchac'").fetchone()
    if row != ('tinchac',):
        raise sqlite3.DatabaseError('FTS5 probe failed')
    db.execute('DROP TABLE temp.fts_probe')


def initialize(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path, timeout=5)) as db, db:
        db.execute('PRAGMA journal_mode=WAL')
        probe_fts(db)
        db.execute('CREATE TABLE IF NOT EXISTS app_metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        db.execute("INSERT OR IGNORE INTO app_metadata VALUES ('db_version', ?)", (DB_VERSION,))
        version = db.execute("SELECT value FROM app_metadata WHERE key='db_version'").fetchone()
        if version != (DB_VERSION,):
            raise sqlite3.DatabaseError('Unsupported database version')


def check_ready(path: Path) -> None:
    # mode=rw prevents a health request from silently creating a missing DB.
    with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=rw', uri=True, timeout=5)) as db, db:
        version = db.execute("SELECT value FROM app_metadata WHERE key='db_version'").fetchone()
        if version != (DB_VERSION,):
            raise sqlite3.DatabaseError('Database not initialized')
        probe_fts(db)
