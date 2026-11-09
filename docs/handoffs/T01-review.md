What this change does:
This adds the TinChắc 1.0 data models, fixture examples, and a health endpoint. It also adds database setup and a repeatable OpenAPI export. I assumed one person running a local demo, with one SQLite connection per operation.

## Must fix

1. **Numbers are accepted as ISO timestamps** (`backend/app/models.py:18`)
   - **What this is:** Timestamp is the shared type for request and resource times. The contract requires an ISO 8601 string with a time zone offset.
   - **Problem:** In the first version, `CheckCreate` accepted both `as_of: 0` and `as_of: "0"` as midnight on 1970-01-01. Pydantic converted Unix seconds to a date even though OpenAPI declared a date-time string.
   - **Fix:** Check the input format before Pydantic parses it. Reject numbers and strings without an ISO time and offset, and add a regression test for both inputs.
   - **If we skip it:** Clients can send values outside the locked contract. A bad time can later select the wrong source snapshot.

Verdict: fix 1 first.
Not checked: live providers, OCR, retrieval, and verification belong to later tasks. No network calls to those services were made.

## Resolution

Finding 1 is fixed in `iso_timestamp` and covered by `test_timestamp_requires_iso_offset`.
The second run passed all 55 tests, including asset state and expiry tests.
All 31 examples still validate. OpenAPI is unchanged by the stricter input check and matches the saved export.
I re-read the shared timestamp callers, final verdict and quote validators, database lifecycle, error handlers,
export script, tests and README. No remaining T01 findings and no lean findings.

Verdict: Ship.
