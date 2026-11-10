# Tiến độ TinChắc

Recovery 10/11/2026, giờ Việt Nam. Quyền bảo trì/commit/push và nghiệm thu kỹ thuật đã được giao cho maintainer (D19). `done` chỉ áp dụng phạm vi acceptance đã kiểm; không thay thế human validation hoặc live benchmark. Bằng chứng hiện tại: [audit](../reports/recovery_audit.md), [kế hoạch](superpowers/plans/2026-11-10-recovery.md). Handoff cũ là lịch sử; checkpoint recovery mới nhất được ưu tiên.

| Task | Owner | Trạng thái | Gate thực tế / bước tiếp theo | Handoff |
|---|---|---|---|---|
| T00 | Maintainer / chủ repo (phần con người) | done | Phạm vi solo/quyền/Git/môi trường và toàn bộ T00–T17 đã đối soát; gate con người được phân đúng task | [T00](handoffs/T00.md) |
| T01 | Maintainer | done | Model/DB/FTS5/schema tests, 31 examples và OpenAPI không drift; baseline 300 + HTTP recovery 305 tests đạt | [T01](handoffs/T01.md) |
| T02 | Maintainer / người kiểm nguồn | blocked | 5 approved (4 học bổng/1 phí), 1 quarantine; thiếu nguồn phí thứ hai và spot-check độc lập | [T02](handoffs/T02.md) |
| T03 | Maintainer | done | 37 unit/build, 4 mock browser, mobile/desktop/keyboard/evidence đạt | [T03](handoffs/T03.md) |
| T04 | Maintainer | done | Lifecycle fixture/TTL/auth/restart, HTTP browser và built release smoke đạt | [T04](handoffs/T04.md) |
| T05 | Maintainer / chủ tài khoản | blocked | Key ngoài repo đã nạp an toàn; model metadata GET200; cap3attempts/0.03USD bền vững đã kiểm; billing/quota thực chưa đọc được nên chưa generation | [T05](handoffs/T05.md) |
| T06 | Maintainer | done | OCR local thật, confirm/edit/delete và browser đạt; nghiên cứu ảnh test/human correction thuộc T12 | [T06](handoffs/T06.md) |
| T07 | Maintainer | done | Corpus validate: 6 sources/7 chunks (5 approved); retrieval regression và tái lập đạt; quy mô dữ liệu là gate T02/T09 | [T07](handoffs/T07.md) |
| T08 | Maintainer | blocked | Đã nối production HTTP, 5 test mới và full 329 tests đạt; thiếu Gemini live/public acceptance D02 | [T08](handoffs/T08.md) |
| T09 | Maintainer / người gán nhãn | blocked | 15 dev drafts, 5 dev/0 test family, 0 human gold, NOT frozen; D17 đã duyệt | [T09](handoffs/T09.md) |
| T10 | Maintainer | blocked | UI fixture/metadata các mode, OCR, keyboard và HTTP integration đạt; nghiệm thu provider live còn D02 | [T10](handoffs/T10.md) |
| T11 | Maintainer | blocked | D17/preparation/input+temporal pins/scorer đạt offline, fixture/replay 27/27; live dev còn D02 | [T11](handoffs/T11.md) |
| T12 | Maintainer / người thử OCR | blocked | Production HTTP scripted regression đạt; 20 ảnh dev/5 family đã đo (CER 29/1812); 0 test, human correction/live D02 chưa có | [T12](handoffs/T12.md) |
| T13 | Maintainer / người chấm evidence | blocked | Chưa benchmark; thiếu holdout/human gold/freeze/D02 và chấm evidence thật | [T13](handoffs/T13.md) |
| T14 | Maintainer / người tham gia tự nguyện | blocked | Consent/protocol/48 planned rows sẵn; actual 0 volunteers, chưa có task/answer-key review | [T14](handoffs/T14.md) |
| T15 | Maintainer | blocked | Static serving/runbook và built browser 2/2 đạt; thiếu cold-start máy thứ hai/video/quyền phân phối | [T15](handoffs/T15.md) |
| T16 | Maintainer / đại diện dự thi | blocked | Draft/AI disclosure/checklist sẵn; form/rules HTTP 200 đã kiểm; identity/evidence thực/benchmark còn thiếu | [T16](handoffs/T16.md) |
| T17 | Maintainer / đại diện dự thi | blocked | Review checkpoint sẵn; phụ thuộc T13–T16, chưa nộp và chưa có receipt thật | [T17](handoffs/T17.md) |
