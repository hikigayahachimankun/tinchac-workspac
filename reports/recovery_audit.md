# Recovery audit — 10/11/2026 (Asia/Ho_Chi_Minh)

Authority: current autonomous-recovery request; D19/D17/D20 in `docs/decisions.md`. Plan: `docs/superpowers/plans/2026-11-10-recovery.md`. This audit records actual gates; a historical handoff or commit is not acceptance.

## Git provenance

Initial tree clean, branch `task/T13-benchmark-evidence`, HEAD `4fdbc5b`. Fetch succeeded. All advertised origin task T01–T08 refs and origin/main point to baseline `5f65546`; local main and task T05–T12 point to `1c8e8ce` (mixed T01–T05 implementation). `4fdbc5b` adds mixed T06–T13 implementation. No unique divergent implementation was found in other fetched refs. No uncommitted work required a rescue commit. Recovery starts from T13 on `recovery/t00-t17-audit`; old branches and all commits retained. No reset, force push, deletion, main integration or deployment.

## Task acceptance inventory

| Task | Observed implementation / gate | Defect class / recovery action |
|---|---|---|
| T00 | Solo authority recorded but old progress omits T14–T17; stale owner-review blockers | Integration/incomplete acceptance: D19, complete task table and checkpoints; physical demo machine unconfirmed |
| T01 | Models/API schema 1.0, 31 examples, DB/FTS5/health implemented | Re-run contracts, full model/HTTP tests, dependency check |
| T02 | 5 approved sources (4 scholarship/1 payment), 1 quarantined personal attachment | Missing data/human-only: discover safe public payment source, preserve quarantine; independent spot-check absent |
| T03 | Typed React UI with explicit mock mode, keyboard/mobile tests | Re-run frontend/build/browser; old uncommitted-contract blocker obsolete |
| T04 | Fixture HTTP lifecycle, capability auth, delete/TTL/restart | Re-run lifecycle tests and browser; old uncommitted-upstream blocker obsolete |
| T05 | SDK schema/retry/budget/unknown-usage ledger implemented | External: account model/price/quota/thinking configuration unverified; no paid calls permitted yet |
| T06 | Local OCR, asset limits, confirmation, cleanup | Re-run real OCR and browser; 20-image research evaluation remains T12 |
| T07 | Reproducible local corpus/FTS5+TFIDF/RRF and temporal cutoff | Re-run corpus/retrieval; corpus still only 5 usable families |
| T08 | Production services exist, HTTP rejects every live check | Integration defect: connect production stages, approved snapshots, durable ledger; provider quality remains unmeasured |
| T09 | 15 draft dev cases, 5 dev/0 test families, 0 human gold; NOT frozen | Missing data/human-only: public claim/annotation tooling; never move exposed dev to test |
| T10 | UI supports live labels but backend missing integration | Integration: test actual HTTP production services with scripted provider; provider live QA gated by D02 |
| T11 | Offline A/B/C/ablation/scorer exists | Integration/incomplete acceptance: approve D17, pin preparation/subset and verify run provenance before future fresh calls |
| T12 | Privacy/failure tests exist; 12 scripted multi-field service cases | Missing integration/data: production HTTP tests; 20-image dev tooling; human correction and real live QA unperformed |
| T13 | Readiness report only; no actual benchmark | External/human-only: no human gold, heldout families, verified model, frozen inputs or evidence scores; keep blocked |
| T14 | No pilot report/consent/allocation/results | Missing implementation/human-only: prepare consent/protocol/blank worksheet; real volunteers cannot be simulated |
| T15 | Build exists, no FastAPI static serving or release runbook | Missing implementation: same-origin local serving and release smoke; second physical machine/video unperformed |
| T16 | No submission draft/AI disclosure | Missing implementation/human-only: factual draft/checklist; identity/official form fields remain pending |
| T17 | No final review or actual submission receipt | Missing implementation/human-only: traceable review/checklist; explicitly not submitted |

## Measured baseline

- `.venv/bin/python -m pytest backend/tests eval/tests -q`: **300 passed** (12.12s).
- `npm test --prefix frontend`: **37 passed / 7 files**.
- `npm run build --prefix frontend`: TypeScript/Vite passed; JS 249.60 kB, gzip 78.06 kB (bundle size, not latency).
- API calls to paid provider: **0**. No benchmark, accuracy, ECV or human evidence scores measured.

## Research limits and decision

Use the protocol's technical-pilot fallback with actual n while attempting lawful source expansion. Current n=5 dev families/0 test and zero gold cannot support an out-of-sample benchmark or any claim that C improves B. AI may prepare inputs/worksheets and inspect public source text; it may not impersonate annotators. Existing source rights allow internal review only; no corpus/raw redistribution claim. Do not lower thresholds, invent supersession histories or label silent sources as contradictions.

## Recovery implemented and verified

- Production HTTP uses existing extraction/retrieval/verification with durable demo ledger and per-job accounting; safe explicit enablement, exact approved snapshots and truthful corpus health. Cancellation/TTL stops between paid stages and cannot restore deleted rows.
- Gemini3 minimal thinking configuration corrected from primary Google docs; candidate_count omitted; thoughts included in actual usage/reservations. Account D02 remains unverified.
- D17 approved; public preparation, exact raw-value traceability, cases/normalized-claims hashes and ordered temporal subset pinned. Scorer rejects A source leakage, nonfinite exchange rates and mode/corpus drift; missing accounting is unknown, not free.
- Safe exact-path HTML candidate collector tested and run; no attachment fetch/promotion. Approved corpus remains unchanged (5 usable families). Draft annotation worksheets do not create gold.
- Local OCR-only pilot actually ran 20 rendered dev images/5 families, 29 edits/1812 reference chars (CER 1.60044%). No heldout image or human correction was manufactured.
- Explicit same-origin static release, private/API path guards and built browser smoke; actual user-pilot allocation, AI disclosure and factual submission/final-review drafts prepared. Actual participants/submissions remain zero.

Final technical regression at recovery checkpoint: **329 pytest**, **37 Vitest**, build/contracts/corpus/eval validators pass; **20 fixture browser +4 mock browser +2 built release browser** pass. UV reports63packages compatible. Fixture/replay27/27 each and scorer synthetic reproducibility pass. No paid provider calls, benchmark verdict metrics, gold annotation, human evidence scoring, production deployment or real submission.

Technical scopes accepted: **T00/T01/T03/T04/T06/T07**. Remaining tasks have completed independent engineering/draft portions but fail full live/data/human/release gates; see current progress table for precise status. Main is deliberately unchanged.

Normal Git push failed because WSL lacks credentials. Connected GitHub has verified push permission; recovery publishes equivalent commits through GitHub tools and verifies identical Git tree hashes. API-created commits have different author/time metadata and thus different commit SHAs; their messages preserve local checkpoint SHAs. Original local checkpoints remain on a preserved local branch before checkout of the published tracking branch. No force push, reset, deleted history or hidden merge is used.
