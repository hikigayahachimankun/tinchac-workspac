# T15 technical self-review

What this change does: It packages and checks an internal fixture release, records a real browser demo and preserves unmet acceptance gates. It fixes missing extensionless assets returning SPA HTML. Expected load: one local FastAPI process, one demo operator; no paid/public hosting.

Used repository ponytail-review sequentially. Traced frontend callers and static routing, FixtureAdapter/Jobs/resource tokens, packaging allowlist and SHA manifest, extraction/install/process cleanup, adapter/ledger quota tests, browser faults/storage/network, CLI replay mode/origin and local video render/audit. This is agent self-review, not independent human/source/gold review.

Resolved before commit:

1. `/assets/missing` returned200HTML. Two-line fallback boundary fix, regression reproduced failure and now passes; API/schema unaffected.
2. Whole-workspace archive would include private/raw data and unresolved source redistribution. Explicit allowlist excludes these, hidden files, node_modules and symlinks, with exclusion/traversal/overwrite regressions. Archive does not claim external rights clearance.
3. Fresh-tree runner initially would drop install diagnostics on command failure. Save captured log before checking status; unique output directory prevents overwriting older evidence. Env removes ambient secrets/VITE/provider settings; always fixture/localhost/one worker.
4. A video can mislead when scrolling removes the mode banner. Export burns permanent FIXTURE/local RC/no Gemini watermark over actual screen capture, with narration and final gate list. No live/benchmark/human claims.

397 backend/eval (gồm 2 HTTP fault tests),37Vitest,31examples/OpenAPI, static/package tests, separate-tree installation, browser390/1440/OCR/keyboard/source,2built smoke and full video decode/frame review passed. Read exact receipts rather than treating prior handoffs as current tests. No extra abstraction/dependency introduced into app, no changes to model/protocol/corpus/schema.

Looks good. Ship as internal fixture RC only. T15 remains blocked.

Independent Ubuntu24.04/Azure VM cold-start and synthetic OCR subsequently passed (run42827045087). Tag job is restricted to explicit RC marker after successful cold-start, creates annotated tag/ref without overwriting, uses short-lived GitHub token and logs only object hashes.

Not checked: physical demo laptop, successful DUT real S-case QA, external licences, real human OCR correction/pilot, live benchmark, human audio listening, physical network outage; native HTTPS remains unavailable; remote annotated RC was subsequently verified by successful workflow receipt and Git type/ref/peeling. No stable-release acceptance is implied.
