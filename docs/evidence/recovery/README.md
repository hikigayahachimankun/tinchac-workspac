# Recovery verification — 10/11/2026

This directory contains technical evidence, not a Gemini benchmark or human evaluation. Historical T04/T06/T10/T12 evidence was preserved; tests wrote fresh outputs here through TINCHAC_EVIDENCE_ROOT. Screenshots use synthetic fixture text only. Mobile/desktop T10 evidence screenshots were opened and inspected. Other screenshots are artifacts of automated assertions; no claim that every screenshot was manually viewed.

Executed gates:

- Full backend/eval:329 passed;31 contract examples/OpenAPI matches;6sources/7exact chunks validate;15dev/0gold/5families validated_NOT_frozen.
- Frontend37Vitest/build pass;20HTTPfixture browser/4mock browser pass. Keyboard,390/1440 (mock also360), no overflow and axe0 in scanned paths.
- Production-build same-origin release2/2 at390/1440, FastAPI without Vite. Initial two release attempts failed on hardcoded8000 probes; corrected to configured origin and stable run passed.
- Fixture27/27/replay27/27; scorer CLI byte-identical synthetic regression passes. These are not model-performance rows.
- `ocr20.json`: real local Tesseract on20rendered dev images/5families,29edits/1812chars, aggregateCER0.016004415011.0heldout; human correction/time null. Images and references regenerate with scripts.ocr_eval; not verdict gold.
- `source_candidates.jsonl`: one actual official HTML candidate, unreviewed embedded rate image omitted, NOT approved; raw/sanitized snapshot stays ignored locally.
- `dev_preparation.json`: actual15input draft preparation, no source/gold read,0human gold, NOT frozen.

Commands and limits are in `docs/handoffs/recovery.md`, per-task handoffs and recovery audit. No actual provider/account usage, human gold, evidence reviewer, consent, volunteer, second physical machine or submission receipt was generated.
