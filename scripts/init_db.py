"""Run from repository root: python -m scripts.init_db."""
from backend.app.config import Settings
from backend.app.db import initialize


def main():
    initialize(Settings().database_path)
    print('SQLite initialized; FTS5 probe passed.')


if __name__ == '__main__':
    main()
