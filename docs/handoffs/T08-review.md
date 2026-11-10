What this change does: T08 checks extracted claims against the T07 snapshot. It validates citations, keeps time separate from truth labels, and builds conclusions from templates. I reviewed the uncommitted T08 files and their extraction, retrieval, adapter, render, and fixture job callers for one demo process with at most two jobs.

All findings below describe the first draft and have been fixed. Line references refer to that reviewed draft.

**Must fix:**

1. **A current-availability draft can crash the guard** (`backend/app/services/evidence.py:L195-200`)
   - **What this is:** The guard checks whether a claim that applications are still open has deadline evidence.
   - **Problem:** A supported draft with a contradicting citation passes this branch after the deadline. ClaimVerdict then raises a validation error instead of returning insufficient evidence.
   - **Fix:** Require both the draft label and citation relation to agree with the code result. Keep unsupported drafts as insufficient evidence.
   - **If we skip it:** One valid JSON response becomes a technical failure for the user.

2. **Unreleased source text can reach the model** (`backend/app/services/verify.py:L40-59`)
   - **What this is:** The prompt builder reads the input bundles before sending excerpts to the adapter.
   - **Problem:** A caller can pass a bundle containing a future or quarantined source. The guard filters it later, but the prompt has already exposed its text.
   - **Fix:** Use the same eligible-hit filter before building context. Test both future and quarantined sources.
   - **If we skip it:** A historical check can use information that was unavailable at the requested time.

3. **Only one citation needs to prove its claimed relation** (`backend/app/services/evidence.py:L201-218`)
   - **What this is:** The guard requires a fact that proves a supported or contradicted label.
   - **Problem:** Add a correct fee-negation citation and an award-amount quote marked contradicts. The label is correct, but the unrelated quote keeps its false relation.
   - **Fix:** Check every final citation relation. Keep unrelated quotes as context only.
   - **If we skip it:** The evidence panel presents a real quote as proof of a claim it does not address.

4. **Vietnamese grouping before a magnitude unit changes the amount** (`backend/app/services/normalization.py`)
   - **What this is:** The parser accepts integer VND and shorthand amounts with a unit.
   - **Problem:** The first version reads “5.000 triệu/suất” as five million. Vietnamese grouping makes this five thousand million.
   - **Fix:** Apply the same dot grouping rule before multiplying by triệu or nghìn. Add both magnitude-unit examples as regression tests.
   - **If we skip it:** An amount can be off by a factor of one thousand.

5. **Repeated context blocks the four-field example** (`backend/app/services/verify.py`)
   - **What this is:** A single verification invocation receives all fields extracted from one notice.
   - **Problem:** Repeating scope and hit metadata makes the short four-field fixture reach a conservative input bound of 6,942. T05 rejects it before calling the provider because its cap is 6,000.
   - **Fix:** Share scope and hit metadata through local references and remove duplicate raw values already present in statements. Keep every claim, bundle, excerpt and citation offset; the same fixture now measures 5,788.
   - **If we skip it:** The multi-field flow passes a loose mock but cannot use the actual adapter's input contract.

**Should fix:**

6. **Different date precision creates a false source conflict** (`backend/app/services/evidence.py:L189-194`)
   - **What this is:** The guard compares reviewed facts across the complete bundle.
   - **Problem:** One source says 10 November and another says 10 November at 16:00. The raw tuple comparison treats these compatible dates as conflicting and downgrades a correct date-only claim.
   - **Fix:** Compare dates by their shared precision and money by matching units. Do not treat separate eligibility conditions or listed URLs as conflicting values.
   - **If we skip it:** Correct answers lose coverage when sources use different precision.

7. **An unrelated program changes the reason for a silent source** (`backend/app/services/evidence.py:L185-187`)
   - **What this is:** The guard distinguishes a source that says nothing about fees from a source with the wrong scope.
   - **Problem:** Adding another program's fee fact changes SOURCE_SILENT to SCOPE_UNCLEAR even though the matching scholarship source still says nothing about fees.
   - **Fix:** Check field presence in the matching source scope before using facts from other programs to explain a scope failure.
   - **If we skip it:** Users are asked to fix scope when the missing fact is the actual problem.

The five initial cases (1, 2, 3, 6, 7) were reproduced together before fixes: 5 failed, 37 deselected. Finding 4 was caught in the final parser read and pinned by an added regression. Finding 5 was reproduced by adding the actual adapter input-bound check to the four-field pipeline test; it failed before the packing fix and passed after. All fixes are in T08; upstream files and tests were kept. Regression tests are in `backend/tests/test_verification.py`.

Re-review: all seven findings are fixed. Read the final extraction/normalization, context builder, temporal logic, citation guard, renderer and CLI with their callers. The four-field fixture pipeline and all six public cases also run offline. Source facts and final citation relations are checked; no model conclusion rewrite or raw private audit text is added. The small in-memory corpus is within the declared solo demo limit.

Validation after fixes: 225 backend tests passed, including 57 T08 tests. OpenAPI and corpus checks pass; HTTP fixture smoke passes at both viewports. The six public mock cases also pass schema repair through the T05 adapter without network calls.

Verdict: Ship.
Not checked: Gemini quality, quota/prices, real latency or load across processes; D02 is not verified.
