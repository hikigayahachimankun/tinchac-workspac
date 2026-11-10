# T05 bounded preflight follow-up

Execution: sequential native under existing autonomous delegation; no approval pause. Spec: latest user instruction, T05, docs/live_setup.md, D02/D21.

Goal: safely load the outside-repo key, verify what read-only access permits, and enforce <=3 total generation attempts / <=0.03 USD without resetting the durable ledger. Do not generate if billing is unverified.

- [x] Implement/test a strict, owner-only, non-shell key loader; never print key/value/hash/provider error body.
- [x] Read official model/pricing/quota/billing docs and make at most one read-only model metadata request with header auth. Explicitly distinguish metadata access from inference/quota/billing availability.
- [x] Add durable per-run call/cost limits to budget reservations, including concurrent calls, retries, restart, unknown accounting and attempts to change registered limits. Keep global/stage caps and API/schema unchanged.
- [x] Give preflight a stable authorization run ID and <=0.03 USD run cap; re-entry cannot silently create a fresh allowance.
- [x] Only execute generation after actual billing verification and a proven token-cost bound; otherwise record exact missing access and zero generation calls.
- [x] Run provider and full backend/eval tests, contracts; review, checkpoint and commit/publish a separate branch. Continue useful offline work independently of billing.

Files: scripts/provider_check.py (safe secret/read-only metadata), scripts/preflight.py, backend/app/services/{budget,llm}.py, focused tests, docs/live_setup.md, decisions/progress/T05 handoff and metadata-only evidence. No gold, source snapshot, frontend or billing setting mutations.

Outcome: actual key loaded and1read-only model metadata GET succeeded; no generation executed because billing access is absent. Public GenerateContent combined-output documentation and rates were verified; run cost/call limits are implemented/tested. Final353tests/contracts/corpus pass. Billing verification/generation are explicitly blocked rather than marked done; checked steps describe the safe conditional workflow and offline engineering only.
