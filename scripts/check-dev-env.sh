#!/usr/bin/env bash
set -eu

missing=0
for tool in git node npm python3.11 codex tesseract; do
  if ! command -v "$tool" >/dev/null; then
    printf 'Missing %s\n' "$tool" >&2
    missing=1
  fi
done
if [ "$missing" -ne 0 ]; then
  exit 1
fi

git --version
node --version
npm --version
python3.11 --version
codex --version
node -e 'const [major, minor] = process.versions.node.split(".").map(Number); if (major !== 22 || minor < 12) { console.error("TinChac expects Node 22.12+ within major 22."); process.exit(1); }'
python3.11 - <<'PY'
import sqlite3

with sqlite3.connect(":memory:") as db:
    db.execute("CREATE VIRTUAL TABLE fts_probe USING fts5(content)")
    db.execute("INSERT INTO fts_probe VALUES ('tinchac')")
    match = db.execute("SELECT content FROM fts_probe WHERE fts_probe MATCH 'tinchac'").fetchone()
    if match != ("tinchac",):
        raise SystemExit("SQLite FTS5 probe failed.")
print("SQLite FTS5 OK")
PY

languages="$(tesseract --list-langs)"
printf '%s\n' "$languages"
for language in vie eng; do
  if ! printf '%s\n' "$languages" | grep -qx "$language"; then
    printf 'Missing Tesseract language %s\n' "$language" >&2
    missing=1
  fi
done
exit "$missing"
