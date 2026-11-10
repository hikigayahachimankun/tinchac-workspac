# Verified Source Sync Implementation Plan

> **For agentic workers:** Execute task-by-task in this session, sequentially. User explicitly selected AUTONOMOUS execution and self-review; no execution-method or routine plan approval gate.

**Goal:** Discover DUT notices safely, retain review candidates, and publish reviewed snapshots to live HTTP without changing closed-corpus research.

**Architecture:** Extend the existing collector with a registry and bounded HTTP transport. Store candidates/checkpoints/receipts privately; promote only supplied, evidenced reviews through existing `ingest()`. Atomically switch a private snapshot pointer; jobs pin a runtime object, while source reads retain historical versions. A separate local scheduler drains coalesced on-demand work.

**Tech Stack:** Existing Python/httpx/httpcore/BeautifulSoup/Pydantic/SQLite, stdlib locking and scheduler. No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-10-verified-source-sync.md` (preserved user request).

## Audit — checkpoint A

- Clean `a97b3c4`, branch `task/T15-release-candidate`, upstream identical; branch inventory/log/entire tracked inventory checked. Feature starts here, not main. Dedicated `feature/verified-source-sync`.
- Current path: exact URL candidates → `collect_sources.collect()` strips embeds/PII → manual T02 register/snapshots/facts → offline `ingest()` validates register/extraction, builds chunks/manifest → `LiveRuntime` loads approved sources → `Jobs.run_live` extracts, retrieves and verifies on one runtime → evidence/time guards → result/source API. Fixture adapter is independent. Eval calls Retriever/verification directly with pinned directory; never Jobs.
- Reuse `normalize_text`, stable IDs/hash, `extract_html/extract_pdf`, `validate_register`, `ingest`, `load_corpus`, `LiveRuntime`, scope/evidence guards, warnings. Do not change model/algorithm/prompt or fingerprinted ingest/retrieval files.
- Missing: authority/listing graph, robots/DNS pinning/bounds, incremental state, candidate review receipts, atomic publication, runtime refresh/archive source lookup, durable coalescing and independent scheduling.
- T09/T13 risks: corpus fingerprint rebuilds, family leakage, backdating, hidden web in eval. Leave all tracked corpus/eval fixtures/split/protocol unchanged; feature uses ignored `data/private/source-sync/`. Existing corpus 5 approved/1 quarantine, all five families exposed dev; no human gold/holdout. Existing agent approval is not independent review.
- Baseline: `.venv/bin/python -m pytest backend/tests eval/tests -q` → 397 passed (29.18s). Source collector tests cover exact path/bytes/HTML/PII/embeds; retrieval and live HTTP tests cover immutable snapshot/cancellation/provider errors.

## Global Constraints

- API `/api/v1`, schema `1.0`; no public fields/enums changed. Candidate state lives outside SourceVersion until review.
- Exact `dut.udn.vn` only, HTTPS443, approved listing/notice paths; no arbitrary URLs, subdomain trust, credentials, login/forms, private destinations or user data sent to DUT.
- ≤1 request/second/host, timeout, bounded retries/pages/notices/bytes/duration; fail closed for unclear robots/access policy. Never evade anti-bot.
- No automatic source approval, inferred facts/supersedes or backdating. Old snapshots retained; no deletion policy silently added.
- No provider calls/keys/billing/gold/test changes. Public Git includes code, synthetic tests, safe registry and metadata/docs only.

## Review Focus

1. Redirect/canonical aliases must not expand trust or erase provenance; test forged/private and cross-unit redirects.
2. A failed/interrupted sync must keep the previous active corpus and resume candidates without truncation; test atomic failure and idempotency.
3. A changed notice must invalidate old review, including unread attachments; test hash binding and family checks.
4. Concurrent job/source requests must not mix versions; test pause during extraction, publish, resume, restart, old citation reads.
5. User-controlled scope must not escape into network URLs or create a queue storm; test fixed registry-only tasks, capacity, cooldown and fixture/replay isolation.

## Task C — registry and safe fetch

Files: `config/source_authorities.json`, `backend/app/services/source_authority.py`, `source_fetch.py`, `backend/tests/test_source_sync.py`.
Interfaces: `AuthorityRegistry.check(url, kind, authority_id=None)` returns authority; `SafeFetcher.get(url, kind, authority_id=None, headers=None)` returns bounded response. Pinned TCP backend validates every DNS answer and connects to checked numeric IP, preserving TLS SNI/Host.
- [x] Add offline security tests for host/scheme/query/redirect/IP/robots/429/403/5xx/size/count/time.
- [x] Implement exact registry, fail-closed transport, pacing and receipts; test `pytest backend/tests/test_source_sync.py -q`.
- [x] Checkpoint C in feature handoff.

## Task D/E — discovery, incremental state and review gate

Files: extend `scripts/collect_sources.py`; add `backend/app/services/source_sync.py`, tests.
Interfaces: `sync(registry, state_dir, fetcher, dry_run=False)` returns receipt; `publish_reviewed(snapshot, register, reviews, ...)` validates reviews then uses existing ingest.
- [x] Test listing pagination, aliases/hash duplicates, conditional304, changed content/version, interruption/resume, one-URL errors, PII/unread attachment quarantine, idempotency and first_seen.
- [x] Store immutable candidate files and SQLite checkpoints with per-run receipts, lock concurrent collector processes; never fetch embedded content by default. PDF/scan requires explicit reviewed local ingest via existing extraction/OCR workflow.
- [x] Test approval/hash/publisher/category/rights/family/time/facts gates and rejected supersession; preserve all existing versions in staging ingest.
- [x] Run focused collector/retrieval tests; checkpoint D/E.

## Task F — atomic publication and live runtime

Files: `backend/app/services/corpus_store.py`, `runtime.py`, `jobs.py`, `api/sources.py`, `config.py`, tests.
Interfaces: `publish(...) -> corpus_version`, `activate(store, version)`, `Jobs.runtime()` reads active pointer only when configured; `Jobs.source(version_id)` can read retained snapshots. Default direct corpus behavior stays.
- [x] Test build failure/pointer failure/restart/rollback/pinned checks/old citations; install snapshot before atomic pointer replacement with file+directory fsync and interprocess lock.
- [x] Jobs pin once in `run_live`; new jobs adopt new snapshot. Retain directories indefinitely until an explicit retention policy exists.
- [x] Run HTTP/runtime regression and same-fixture hot-path measurements before/after; checkpoint F.

## Task G — independent schedule and bounded on-demand queue

Files: `backend/app/services/source_lookup.py`, `scripts/sync_sources.py`, settings/env example, tests.
Interfaces: `enqueue_missing(claims, bundles)` enqueues only authority IDs, no raw/user scope saved/sent; scheduler drains SQLite queue. Same registry-wide task coalesces all equivalent requests, cooldown/capacity/lease enforced transactionally.
- [x] Trigger on no eligible same-scope source, before context clipping, only production Jobs live and opt-in. Return existing warnings; never hold check for network or mutate completed results.
- [x] Add CLI once/dry-run/daemon/review-publish/rollback controls; schedule enable and interval explicit. Fixture/replay refuse network; no FastAPI background crawler.
- [x] Test storm/cooldown/restart/lease/bounds/has-approved/source-after-publish/error isolation; checkpoint G.

## Task H/I — regression, actual smoke, self-review and Git

Files: `reports/source_sync.md`, README/source_log/decisions/progress, `docs/handoffs/source-sync.md`.
- [x] Final full backend/eval471passed; frontend37unit/build passed, contract/corpus checks; no locked artifacts modified.
- [x] Bounded DUT smoke through safe transport: robots first, trust links, both registered units, local-only retention. Report real HTTP/parser/hash/counts and any block; zero new approval unless actual reviewed evidence supplied.
- [x] Apply ponytail-review to full diff+callers; document and fix substantiated findings, retest.
- [x] Document schedule installation/activation truthfully (CLI availability ≠ running service), safe private paths, promotion/reload/rollback and open human/rights gates.
- [ ] Commit/push exact public feature tree safely; no force/merge/tag/deploy. Review state, not upstream task done.

## Plan self-review

Coverage checked against all 21 request sections. Conservative unread-attachment quarantine is intentional; registry is closed, not universal DUT crawling. Technical review cannot grant rights or human verification. No UI change needed because warnings already render. Execution remains sequential under explicit user instruction, overriding the skill's routine approval and sub-skill execution suggestions.
