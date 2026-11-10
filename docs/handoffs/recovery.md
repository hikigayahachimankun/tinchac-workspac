# Autonomous recovery handoff — 10/11/2026

Owner: delegated maintainer; sequential technical self-review, not independent human validation. Current work is rooted at T13 `4fdbc5b`, not main. Audit: `reports/recovery_audit.md`; scope/status: `docs/progress.md`; decisions D17/D19–D22; plan: `docs/superpowers/plans/2026-11-10-recovery.md`.

## Completed work

Production HTTP/approved snapshots/ledger/cancellation, Gemini3 reasoning config, eval preparation/hash/temporal/scorer guards, public candidate collection,20-image dev OCR, same-origin local release, usability preparation and truthful submission/disclosure/final checklists. Contracts/schema1.0 and approved corpus unchanged. No gold, paid API, benchmark, human reviewer/participant or actual submission generated.

Accepted technical tasks: T00/T01/T03/T04/T06/T07. Others remain blocked only on explicit full-acceptance gates recorded in progress. Source candidate11659 is NOT approved; no source count inflated. OCR CER29/1812=0.0160044150 is dev-only, not a verdict benchmark.

## Checks actually run

```bash
.venv/bin/python -m pytest backend/tests eval/tests -q --tb=short
.venv/bin/python -m scripts.export_contracts --check
.venv/bin/python -m scripts.validate_corpus
.venv/bin/python -m scripts.validate_eval
uv pip check --python .venv/bin/python
npm test --prefix frontend
npm run build --prefix frontend
```

Results:329pytest;31examples/OpenAPI matches;6sources/7exactchunks (5approved);15dev/0gold/5families NOT frozen;63packages compatible;37Vitest/build pass. Browser env: TINCHAC_CHROMIUM_PATH=/tmp/tinchac-chrome/chrome-linux64/chrome, LD_LIBRARY_PATH=/tmp/tinchac-browser-libs/unpacked/usr/lib/x86_64-linux-gnu; use TINCHAC_EVIDENCE_ROOT to preserve historical captures. Full fixture20/20, mock4/4, built release2/2. Initial release hardcoded-port probe failures were fixed and stable run passed. Final focused changes were backend safety/test isolation only; no UI design changes.

Fixture27/27 at `/tmp/tinchac-recovery-fixture`; replay27/27 at `/tmp/tinchac-recovery-replay`. Scorer known-vector/byte-reproducibility tested in eval suite; these are synthetic plumbing, not DUT gold. Preparation `/tmp/tinchac-recovery-dev-preparation`; OCR images `data/raw/recovery-ocr20/`; candidate sanitized snapshot `data/raw/recovery-sources/` (ignored). Durable summaries/screenshots at `docs/evidence/recovery/`; these reproduce with committed scripts if tmp is removed.

## Git preservation/publication

Initial tree clean. Source commits `5f65546 -> 1c8e8ce -> 4fdbc5b`, containing mixed task batches, were preserved; fetched remote task branches held no newer divergent code. No reset/force/deletion/main integration/deployment. Recovery commits record separate tested changes. Standard HTTPS push failed (no WSL credential); connected GitHub permission is verified. Publication uses base T13, creates identical Git trees, and fast-forwards with expected SHA. Remote commit messages map each original local checkpoint; author/time metadata differ. Preserve original local history as `recovery/t00-t17-local-checkpoints`, then fetch/switch to tracking `recovery/t00-t17-audit` only after tree equality and clean tree checks. Git log is the source of exact final commit IDs; no self-referencing commit SHA is invented here.

## Remaining real gates

- D02: GEMINI_API_KEY absent from process; configure only outside repo via `docs/live_setup.md`. No key in chat. Need actual model/quota/pricing, capped3-attempt preflight authorization and dashboard accounting. HTTP default remains LLM_LIVE_ENABLED=false.
- Dataset:5dev/0testfamilies,0human gold; lawful complete fee notice and family/rights review, actual private annotation/evidence scores, temporal/config/corpus freeze before fresh benchmark. D17 technical approval is already resolved.
- T12/T14:0heldout images, no human OCR correction/time,0consenting volunteers. Planned allocation/worksheets are not observations.
- T15:second physical-machine smoke, human video/rehearsal and distribution licences. Current WSL fixture release is verified.
- T16/T17:real entrant identity/eligibility, permitted images/final evidence, actual applicant declaration/submission/receipt. Current status NOT submitted.

## Next step (one)

Resolve D02 with the owner-only outside-repo secret/account and capped preflight permission; keep the other offline/human gates explicitly open and do not substitute fixture scores or AI annotations.

Final verification: full **329 passed (13.24s)** after adding cap/non-HTML source regressions;31examples/OpenAPI match. T04 probes also re-run through the Vite proxy after their origin fix: **2/2 (12.9s)**, separate from built release2/2. Detector returned[]; no UI redesign. Planned usability tasks refined by input metadata to include an award, modified amount, unverified fee and payment deadline across four dev families;48-row balance assertions rechecked, still0actual participants/outcomes.

Documentation finalization initially stopped on a Python syntax error and CSV CRLF whitespace check; corrected generation and normalized planned CSV files to LF before committing. No failed command was counted as a passing gate or benchmark outcome.

## T05 follow-up (D23) — current key/account state

