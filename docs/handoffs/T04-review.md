What this change does:
This connects the existing text UI to FastAPI and a SQLite job. Named fixture cases return scripted results and public snapshots; resource tokens protect polling and deletion. I assumed one local process and a few demo users, with at most two active workers.

**Must fix:**

1. **An unavailable snapshot becomes a worker error** (`backend/app/services/fixture.py:41`)
   - **What this is:** The adapter checks whether the source existed at the requested time.
   - **Problem:** Sending the named amount case with `as_of=2026-10-31T00:00:00Z` returns failed/NO_CHECKABLE_CLAIM. The contract says missing eligible sources are a completed insufficient_evidence result.
   - **Fix:** Clear evidence and sources, change the scripted claims to insufficient_evidence/NO_SOURCE, and recount the summary. Add an HTTP test for a time before source availability.
   - **If we skip it:** A valid historical request appears to be a technical failure.

2. **A UI-only expiry example enters the backend catalog** (`data/fixtures/cases.jsonl`, case `expired`)
   - **What this is:** T03 has a fixed example to show the expired time label.
   - **Problem:** The copied example marks an amount claim expired even with `as_of=2026-11-08`, while the T02 source deadline is 10 November. Copying it into the HTTP adapter presents an inconsistent time result.
   - **Fix:** Keep this presentation-only example in explicit T03 mock mode. Remove it from the backend catalog and HTTP selector. Resource TTL expiry remains covered by T04 tests; real temporal checks belong to T08.
   - **If we skip it:** The API claims expiry before the source deadline.

Verdict: fix 1 and 2 first.
Not checked: live provider, OCR, real retrieval, multi-process hosting, physical phones, and a wall-clock 24-hour expiry wait.

## Resolution and final review

Both findings are fixed. `test_historical_source_absence_is_completed_nei` covers finding 1.
The catalog test pins the five HTTP cases and their UI texts; the expired presentation example remains in explicit T03 mock mode only.

I traced checks routes → job storage and worker → fixture adapter → CheckResult → HTTP client → polling → result/evidence components.
I also read the error handlers, lifespan cleanup, startup commands, OpenAPI export, existing T01/T03 tests and every caller of the changed interfaces.
The final run has 69 backend tests, 11 frontend tests, a passing production build, and 2 real-backend browser smoke tests.
The 4 T03 browser regression tests also passed. The original 38 OpenAPI components are unchanged, and the exported routes match the saved contract.
The resource tests cover token headers, stored hashes, queued state, conditional transitions, two-worker limit, restart interruption, deletion during work, expiry during work, tombstone cleanup and safe unexpected errors.
No remaining findings or lean findings within T04.

Verdict: Ship.
Not checked: real AI quality, live provider/OCR/retrieval, multiple server processes, physical devices, a wall-clock 24-hour wait, or a wall-clock 120-second browser wait. These are outside this fixture review. The owner still decides whether the task is done.
