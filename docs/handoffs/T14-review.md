# T14 technical self-review — 10/11/2026

Skill: `.agents/skills/ponytail-review/SKILL.md`. This is the implementing agent's self-review, not independent human usability or answer-key review.

What this change does: Prepares an offline facilitator form and a reproducible 12-slot allocation checker. It records consent and timed responses privately, preserves incomplete attempts, exports the requested CSV and summarizes paired differences by person. It creates no human observations.

Expected load: one facilitator on Linux/WSL, 12 people in sequence, four trials each. No public server, model endpoint or concurrent survey service. Read the complete CLI, its tests/callers and the protocol, existing allocation/input materials, public snapshot references in the draft action rubric, upstream QA handoffs and all changed documentation. Searched consumers of the old blank CSV; none import its old ten-column header.

Concrete findings fixed during review:

1. Label meaning choices between primary trials could teach later answers. Debrief now runs after all four trials; a regression checks prompt order. Retrospective choice/recall bias is disclosed.
2. Ctrl-C at source-count/comments could overwrite an already-completed task's duration and score. It now preserves the primary measurement; tests cover both typed stop and interruption.
3. A stop/withdraw response arriving at the deadline could be treated as timeout. Control responses now take precedence; regression checks late withdrawal. Skip is also supported without removing an attempted trial.
4. Mixing `select` with buffered `readline` could hide rapid pretyped lines and wait until timeout. Console reads bytes without prefetch; real pseudo-terminal tests check rapid consent/start/stop and actual timer expiry.
5. A later collector/scorer edit could alter interpretation of a saved manifest. The manifest now pins source-code bytes as well as materials/consent, and rejects a changed collector. It is an accidental-drift guard, not a tamper-proof attestation.
6. A process crash before timing finished originally left duration=0 in CSV. Interrupted attempts now store JSON null/CSV blank and are counted separately, never as a real zero-second response; the crash regression checks this export too.

No remaining must-fix finding for the technical package at the stated load. Regression covers readiness failure, allocation drift, consent/refusal, timer/late input, skipped/timeout/error/stopped/crashed attempts, withdrawal/no ID recycling, paired arithmetic/partial denominators, empty n/rates, CSV fields/formula handling, no free text in summaries, OS locking, private path restrictions, source-rubric provenance and separation of synthetic from real counts.

Verdict: Ship the technical package. Keep real T14 acceptance blocked. Full offline commands/results are in `T14.md`; no frontend changes need new UI browser acceptance.

Not checked: actual student comprehension, consent with people, independent review of action rubric, selected release's full live pilot-task QA, external recruitment rights, real three-case misunderstanding review. Draft broad safe-action rubric may have a ceiling effect; resolve wording/rubric before locking. Local files are not encrypted; no retention cron or cloud backup protection is claimed.
