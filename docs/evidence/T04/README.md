# T04 smoke evidence

These captures show a real Vite frontend, proxying to a real FastAPI server in fixture mode.
They are scripted fixture outputs, not evidence of AI accuracy. No provider was called.

- `success-{390,1440}.png`: text pasted into the form, keyboard consent/submit, HTTP result, evidence and full T02 fixture snapshot opened.
- `worker-error-{390,1440}.png`: FastAPI accepts the request, then GET returns failed/PROVIDER_TIMEOUT with no verdict.
- `network-{390,1440}.log`: method/path/status only. No headers, tokens, text payloads or response bodies are recorded.
- Smoke test also checks a refused connection does not fall back to mock, and direct backend wrong-token/delete/read-after-delete behavior.

Reproduce using the exact commands in `docs/handoffs/T04.md` and `frontend/tests/smoke/fixture.spec.ts`.
Final smoke: **2 passed (12.0s)**. Desktop/mobile are Chromium emulated viewports, not physical phones.

## UI audit

Implementation integrity: pass within T04. Existing T03 layout, CSS, focus treatment and banners remain coherent. The HTTP error displays the backend code/message next to the recovery action. All four final captures were visually inspected.

| Dimension | Score | Evidence / limit |
|---|---:|---|
| Accessibility | 3/4 | Keyboard text → consent → submit → result/evidence, and axe A/AA/2.1 AA: 0 violations on HTTP success/evidence and worker error at both widths; no screen reader check. |
| Performance | 3/4 | Build passes, no added dependencies; no latency benchmark or Lighthouse. |
| Theming | 4/4 | Existing T03 tokens/CSS retained, light theme per brief, no theme changes. |
| Responsive | 3/4 | 390/1440 screenshots and overflow checks pass; no physical touch test. T03 regression also covers 360 and text scaling. |
| Implementation integrity | 4/4 | Impeccable detector over changed App/InputForm: []; no visual drift found in captured states. |
| **Total** | **17/20** | **Good**, limited to the measured states. |

P0/P1/P2/P3: no verified UI findings in the measured states. No UI fixes recommended.
Preserve inline evidence, visible fixture banner, keyboard focus and the distinction between technical errors and completed insufficient_evidence.
