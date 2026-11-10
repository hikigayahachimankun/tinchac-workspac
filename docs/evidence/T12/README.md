# T12 QA artifacts

Only synthetic fixtures and aggregate metadata. No private screenshots, capability values, raw request logs, provider prompts, keys, gold or participant data.

- `build.json`: exact file-hash inventory, branch, base commit and working-tree build ID. It is not a release commit or a frozen experiment version.
- `client-only.patch`: phần sửa T12 riêng, inverse SHA256 đã đối chiếu upstream T10.
- `commands.md`: browser wrapper và các lệnh audit inline đã thực chạy.
- `access-log-audit.json`: Uvicorn localhost synthetic canary, raw log tạm đã xóa.
- `privacy-audit.json`: ten synthetic gitignore probes and static key-pattern counts; no real key was read for comparison.
- `privacy-{390,1440}.json`: browser privacy assertions, not raw logs.
- `empty-ocr-confirmed-{390,1440}.png`: synthetic blank image/manual fixture flow at both viewports. Reviewed visually.
- `ocr-existing.json`: two existing dev images/one family, automatic CER only. Corrected human evaluation explicitly NOT RUN.

Read `reports/qa_smoke.md` for commands, expected/actual/build table, blockers, the test history and the T15 release checklist. `docs/handoffs/T12-review.md` is a self-review; owner still accepts the change.
