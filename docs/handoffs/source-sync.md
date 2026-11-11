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


## Checkpoint I — Git publication verified

- Feature code published at `0a11d5e1177a4fd9e90dcf001a5ffb78b54fe7b4`, parent a97b3c4, remote branch `feature/verified-source-sync`. Native original c56c9b8 retained on `feature/verified-source-sync-local-checkpoints`; renamed the clean local branch and checked out the fetched feature branch without reset/force.
- Local/remote code trees both `87c59440ecd9f289e3fc12a7a3badd008ee821f0`, verified after fetch. Receipt `docs/evidence/source-sync/git.json`. Later receipt-only commit adds this verification; runtime code unchanged. No corpus/raw/private/gold/user content newly uploaded; no merge, tag, workflow, deployment or model calls.
- Final status **review**, technical checkpoints A–I complete with471backend/eval tests/37frontend tests/build/contracts/corpus checks and actual bounded DUT smoke. New approvals0; unattended scheduler off. Runbook README; actual results report and review linked above.
- Next step: actual source reviewer checks lawful completeness/content-use rights for one quarantined public fee notice before any promotion.

## Working-product checkpoint — 11/11/2026

- Branch `feature/verified-source-sync`, base/initial HEAD `5c57b0e`; started clean. Current work extends existing implementation rather than rebuilding it. Status **in progress**, not DONE and no new source approval claimed.
- Plan: `docs/superpowers/plans/2026-11-11-source-sync-operation.md`; decision D29. Changes: exact decorative/application-link classification, plain document/CSS/SVG completeness, extraction revision, narrow agent review through existing publish validator, observable start/stop/status/heartbeat with process identity, interrupted queue lease recovery, safe local live launcher.
- Initial regression471passed/19.45s; focused new tests have passed. Full intermediate regression486passed/1failed caught changed opt-in default; restored tracked enabled=false, while explicitly enabled actual scheduler remains operating. Final regression still pending after last hardening edits; do not report the intermediate failure as unresolved code behavior without rerunning.
- Actual two60s DUT cycles: `docs/evidence/source-sync/scheduler-operation.json`; private run IDs d8e104ee-094d-4d31-8212-4f0b0f9c63c4 /0482eee0-8932-4bff-871b-5df424c08f20. Restored3600s, restart preserves schedule; current process evidence must be refreshed with status. User systemd offline; detached local CLI, host/WSL availability required.
- Actual FastAPI localhost: `scripts.serve_live`, existing Free Tier readiness/secret loader/ledger, built HTTP frontend. First AIDA check completed using actual Gemini,603input/282output,2attempts,0USD estimated; no mock. Private record/capability: `data/private/source-sync/http/before*.json`. Token stays private. Before corpus remains corpus-6b5cb0eb9e0b4f5029857ffe83259f77290af8585d05aa50216fee0d122142e5. On-demand enqueued only dut_ctsv; actual daemon receipt9066fbc4-3085-4fd1-9b89-d2f2445e9460 records CTSV-only DUT requests. Source still pending gives NEI, no fake supported.
- New candidate12218 (AIDA) is complete HTML, one registration action, no unread attachment or PII found in agent reading. Proposed programme/deadline quote spans checked; no Yen/VND amount or subgroup facts inferred. Deadline15/9/2026 is historical. Private review summary `data/private/source-sync/aida-review-pending.json`; recollect with final extraction revision before any promotion. No content-use policy/rights assertion fabricated.
- Required user action asked immediately via pending async question: confirm an actual basis/right for internal use of eligible public DUT notices (example https://dut.udn.vn/Phong/CTSV/Thongbao/id/12218), no redistribution/personal lists. Do not ask user to edit JSON or run commands. On answer, record exactly its scope/basis and only then publish/recheck. No human source reviewer is invented.
- Two financial PDFs5631/5574 read all2pages each locally; they are scans, native text empty. Original5631 has30/10 deadlines and overlaps the existing6075extension family;5574 has specific enrolment charges and K2026 scope. Private administrative review material/OCR under `data/private/source-sync/review-materials/`; nothing uploaded to Gemini or Git. Known personal12381 not reopened; award-list12373 only metadata read,16.9MB, no personal list downloaded. Final eight-candidate disposition and remaining metadata-only financial12319 must be made explicit in report.
- Still required: finish focused/full QA and review, durable safe receipts/report/runbook, commit/push; after genuine content-use answer, publish new DUT source, actual post-publish check/citations/restart/rollback with old-record immutability. Benchmark corpus/protocol/gold unchanged.
- Next step: finish final security review/regression and prepare the safe operational receipts while awaiting the pending content-use answer.

## Checkpoint final — real auto-publication, HTTP/browser and recovery

- Supersedes the pending-rights/0approved statements in the earlier11/11checkpoint. Owner answered the specific content-use question affirmatively; private policy records exactly an internal-use owner attestation, not a DUT licence or human source review.
- Actual on-demand scheduler run2f9b466e-d525-471e-a805-e7833acd6609 automatically approved/published AIDA12218. New version `dut_39c806ec6715272c_0294c3ba0dc48e23`, family scholarship_37b499ae1fea9692; corpus6b5cb0… → b646223… (7versions/6approved/8chunks). Full hashes/URLs/counts/metadata and old-eight dispositions: `docs/evidence/source-sync/operation.json`, `candidate-dispositions.json`, `attachment-metadata.json`, `retrieval-live.json`.
- Actual Gemini source-grounded HTTP and then browser checks supported the programme identity with exact new version/chunk and quote span81–123. Browser390/1440, keyboard, opened evidence/snapshot, no overflow/page errors; private screenshots/record `data/private/source-sync/browser/`. Initial post-publish citation failure and audience/scope failure remain immutable; no fallback mock or guard bypass. Production context adds verbatim program quote beside q; model/prompt/strict validator and benchmark path unchanged. Synthetic regression covers exact quote and original context cap.
- Actual rollback→cold backend restart→archive new-source citation→forward restore passed, old NEI and new supported JSON unchanged. Receipt `docs/evidence/source-sync/rollback-restart.json`. Backend currently bound127.0.0.1:8000 with built live frontend; scheduler user-owned detached process uses3600s/poll10s, restart preserves cadence/queue/last-cycle evidence. Inspect current state with CLI status; no claim of24/7 or reboot supervisor.
- Actual source operations:7persisted new collector receipts/176HTTP requests;5scheduler cycles including two60s test cycles and real CTSV-only lookup. Supplementary inspections/Drive reads counted separately, not invented. All key/raw/source/PDF/image/OCR/lookup capability data stay private; benchmark corpus7b832d…/reference files/protocol/gold unchanged.
- Final curated HTTP+browser accounting:16actual Gemini attempts,5822input/2602output,0USD estimated Free Tier, original shared ledger. Five additional localhost/live attempts in ledger are not called curated tests and no private input was read. Two earlier503unknown holds0.0122415USD paid-equivalent remain. Consumed preflight not rerun, no paid fallback/billing/hosting.
- Validation: full backend/eval504passed35.69s before the final smoke-capability path hardening; focused source operation8passed and collector56passed after final hardening/performance change. Final full-current-tree rerun is recorded below once complete. Frontend37unit/build passed;31examples/OpenAPI match; benchmark corpus6sources/7chunks valid. Same-host1500link fixture median166.18ms→121.24ms, `parser-measurement.json`.
- Self-review: `docs/handoffs/source-sync-review.md`; no unresolved Must/Should fix at stated local load. Gate limitations: initial/historical programme+deadline class only, some model inputs still NEI, financial/scan/list reviews and full upstream12case QA/research remain separate. Source deadline15/9/2026 does not imply applications currently open.
- Next step: finalize the current-tree regression receipt and publish the verified public Git tree; keep task in review under AGENTS.md rather than impersonating an independent reviewer.

- Final current-tree rerun: `.venv/bin/python -m pytest backend/tests eval/tests -q` → **505passed,23.87s**; safe receipt `docs/evidence/source-sync/qa.json`. Final source security/helper changes included. Backend/source health and benchmark integrity checked; no further model calls needed.

## Git publication and resume verified

- Code commit20e1201e92d422e83819d0b18443a69342ab5b9f published on feature/verified-source-sync; exact tree7a565c25506e5a91663cb343c2b8e58cec9eb24e matches the505-test local tree. Original local cdcaf97 retained on feature/verified-source-sync-local-operation-checkpoint. No reset/force/merge/tag/deploy or private source upload. Receipt: docs/evidence/source-sync/git-operation.json. A receipt-only follow-up records this state.
- After environment interruption, both processes were correctly detected dead/stale. Restart restored backend/live/frontend/source HTTP200 and scheduler state without clearing checkpoints/cooldown/ledger. Original NEI and new supported records/quotes unchanged. Scheduler completed one more actual DUT cycle: total6cycles,8newcollector receipts/199recordedHTTP requests. Evidence docs/evidence/source-sync/resume.json;0additional model generation calls by resume.
- Status remains review under AGENTS.md; maintainer technical acceptance is complete for the documented local scope, not independent human approval or upstream benchmark acceptance. Source/privacy/financial and host-availability limits remain as documented. Running process is real local CLI; it does not imply uptime while environment is stopped.
- Next step: monitor the next scheduled cycle using the README status command.
