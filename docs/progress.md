# Tiến độ TinChắc

Recovery 10/11/2026, giờ Việt Nam. Quyền bảo trì/commit/push và nghiệm thu kỹ thuật đã được giao cho maintainer (D19). `done` chỉ áp dụng phạm vi acceptance đã kiểm; không thay thế human validation hoặc live benchmark. Bằng chứng hiện tại: [audit](../reports/recovery_audit.md), [kế hoạch](superpowers/plans/2026-11-10-recovery.md). Handoff cũ là lịch sử; checkpoint recovery mới nhất được ưu tiên.

| Task | Owner | Trạng thái | Gate thực tế / bước tiếp theo | Handoff |
|---|---|---|---|---|
| T00 | Maintainer / chủ repo (phần con người) | doing | Đã khôi phục Git và quyền quyết định; kiểm môi trường/demo, hoàn tất recovery | [T00](handoffs/T00.md) |
| T01 | Maintainer | done | Model/DB/FTS5/schema tests, 31 examples và OpenAPI không drift; baseline 300 + HTTP recovery 305 tests đạt | [T01](handoffs/T01.md) |
| T02 | Maintainer / người kiểm nguồn | blocked | 5 approved (4 học bổng/1 phí), 1 quarantine; thiếu nguồn phí thứ hai và spot-check độc lập | [T02](handoffs/T02.md) |
| T03 | Maintainer | review | 37 unit + build đạt; đang chạy lại browser/keyboard/mobile | [T03](handoffs/T03.md) |
| T04 | Maintainer | review | Lifecycle fixture/TTL/auth/restart đạt; đang chạy lại browser | [T04](handoffs/T04.md) |
| T05 | Maintainer / chủ tài khoản | blocked | SDK/retry/reservation/unknown usage đạt offline; D02 account/model/quota/giá/preflight chưa có | [T05](handoffs/T05.md) |
| T06 | Maintainer | review | OCR/local limits/confirm/delete đạt backend; đang kiểm lại OCR browser | [T06](handoffs/T06.md) |
| T07 | Maintainer | done | Corpus validate: 6 sources/7 chunks (5 approved); retrieval regression và tái lập đạt; quy mô dữ liệu là gate T02/T09 | [T07](handoffs/T07.md) |
| T08 | Maintainer | blocked | Đã nối production HTTP, 5 test mới và full 305 tests đạt; thiếu Gemini live/public acceptance D02 | [T08](handoffs/T08.md) |
| T09 | Maintainer / người gán nhãn | blocked | 15 dev drafts, 5 dev/0 test family, 0 human gold, NOT frozen; D17 đã duyệt | [T09](handoffs/T09.md) |
| T10 | Maintainer | review | UI/backend production đã nối; unit/build đạt, browser đang kiểm; model live còn D02 | [T10](handoffs/T10.md) |
| T11 | Maintainer | doing | D17 sidecar/accounting đã chốt; đang kiểm preparation/freeze/provenance/scorer; live dev còn D02 | [T11](handoffs/T11.md) |
| T12 | Maintainer / người thử OCR | blocked | Production HTTP scripted regression đạt; chưa đủ 20 ảnh/reference và human correction/live D02 | [T12](handoffs/T12.md) |
| T13 | Maintainer / người chấm evidence | blocked | Chưa benchmark; thiếu holdout/human gold/freeze/D02 và chấm evidence thật | [T13](handoffs/T13.md) |
| T14 | Maintainer / người tham gia tự nguyện | todo | Chuẩn bị consent, allocation và worksheet; không giả kết quả người thật | — |
| T15 | Maintainer | todo | Thiếu static serving/runbook; cold-start máy thứ hai và video chưa thực hiện | — |
| T16 | Maintainer / đại diện dự thi | todo | Chuẩn bị draft factual/AI disclosure; form/identity/benchmark còn thiếu | — |
| T17 | Maintainer / đại diện dự thi | blocked | Phụ thuộc T13–T16; chưa nộp và chưa có receipt thật | — |
