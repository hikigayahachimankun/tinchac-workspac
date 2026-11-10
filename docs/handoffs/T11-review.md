# T11 review — sequential self-review, not independent owner acceptance

What this change does: It runs the same target and official bundle through A/B/C and a temporal ablation. It scores saved predictions offline and keeps API failures in the planned denominator. Expected load is one solo operator, one sequential writer, at most72 test targets plus24 temporal invocations.

## Findings corrected before handoff

1. **Fresh adapter could not start.** T05 permits max_calls only1..3 for preflight; the first harness draft passed480. The new fresh-path retrieval failure test reproduced the exception before any output. Harness now bounds schedule size and uses the standard adapter without the preflight-only argument; retry and durable stage/global money caps remain T05's responsibility.
2. **Duplicated metadata exceeded the provider context limit.** Full source.text and repeated scope/date strings caused even tiny multi-version fixtures to fail INPUT_TOO_LARGE, disproportionately affecting C. All systems now receive the same compact source representation with full selected chunk text, title/date/scope/facts/URL; scope interning and removing repeated dates/provenance retain reasoning information. The cap regression checks all8 fixture cases across all4 variants against the exact T05 bound including schema/prompt overhead.
3. **Stop threshold counted calls rather than cases.** One failed system for8/72 targets could exceed10% affected targets while staying below10% invocations. The run now counts unique affected case IDs, stops on >10% technical-error cases or budget, and keeps missing rows in scoring.
4. **Unknown accounting and mixed artifacts could yield misleading totals.** Known subtotal is now explicitly flagged; total cost becomes N/A on unknown/missing accounting and fixture/replay have no inference latency/cost estimate. Scorer rejects duplicate keys, model/config/prompt drift, wrong target, different shared bundle and foreign batches; absent human review makes ECV N/A.

## Validation

`eval/tests/` uses8 artificial outcomes with hand-computed metrics, unequal families, API ERROR, alternatives retrieval, bad citation, zero denominators, missing review/row, paired ablation, fixture/replay/CLI and actual T05 adapter with mocked SDK/ledger. Full command `.venv/bin/python -m pytest eval/tests backend/tests -q`: **274 passed**, no warnings. `.venv/bin/python -m scripts.export_contracts --check`:31 examples/OpenAPI match. Scripted fixture and replay each27/27; synthetic scorer repeated output matches byte-for-byte.

Verdict: Ship the offline harness for owner review. Full live acceptance remains blocked by R1/D02 and review of D17 Claim preparation/accounting proposals. No shared service/API/schema/gold/test changes were made.

Not checked: real account/model/pricing/quota, live usage, sealed test, human evidence review, OCR/end-to-end benchmark and frontend (no UI changes).
