# T08 evidence — offline only

- `offline-dev.json`: 12 synthetic developer cases through the real guard/render; six public target claims through Retriever T07 and GeminiAdapter T05 with `_invoke` replaced by a synthetic SDK response. Mock usage/token/cost values test accounting; they are not account usage or a model quality measurement.
- `candidate.json`: current prompt/code/schema/retrieval/corpus/config fingerprints for owner review before freeze; model and price availability are not verified.
- `smoke/`: text HTTP fixture T04 regression at 390/1440. Source/evidence, keyboard, no overflow, axe 0 violations, worker error, no HTTP fallback, wrong-token/DELETE checks. Browser still shows scripted T04 fixture outputs, not live T08 results.
- `docs/handoffs/T08.md`: commands, case results, limitations, and owner-run live instructions. `docs/handoffs/T08-review.md`: full ponytail review and resolved findings.

No Gemini calls, no new downloads, no private user messages, no test_gold. D02/live blocked; D03 seed shortage remains open. Browser reuses local Chromium and libraries; T04 evidence is restored after the run.