The key is now configured outside the repository and loaded safely without sourcing/export/logging; one read-only models.get returned200 for the configured3.5Flash-Lite and advertised generateContent. This supersedes the earlier key-absent checkpoint. Account billing/quota remain unverified because no Cloud OAuth/project access or suitable billing connector is available. No generation was called. See latest T05 handoff and `docs/live_setup.md` for actual receipts, conditional public cost bound0.0234USD, stable3attempt/0.03USD SQLite run limits and the CLI's fresh genuine billing/quota receipt guard. Do not re-request key setup or infer paid readiness from metadata.

Next step for T05: obtain authenticated read-only account billing/AI Studio access for the key's project, then verify and run the existing conditional authorization. No manual code review/commit is required from the owner.

Follow-up technical check:353backend/eval tests passed, contracts/corpus match, expected CLI billing gate returned2 without generating. Details/review/actual metadata receipt are in T05 handoff; no billing success, inference result or project-wide account spend is inferred.

## Current Free Tier checkpoint — 10/11/2026 (supersedes D23 account-only blocker)

Branch `recovery/t05-free-tier-preflight`, based on published584b0ed; previous recovery/task/main branches and local checkpoints retained. Owner confirmed Free Tier and authorized3preflight attempts followed by capped Free Tier recovery. D24/D25 now govern account and DEV repairs. Do not request the same key/account confirmation again or rerun the consumed preflight. No paid/billing/top-up/deploy/submission operation.

Completed: actual preflight3/3,859input/1126output incl thoughts,0estimated Free Tier charge; real model/version/SDK/MINIMAL structured output works. Added explicit Free Tier usage/account gate, durable run caps, atomic project-local quota and cross-run refusal stop. T05 is technically done; T00/T01/T03/T04/T06/T07 remain done. D17 approved, D24 accepted owner Free Tier evidence without inventing authenticated billing flags, D25 specified reviewed-span citation alignment and context/ID repairs before freeze.

Continued actual T08 DEV: round1 stopped on503,round2 completed6responses with allN after citation guard. Saved raw drafts enabled literal exact-reviewed-span canonicalization, with0-call offline replay4S/1C/1N and5explicit repairs. Original live rows remain allN; replay is not benchmark/live acceptance. No third C-dev tuning round. B/C/C_NO_TIME get identical q metadata/full shared benchmark bundles; all wrong-source/time/scope/semantic guards remain. Production context now omits empty no-fact overhead/duplicate text and redacts values rather than corrupting opaque numeric IDs. Original cap6000,220excerpt and schema1.0 preserved.

Continued T12 production HTTP actual12planned pairs/5exposed families. First run1complete/1INPUT_TOO_LARGE/10missing; offline fix then second full-input run2complete/1failed/9missing. The latter failed on503followed by known retry because first-attempt usage remains unknown; no silent success/fixture fill-in. All successful HTTP verdicts were conservativeN, with no S/C citation-quality claim. Public files include selected inputs, safe results, code/prompt hashes for the repaired run, cleanup/summary; no capability secret. Both failed runs remain in docs/evidence/T12. No further API generation after these partial batches.

Retained SQLite ledger receipt `docs/evidence/T05/free-tier-ledger-2026-11-10.json`:23attempts=3preflight+5DEVround1+6DEVround2+3HTTPinitial+6HTTPfixed;21settled/2unknown503. Known17093input/6799output tokens,knownestimated0USD,totalactualN/A,heldpaid-equivalent0.0122415USD. No quota/FreeTier refusal. Unknown records/tokens are not zeroed or discarded. Shared local quota cannot audit other applications or invoice.

Validation:372pytestpassed(13.48s);31examples/OpenAPI match; corpus6sources/7exactchunks valid. Added quota/refusal restart, receipt, zero-charge-real-token, exact reviewed quote repair/fabrication rejection, numeric-ID redaction,12pair bound, public HTTP stop/delete/no-token and recorded guard replay regressions. No UI changes; prior37Vitest/fixture20/mock4/built2browser evidence was not rerun or passed off as fresh live browser acceptance. A wrong contract-check module name and intermediate context-bound tests failed, were corrected, and are not claimed as passing checks.

Remaining gates by task: T02 complete lawful second fee source/spot-check; T08/T10 complete live acceptance/reliability and full UI/live flow; T09/T11/T13 actual reviewed human gold/new holdout families/config+corpus+temporal freeze/live benchmark and human evidence scoring; T12 full12live success plus heldout OCR/human correction; T14 real consented volunteers; T15 second physical machine/video/distribution rights; T16/T17 entrant identity/eligibility/final evidence/submission/receipt. Existing5dev/0testfamily/0gold cannot support a frozen benchmark. Do not relabel exposed families or generate fake independent reviewers. Main is not merged while these gates remain.

Git: first local checkpoint485a123 published as58af13ed1dac22ac80bcbffaa5ebfe5949416725 with identical tree; follow-on fixes/evidence go in a separate tested commit on the same recovery branch. Connected GitHub publishes verified identical trees because WSL HTTPS credentials are unavailable. Preserve local checkpoint branch before switching to remote tracking; no force/reset/deletion. Exact final Git IDs are in git log, not self-referential placeholders.

Next step: reconcile both unknown503attempts with genuine account/provider evidence, then run one separately identified complete public acceptance batch with unchanged criteria, without reopening the consumed preflight or treating replay as live.
