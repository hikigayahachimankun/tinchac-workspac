# T12 — self-review theo ponytail-review

What this change does: T12 adds offline checks for error paths and private data handling. A small cleanup command removes expired resource data using the same TTL rules as the app. With the owner's approval, the HTTP client now rejects malformed results before React renders them.

Reviewed: the new T12 tests, `scripts/purge_private.py`, and only the T12 addition to `frontend/src/api/client.ts`. Traced request → Jobs/Assets → SQLite, asset OCR cleanup, provider logging/reservations, client → App → ResultTable/EvidencePanel. Assumed one local demo process with at most two workers. This is a self-review, not an independent review or owner acceptance.

**Must fix (found and fixed):**

1. **A malformed successful response crashes the result page** (`frontend/src/api/client.ts:81`, caller `frontend/src/components/ResultTable.tsx:9`).
   - **What this is:** The client checks HTTP JSON before storing it in React state.
   - **Problem:** It accepted `completed` with `summary: null`, missing warnings, or an invalid timestamp. The browser reproduced a TypeError and lost the result page instead of showing a technical error.
   - **Fix:** Check the fields the UI reads, timestamps, summary counts, citation relations and source IDs. Reject invalid data with ApiError; never repair labels or silently remove evidence. The owner explicitly approved editing the existing upstream client file after the proposal in D18.
   - **If we skip it:** A broken API response can blank the demo. The final T12 unit and browser regressions require a visible technical error with zero verdict rows and zero page errors.

2. **An inherited property is accepted as an error code** (`frontend/src/api/client.ts:69`).
   - **What this is:** Error codes select a Vietnamese error message from an object.
   - **Problem:** Using `code in errorMessages` accepts `toString`. Rendering the inherited function as a React child is invalid.
   - **Fix:** Require a string code owned by the message object, a string message and a boolean retry flag. A T12 unit regression checks the inherited-name response becomes INTERNAL_ERROR.
   - **If we skip it:** A malformed error envelope can cause another failure while reporting the original error.

The fixes add no dependency and do not change types, API, labels, prompts or model behavior. The client guard checks render safety and existing consistency rules; Pydantic remains the full contract validator. A missing snapshot still leaves the original citation visible in EvidencePanel. No new ErrorBoundary was needed for the reproduced response crash.

Cleanup review: rw mode refuses a missing DB; a transaction calls existing asset/job TTL methods. It does not initialize jobs, remove active raw files, erase the whole DB, or touch a billing table. Tests preserve active queued resources and a synthetic ledger row, scrub request/OCR/text_modified, and retain token-hash tombstones. Counts describe expired rows found, including retained tombstones; repeated calls may count a tombstone until its purge_at. Cleanup requires the packaged fixture files used by Jobs; it is not a standalone database recovery tool. SQLite secure erasure and backups are outside this logical TTL check.

Verdict: Ship the scoped QA/client/cleanup changes for owner review; the full T12 release gate remains blocked by missing split-image evaluation and live HTTP integration.
Not checked: real Gemini output/latency, held-out images/gold, human correction times, second-machine setup or public/multi-process deployment.
