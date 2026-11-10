# Source sync — verified DUT discovery and live refresh

- Owner/reviewer: autonomous maintainer / self-review; human source/rights gates separate.
- Branch: `feature/verified-source-sync`, base `a97b3c4`; uncommitted feature work.
- Status: implementation, checkpoints A/B verified.
- Audit/plan/spec: `docs/superpowers/plans/2026-11-10-verified-source-sync.md`.
- Baseline: `.venv/bin/python -m pytest backend/tests eval/tests -q` → 397 passed, 29.18s.
- Existing corpus/eval/protocol/gold remain untouched. No provider calls or credentials.
- Not yet run: new feature tests, live source smoke, review/publish/schedule.
- Next step: implement authority registry and bounded fetch security tests (checkpoint C).

## Checkpoint C — authority/fetch verified

- 30 security tests passed offline: exact host/path, private/mixed DNS answers and numeric TCP pinning, robots longest-match/group/wildcard, 403/429/5xx/backoff, strict redirects, type/byte/request/time limits. No credentials/provider used.
- References checked: RFC9309 and OWASP SSRF Prevention primary documents; URLs in implementation plan/spec. `source_fetch.py` isolates the pinned httpx/httpcore transport seam.

## Checkpoint D/E/F/G — implementation and initial checks

- Registry/listing discovery, conditional304, content/attachment-change review identity, immutable private candidate files, per-notice SQLite checkpoints and safe receipts implemented. Existing `collect_sources` CLI delegates to registry sync; existing exact-notice helper callers retained.
- Review packets enforce authority/extraction/provenance/privacy/family/quotes/time/content-use; risky sources additionally require declared actual human review. Existing ingest builds staging snapshots; snapshot pointer, runtime adoption/pinning, archive reads and explicit rollback implemented.
- Queue stores fixed registry IDs only; cooldown/capacity/lease/coalescing; opt-in live Jobs integration and separate local scheduler/CLI.
- `.venv/bin/python -m pytest backend/tests/test_source_sync.py backend/tests/test_source_publication.py -q` →56passed,2.28s (before latest channel/empty-embed parser refinements). Collector compatibility suite earlier51passed. First integration test run caught invalid lock-file chmod use; corrected to os.fchmod and rerun passed.
- Actual smoke receipt `data/private/source-sync/runs/211ec4d6-8161-475e-abcb-dce54e7db035.json`: 7requests/7.29s, homepage links verify2units,3listings,6discovered URLs,2notice200 responses,2content_empty rejects,0approval. Follow-up listing inspection discovered CTSV's `/Phong/Sinhvien` alias channel; registry now records official-listing evidence. No attachment fetched. Full smoke/result report still pending.
- Next step: finish adversarial review/publish/scheduler tests and full regression, then final bounded smoke and self-review.

## Checkpoint H — actual smoke, review and acceptance limits

- Actual bounded runs and public safe receipt: `docs/evidence/source-sync/smoke.json`, detailed counts in `reports/source_sync.md`. Four runs35recordedHTTP requests;3unique listings/12checks;18discovered URLs;8quarantined candidates/0complete pending/0newapproved. Extra inspection2listings had request cap6 but count not persisted. Last successful run11/11/2026 00:04:50UTC+07. No attachment/model fetched; no source truth/human/rights approval inferred.
- Bootstrapped private store offline from unchanged seed: `corpus-6b5cb0eb9e0b4f5029857ffe83259f77290af8585d05aa50216fee0d122142e5`; existing research corpus remains `corpus-7b832d58775878a57849d32ff241cc61904afadfc0299a66e3918ad82da18982`,6sources/5approved/7chunks. Different ingest commit changes manifest identity; zero new approved content. Actual local Jobs read the store successfully. No app env or running service switched silently.
- Runtime lookup10000calls on same6sources: before0.699µs direct, after0.943µs direct, opt-in pointer42.945µs. Read-only measurement; no retrieval optimization/provider latency claim.
- Self-review `docs/handoffs/source-sync-review.md`: fixed review evidence persistence, post-replace failure restoration, backlog durability/interruption receipts, attachment metadata identity, retry/robots/encoding bounds, idempotent approval retry and corrupt archive lookup. New tests are synthetic; no human review fabricated.
- Frontend `npm test --prefix frontend -- --run` →37passed; `npm run build --prefix frontend` →success. No UI changed; existing warnings renderer inspected, no impeccable/UI screenshots required.
- Contracts31examples/OpenAPI match; corpus6sources/7exactchunks valid; eval15cases/5families/0gold validated_NOT_frozen. `git diff --exit-code a97b3c4 -- data/corpus eval config/experiments.yaml backend/app/models.py backend/app/services/corpus.py backend/app/services/retrieve.py scripts/ingest_sources.py prompts contracts frontend/src` →exit0. Fixture/replay/research inputs unchanged.
- Scheduler daemon available and synthetic start/tick/drain/stop/restart verified. Not installed/running unattended; user systemd reports offline. New source/human/rights and live update304/provider acceptance stay pending. No T12/T13/T15 task moved to done.
- Native `GIT_TERMINAL_PROMPT=0 git push --set-upstream origin feature/verified-source-sync` failed for missing HTTPS Username. Connected GitHub confirms public repo push/admin. Use the same exact-tree Git Data transport already established in D26/D27, never credentials/force/reset/merge.
- Status: review, technical feature only. All data local/private,0provider calls/0tokens/0USD. Temporary context handoff at `/tmp/tinchac-source-sync-handoff.md`; official checkpoint remains this file.
- Next step: finish final regression and publish the checked public feature tree with exact local/remote tree verification.

Final regression: `.venv/bin/python -m pytest backend/tests eval/tests -q` → **471passed,19.27s**, including74new feature tests. Source-only full suite baseline397; no gold/network/provider calls in regression.
