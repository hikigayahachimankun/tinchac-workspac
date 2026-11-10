# Tiến độ TinChắc

Recovery 10/11/2026, giờ Việt Nam. Quyền bảo trì/commit/push và nghiệm thu kỹ thuật đã được giao cho maintainer (D19). `done` chỉ áp dụng phạm vi acceptance đã kiểm; không thay thế human validation hoặc live benchmark. Bằng chứng hiện tại: [audit](../reports/recovery_audit.md), [kế hoạch](superpowers/plans/2026-11-10-recovery.md). Handoff cũ là lịch sử; checkpoint recovery mới nhất được ưu tiên.

| Task | Owner | Trạng thái | Gate thực tế / bước tiếp theo | Handoff |
|---|---|---|---|---|
| T00 | Maintainer / chủ repo (phần con người) | done | Phạm vi solo/quyền/Git/môi trường và toàn bộ T00–T17 đã đối soát; gate con người được phân đúng task | [T00](handoffs/T00.md) |
| T01 | Maintainer | done | Model/DB/FTS5/schema tests, 31 examples và OpenAPI không drift; baseline 300 + HTTP recovery 305 tests đạt | [T01](handoffs/T01.md) |
| T02 | Maintainer / người kiểm nguồn | blocked | 5 approved (4 học bổng/1 phí), 1 quarantine; thiếu nguồn phí thứ hai và spot-check độc lập | [T02](handoffs/T02.md) |
| T03 | Maintainer | done | 37 unit/build, 4 mock browser, mobile/desktop/keyboard/evidence đạt | [T03](handoffs/T03.md) |
| T04 | Maintainer | done | Lifecycle fixture/TTL/auth/restart, HTTP browser và built release smoke đạt | [T04](handoffs/T04.md) |
| T05 | Maintainer | done | Free Tier do chủ tài khoản xác nhận; preflight thật3/3,859input/1126output,0USD ước tính; cap/quota/no-retry/refusal bền vững đã kiểm (D24) | [T05](handoffs/T05.md) |
| T06 | Maintainer | done | OCR local thật, confirm/edit/delete và browser đạt; nghiên cứu ảnh test/human correction thuộc T12 | [T06](handoffs/T06.md) |
| T07 | Maintainer | done | Corpus validate: 6 sources/7 chunks (5 approved); retrieval regression và tái lập đạt; quy mô dữ liệu là gate T02/T09 | [T07](handoffs/T07.md) |
| T08 | Maintainer | blocked | Preflight thật đạt; 2 DEV rounds và replay guard đã lưu; HTTP sửa context/ID, còn503unknown và thiếu full live acceptance (D25) | [T08](handoffs/T08.md) |
| T09 | Maintainer / người gán nhãn | blocked | 15 dev drafts, 5 dev/0 test family, 0 human gold, NOT frozen; D17 đã duyệt | [T09](handoffs/T09.md) |
| T10 | Maintainer | blocked | UI/fixture/browser và HTTP integration offline đạt; HTTP thật mới2ca hoàn tất/run, chưa đủ nghiệm thu live/UI | [T10](handoffs/T10.md) |
| T11 | Maintainer | blocked | D17/scorer/pins/shared-context đạt offline; model preflight thật đạt; chưa đủ dev gold/test families/freeze để benchmark | [T11](handoffs/T11.md) |
| T12 | Maintainer / người thử OCR | blocked | HTTP thật run1:1/12, run2:2/12 rồi503unknown; 20ảnh dev CER29/1812; còn0heldout/human correction và full live gate | [T12](handoffs/T12.md) |
| T13 | Maintainer / người chấm evidence | blocked | Chưa benchmark; preflight đã đạt, còn holdout/human gold/freeze, provider reliability và chấm evidence thật | [T13](handoffs/T13.md) |
| T14 | R3 maintainer; R2 kỹ thuật hỗ trợ / người tự nguyện | blocked | Collector local/consent/timer/CSV/summary, kiểm 48-row allocation và rubric nguồn dự thảo sẵn; 20 T14 + full offline392 tests đạt, actual n=0; còn QA đúng build, chốt rubric và quyền tuyển/người thật | [T14](handoffs/T14.md) |
| T15 | R1 autonomous maintainer; R2 hỗ trợ | blocked | Internal fixture RC: allowlist package, cold-start WSL + CI Ubuntu độc lập đạt, 397 pytest/37 Vitest, browser390/1440, video3:40 và fault injection; còn ca DUT thật đạt QA, laptop demo vật lý và quyền phân phối | [T15](handoffs/T15.md) |
| T16 | Maintainer / đại diện dự thi | blocked | Draft/AI disclosure/checklist sẵn; form/rules HTTP 200 đã kiểm; identity/evidence thực/benchmark còn thiếu | [T16](handoffs/T16.md) |
| T17 | Maintainer / đại diện dự thi | blocked | Review checkpoint sẵn; phụ thuộc T13–T16, chưa nộp và chưa có receipt thật | [T17](handoffs/T17.md) |
