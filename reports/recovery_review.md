# Recovery technical self-review

What this change does: It connects the existing production services to HTTP, makes evaluation inputs/provenance explicit and prepares a local fixture release. It automates source discovery and OCR-dev checks while preserving human/account/research gates. Expected load: one local demo process, at most two job workers, one sequential eval writer.

Used `ponytail-review` sequentially. Traced API→Jobs→extraction→retrieval→guard/render→SQLite/ledger and client/source rendering; traced EvalCase/Claim preparation→A/B/C contexts→run envelope→offline scorer, plus static fallback and source acquisition. This is not an independent human source, gold or usability review.

Findings fixed and tested:

1. HTTP rejected all live jobs and served no approved real snapshots. Existing services now run through HTTP with shared durable accounting, explicit enablement and cancellation between stages. Five HTTP regressions exercise production services with SDK-scripted responses; no actual Gemini call claimed.
2. Gemini3 reasoning used the old budget0 control. Primary docs verified levels/minimal and candidate behavior; adapter/preflight/metadata now agree, all systems share config, and thought tokens remain billed/accounted. Account support still requires preflight.
3. Eval accepted raw values absent from public input and re-selected temporal metadata without preparation pins. Exact input excerpts/IDs/spans and cases/normalized-claims/subset hashes now guard fresh execution. Scorer rejects source evidence in A, nonfinite rates and provenance drift, treating absent accounting as unknown. Synthetic reproducibility formulas still match.
4. Release tests assumed backend port8000. Their probes now use the configured origin, and the built app passes without Vite. Static API misses and private/path/symlink escapes are tested, including an outside index.html symlink. New release tests use temporary paths rather than default private storage.
5. Candidate collection lacked explicit cap/non-HTML regression tests. Added two final tests; redirects/size/MIME/privacy checks leave no retained candidate, embedded attachments never follow and no source is auto-approved. Candidate remains outside corpus.

No remaining code blocker found within the verified local fixture/offline scope. Dependencies/schema/corpus unchanged. All decisions and known limits are recorded, including conservative scope guards/context bounds, local-only queue and logical SQLite deletion (not secure erase).

Verdict: Ship on the recovery branch for verified offline/local fixture use. Full live/research/release acceptance remains blocked as recorded in progress. Main is unchanged.

Not checked: paid provider/account support, actual human annotation/evidence/correction/volunteers, second physical machine/video, third-party redistribution permission or real submission. Exact executed counts and artifacts are in the recovery handoff; none of these missing checks are inferred from unit tests.
