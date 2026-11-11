# Verified Auto-Sync Working Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. User explicitly chose autonomous sequential execution and overrides routine approval checkpoints; those execution sub-skills are not installed. Continue natively with the checked tasks below.

**Goal:** Publish a genuinely new eligible DUT document to a separate operational corpus, run scheduled discovery and prove HTTP checks adopt it without changing historical results or research artifacts.

**Architecture:** Keep the existing registry, pinned HTTP client, candidate store, review validator and offline ingest. Add conservative classification of known decorative markup and application links, evidence-bound machine review for a narrow complete HTML scholarship class, and observable scheduler lifecycle. Preserve all other candidates for evidenced review.

**Tech Stack:** Existing Python/Pydantic/BeautifulSoup/httpx/SQLite/FastAPI, local Linux process supervision, existing frontend.

**Spec:** `docs/superpowers/specs/2026-11-10-verified-source-sync.md`, extended by user instructions of 11 November (working product, eight-candidate disposition, real local operation and HTTP smoke).

## Global Constraints

- `/api/v1`, `schema_version=1.0`, `supported`, `contradicted`, `insufficient_evidence` remain unchanged.
- Preserve benchmark T09/T13, A/B/C/C_NO_TIME, gold, prompts/model/budget guards and tracked seed snapshots.
- Never claim agent review is human review; never grant content rights by assertion.
- Keep pending/quarantined documents out of retrieval; no backdated available_at.
- Closed authority IDs, robots, public DNS pinning, one request/second, bounded runs and queue.
- No paid API/hosting/billing mutations; use existing Free Tier authorization only within durable caps.

## Audit

Clean feature branch at 5c57b0e, matches upstream. Baseline 471 backend/eval tests passed in 19.45s. Prior work already implements collection, review validation, immutable publication, runtime pinning and queue. Missing operational bridge: machine review has no executable path; all links/embeds cause quarantine; scheduler has no heartbeat or start/stop process proof. Earlier source receipts contain eight quarantined notices and no newly approved content. Runtime uses private pointer only when explicitly configured. Existing warnings suffice; no UI edit planned.

## Review Focus

1. A decorative image inside a title must not block complete HTML, but an unknown business image must still block publication (Task 1).
2. An application form is an outbound action, not authority for unread policy; never fetch it (Task 1).
3. Duplicate aliases or altered review/first_seen must not generate fresh approved evidence (Task 2).
4. Restart or simultaneous scheduler start must preserve cadence, queue and exclusive execution (Task 3).
5. A real check before publication must retain its pinned corpus and result after publish/restart/rollback (Task 4).

### Task 1: Extraction completeness and real candidate disposition

**Files:** `backend/app/services/source_sync.py`, `backend/tests/test_source_sync.py`, safe receipts under `docs/evidence/source-sync/`.
**Interfaces:** `parse_notice(body: bytes, authority: dict, url: str) -> dict` stays compatible; enrich link roles only when proven by markup, keep unknown objects unread.
- [x] Add failing cases: title badge ignored, inline emoji ignored only from exact known markup, unknown image/iframe still incomplete, forms retained as links without fetch, personal lists rejected.
- [x] Run focused tests, implement minimal classification and rerun.
- [x] Recollect through bounded safe transport; examine all original eight and alternative official listing notices. Record duplicates/privacy/relationship/completeness individually, without retaining personal attachments.

### Task 2: Evidence-bound low-risk promotion

**Files:** new `backend/app/services/source_review.py`, existing `corpus_store.py` callers and `scripts/sync_sources.py`, new `backend/tests/test_source_review.py`.
**Interfaces:** `review_candidates(state: Path, store: Path, registry: AuthorityRegistry, policy: dict) -> dict` builds private packets/union/register then invokes existing `publish_reviewed`; no second ingest.
- [x] Test exact quote/span and narrow deterministic extraction, unknown/multiscope/PII/attachment/amendment/critical update refusal, duplicate canonical rejection and content-use gate.
- [x] Implement explicit agent identity, machine evidence and private review artifacts, bind candidate hash and preserve original records. Do not change mandatory human gates.
- [x] Test actual publish, re-run idempotency, restart and rollback. Record before/after corpus/source IDs and content hashes.

### Task 3: Scheduler lifecycle and automatic promotion bridge

**Files:** `scripts/sync_sources.py`, new lifecycle wrapper as needed, `config/source_sync.json`, scheduler tests, README.
**Interfaces:** preserve `run_once` and `daemon`; add start/stop/status with lock/process identity plus heartbeat and last-cycle receipt. Daemon runs review only under explicit evidenced policy.
- [x] Test heartbeat, competing daemon exclusion, graceful stop, restart cadence/checkpoint and review failure isolation.
- [x] Run two actual bounded cycles at 60s test cadence, restore production 3600s and verify process/status/log; no 24/7 claim.

### Task 4: Actual product smoke, review and Git

**Files:** focused real smoke runner, safe evidence, reports/runbook/handoff/decisions/progress.
**Interfaces:** use existing HTTP `/health`, `/checks`, `/sources`; load authorized key via existing safe loader, same ledger/caps. No new public contract.
- [x] Build/frontend tests; run real FastAPI localhost serving built frontend.
- [x] Execute a missing-source HTTP check, inspect fixed-ID queue, drain via real DUT collector, publish eligible source and repeat check. Check exact citations/version and immutable old result, restart and rollback. Separate real network/model observations from fixtures.
- [x] Run full backend/eval, contracts, corpus and security regressions; self-review full diff/callers with ponytail-review and fix concrete findings.
- [ ] Update receipts/runbook and durable checkpoint; commit and safe push public code/metadata only. Record any unavoidable human action immediately and continue independent technical work.
