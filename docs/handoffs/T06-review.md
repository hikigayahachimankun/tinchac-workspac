What this change does:
It reads PNG/JPEG images locally and lets the user review the text before checking it. It uses the existing fixture pipeline and stores asset access tokens as hashes. This review assumes one local server process and a few demo users, as specified in the plan.

**Must fix:**

1. **Checking OCR again can erase manual edits** (`frontend/src/components/OCRReview.tsx:L29-41`, `poll`)
   - **What this is:** After the two-minute poll limit, the user can type text and ask for OCR status again.
   - **Problem:** A late ready response calls `setText` with OCR text. It replaces the user's draft, including corrected money or dates.
   - **Fix:** Track whether the user edited the draft. Only fill untouched drafts from an OCR response; reset that flag on a new image.
   - **If we skip it:** A corrected number can silently revert before confirmation.

2. **Changing input mode leaves a retry for a deleted asset** (`frontend/src/App.tsx:L39-50`, mode buttons and retry state)
   - **What this is:** A failed image check can expose a retry button. Leaving the image view deletes its asset.
   - **Problem:** The error and retry data stay visible after switching to text. The old retry still submits the deleted asset token, so the server returns 404.
   - **Fix:** Clear the previous output, error and retry data when changing input mode.
   - **If we skip it:** A visible retry action cannot succeed and sends an expired capability again.

Verdict: fix 1 and 2 first.
Not checked: public hosting, multiple server processes, physical mobile devices, provider calls or the locked evaluation set.


## Fixes and second pass

Both findings were reproduced in browser tests before the fixes: the draft changed from 5 million to 7 million, and the deleted-asset retry stayed visible. Both tests pass after the small fixes. `OCRReview` now fills only an untouched draft. Mode changes clear the old check output and retry data.

Re-read intake, OCR, asset routes, middleware, Jobs, HTTP clients, UI, fixture adapter and their tests. Checked byte/pixel caps and real decode; streamed multipart file closure; raw image cleanup on OCR success/error/timeout, storage failure and restart; token hashing, authorization, DELETE/TTL and late writes; and confirmed_text through the real fixture adapter. Existing OpenAPI components and paths are unchanged.

Final checks: 141 backend tests, 13 frontend unit tests and 8 real fixture browser tests pass. Build and OpenAPI check pass. Browser tests verify no check before confirmation, manual fallback, draft preservation, deletion, and the result for the edited amount. Screenshots were inspected at 390 and 1440 px; WCAG A/AA checks pass on the edited-result views.

Verdict: Ship.
Not checked: public hosting, multiple server processes, physical mobile devices, provider calls or the locked evaluation set. “Ship” here means ready for the owner's local T06 review, not deploy or task done.
