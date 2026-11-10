What this change does: Rebuilds a local versioned source corpus and returns evidence chunks available at the requested time. It combines word search with character search and keeps exact source hashes and spans. This review assumes one demo process, two worker threads, and a small closed corpus.

The findings below describe the first implementation before fixes. Review covered the T07 files and their callers, not the pre-existing T06 diff. Each finding was fixed in a separate implementation step, then checked again.

**Must fix:**

1. **An ingest can remove old versions** (`scripts/ingest_sources.py`, original lines 119–126; guard now at lines 129–135)
   - **What this is:** Ingest writes the source snapshot, chunks and manifest to an output directory.
   - **Problem:** Build a corpus, then supply a snapshot missing an old version to the same directory. The first implementation silently overwrites that version; historical retrieval loses its source. The regression test failed before the fix.
   - **Fix:** Before writing, reject any missing or changed stored version. Keep all previous versions in an expanded snapshot, or write a separate snapshot directory.
   - **If we skip it:** A later import can erase evidence needed to reproduce earlier checks.

**Should fix:**

2. **A query leaves its SQLite connection open** (`backend/app/services/retrieve.py`, original line 51; closing now at line 53)
   - **What this is:** Each uncached query creates a small private search index in memory.
   - **Problem:** A SQLite connection context commits or rolls back; it does not close the connection. A test kept a reference after retrieval and could still query the supposedly finished database. It failed before the fix.
   - **Fix:** Use `contextlib.closing` around the connection. The same boundary also closes it after an FTS error.
   - **If we skip it:** Repeated requests retain database memory until garbage collection runs.

3. **The raw ingest test fails on a fresh checkout** (`backend/tests/test_retrieval.py`, original lines 241–242)
   - **What this is:** The first integration test replayed the real T02 raw HTML and scan files.
   - **Problem:** Those files live in `data/raw/`, which `.gitignore` excludes. A checkout with the committed normalized snapshots cannot run that test.
   - **Fix:** Generate tiny HTML, PDF and manual-extract inputs inside the test directory. Test committed normalized snapshot rebuilds separately. Keep real raw replay as an explicit local acceptance command.
   - **If we skip it:** A valid checkout reports a broken backend because private local files are absent.

Fix verification: the two added behavior regressions first failed, then passed. All 27 T07 tests pass, including self-contained raw parsers and normalized snapshot rebuilds. Real approved raw files also replay exactly with `--from-raw`; quarantine is skipped.

Final re-review checked availability filtering before both scoring statistics and candidate limits; inclusive UTC boundaries; old and new versions in the same family; explicit reviewed supersession; NFC/hash/source and page spans; cache input/time/version/k identity, expiry, bounds, mutation isolation and two threads. No unresolved finding remains in T07. The 10 fixed public seed probes produce identical orders and scores on replay. This is a technical pilot of five approved families, not a quality result from held-out test data.

Verdict: Ship.

Not checked: production load, owner source spot-check, redistribution rights, additional payment sources (D03), provider calls, gold test, or T08 verdict logic. Final backend/OpenAPI/T04 smoke results are recorded in T07.md. Ship means ready for owner review; T07 is not marked done.
