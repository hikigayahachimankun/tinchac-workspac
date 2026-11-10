"""Purge expired resources only; run against the demo's existing SQLite database.

Uses environment Settings without loading .env. Never initializes/resumes jobs,
removes an entire database, or touches billing reservations. Output is counts only.
The application still owns the regular 60-second TTL sweep and orphan cleanup.
"""
from contextlib import closing
import json
import sqlite3
import sys

from backend.app.config import Settings
from backend.app.services.intake import Assets
from backend.app.services.jobs import Jobs, now


def purge_expired(settings: Settings) -> dict[str, int]:
    jobs = Jobs(settings)
    assets = Assets(jobs)
    # rw avoids creating a new empty ledger at a mistyped path.
    uri = settings.database_path.resolve().as_uri() + '?mode=rw'
    with closing(sqlite3.connect(uri, uri=True, timeout=5)) as db, db:
        db.row_factory = sqlite3.Row
        tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'checks', 'assets'} <= tables:
            raise ValueError('Resource tables are not initialized')
        stamp = now().isoformat()
        counts = {f'expired_{table}': db.execute(
            f'SELECT COUNT(*) FROM {table} WHERE expires_at<=?', (stamp,)).fetchone()[0]
            for table in ('checks', 'assets')}
        assets.purge(db)
        jobs.purge(db)
    return counts


def main() -> int:
    try:
        counts = purge_expired(Settings(_env_file=None))
    except (OSError, sqlite3.Error, ValueError):
        # Exception text can contain paths/private values; do not echo it.
        print('Privacy cleanup failed; check the configured database and local permissions.', file=sys.stderr)
        return 1
    print(json.dumps(counts, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
