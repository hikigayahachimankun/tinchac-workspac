# Tiến độ TinChắc

Starter đã chuẩn bị công cụ làm việc. Trạng thái dưới đây là khởi tạo, cập nhật sau khi nhóm xác nhận thực tế.

| Task | Owner | Trạng thái | Blocker / bước tiếp theo | ETA | Handoff | Giờ thực |
|---|---|---|---|---|---|---|
| T00 | Chủ repo (solo) | doing | Repo/nhánh/phân công đã chốt theo D01; máy demo và các đầu vào còn lại chưa xác nhận | — | — | — |
| T01 | Agent / chủ repo review | review | 55 tests pass; health HTTP 200; 31 examples; OpenAPI tái lập, không drift; chờ chủ repo xem diff | — | [T01](handoffs/T01.md) | Không đo giờ riêng |
| T02 | Agent / chủ repo solo review | review | 5 nguồn đọc đủ (4 học bổng + 1 phí), 1 phí quarantined; 7 SourceVersion valid; D03 thiếu 1 phí; chờ kiểm tay | — | [T02](handoffs/T02.md) | Không đo giờ riêng |
| T03 | Agent / chủ repo solo review | review | Vitest 8 + browser 4 pass, build pass, audit ship; nền T01 lưu cùng commit tích hợp T02–T05; chờ chủ repo nghiệm thu | — | [T03](handoffs/T03.md) | Không đo giờ riêng |
| T04 | Agent / chủ repo solo review | review | HTTP fixture thật; 69 backend + 11 frontend tests, browser T04 2/T03 4, build/OpenAPI pass; review đã sửa 2 lỗi; chờ chủ repo xem diff | — | [T04](handoffs/T04.md) | Không đo giờ riêng |
| T05 | Agent / chủ repo solo review | review | 121 backend (52 T05) + 11 frontend pass; smoke T04 2/2, OpenAPI không drift; review đã sửa 2 lỗi; T04 lưu cùng commit tích hợp T02–T05; D02 chưa xác minh, live do chủ repo chạy | — | [T05](handoffs/T05.md) | Không đo giờ riêng |
| T06 | Agent / chủ repo solo review | review | 141 backend + 13 unit; browser fixture 8/T03 4 pass; vie+eng thật, CER 2 ảnh dev; review sửa 2 lỗi; chờ chủ repo nghiệm thu | — | [T06](handoffs/T06.md) | Không đo giờ riêng |
| T07 | Agent / chủ repo solo review | review | 168 backend (27 T07), OpenAPI và smoke T04 2/2 pass; 10 dev recall@5 10/10; 5 approved/1 excluded; D03 giữ mở; chờ chủ repo nghiệm thu | — | [T07](handoffs/T07.md) | Không đo giờ riêng |
| T08 | Agent / chủ repo solo review | review | 225 backend (57 T08), 12 dev + 6 public mock, OpenAPI/corpus và smoke 2/2 pass; review sửa 7 lỗi; T07 chưa commit; D02 live blocked | — | [T08](handoffs/T08.md) | Không đo giờ riêng |
| T09 | Agent / chủ repo solo review | review | Pilot 5 dev / 0 test family (4 học bổng + 1 phí), 15 dev chưa gold; 30 fixture tests pass; protocol/guide/validator sẵn; NOT frozen, chờ owner gán nhãn và bổ sung holdout | — | [T09](handoffs/T09.md) | Không đo giờ riêng |

| T10 | R2 agent / chủ repo solo review | review | RC offline: 20 unit, 17 fixture + 4 mock browser, build/contracts đạt; live/replay chỉ mock UI, HTTP live chờ R1/T08/D02 | — | [T10](handoffs/T10.md) | Không đo giờ riêng |

| T11 | R4 agent / chủ repo solo review | review | Harness offline ready: 274 tests, fixture/replay 27/27, scorer tái tính khớp; live dev blocked R1/D02, Claim sidecar/accounting chờ owner review D17; chưa mở test thật | — | [T11](handoffs/T11.md) | Không đo giờ riêng |

Thêm các task còn lại từ bảng điều phối §6.1 khi chốt T00. Trạng thái dùng `todo`, `doing`, `blocked`, `review`, `done`.

| T12 | R2 agent / chủ repo solo review | blocked | Diff độc lập sẵn review: 300 pytest + 37 Vitest + 20 fixture/4 mock browser; đã sửa crash API; thiếu HTTP live R1/D02 và 20 ảnh split/correction R3/R4 | — | [T12](handoffs/T12.md) | Không đo giờ riêng |

| T13 | R4 agent / chủ repo; R3 chấm độc lập chưa có | blocked | Kiểm offline: 49 tests eval, corpus/contracts đạt; fixture/replay 27/27, scorer tổng hợp tái lập; chưa chạy benchmark: T09 NOT frozen/0 test, D02/D17 và human scoring chưa đủ | — | [T13](handoffs/T13.md) | Không đo giờ riêng |
