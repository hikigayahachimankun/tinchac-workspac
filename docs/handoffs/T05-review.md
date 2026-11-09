What this change does: This adds Gemini extraction with structured JSON output and full server validation. A SQLite ledger reserves money before each attempt, including retries. Provider faults remain technical errors.

Scope: T05 files listed in T05.md, including all new untracked files. I read the extraction caller, preflight, settings, contract, job error handling, fixture adapter, SDK retry code, and tests. I assumed the planned single-process demo with up to two jobs and separate SQLite connections. This was a solo review using `.agents/skills/ponytail-review/SKILL.md`; it is not owner acceptance.

**Must fix:**

1. **Zero token counts can release an unknown charge** (`backend/app/services/llm.py:65`)
   - **What this is:** A completed provider response supplies token counts used to settle the reserved money.
   - **Problem:** The first implementation accepted input=0, output=0, total=0 even when the provider returned text. This released the whole reservation as a zero charge.
   - **Fix:** Treat zero input, or zero output with returned text, as unknown usage. Keep the reservation and return PROVIDER_BAD_OUTPUT. Fixed; `test_zero_usage_for_nonempty_output_is_unknown` passes.
   - **If we skip it:** Later requests can spend money that the app has already used but failed to count.

**Should fix:**

2. **The preflight corpus fingerprint covers only the first sample** (`scripts/preflight.py:45`)
   - **What this is:** Preflight stores a corpus identifier with each attempt for later checks.
   - **Problem:** The first implementation hashed only the first sample. Editing the second or third source sample left the corpus identifier unchanged.
   - **Fix:** Hash all three sample texts and their timestamps once, then reuse that identifier for the run. Fixed; both full preflight mock paths pass, including the retry ceiling.
   - **If we skip it:** Two preflight runs can claim the same corpus identifier while using different public sample sets.

Final checks: 52 T05 mock tests pass, including SDK success and 429 through HTTP MockTransport, provider/client not called at exhausted budget, concurrent reservations on separate connections, no write transaction during provider I/O, retry and repair limits, Retry-After, cancellation, missing usage, output caps, cache identity/expiry/copies, redaction, safe errors, and the job error boundary. The cache has at most 64 public entries in memory and uses all six required key fields plus full schema/config hashes; private input is not cached. No key or raw input is stored in the ledger or application log messages. Config/model/job/OpenAPI files were compared with the start-of-session copies and were unchanged.

Verdict: Ship.
Not checked: Live Gemini availability, account quota/pricing, and actual support for temperature=0 and thinking_budget=0. D02 is unverified. The verdict covers the offline T05 implementation; owner review and live preflight are still pending.
