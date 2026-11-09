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
| T09 | R4 | todo | Chuẩn bị hướng dẫn nhãn, tạo dữ liệu sau nguồn T02 | — | — | — |

Thêm các task còn lại từ bảng điều phối §6.1 khi chốt T00. Trạng thái dùng `todo`, `doing`, `blocked`, `review`, `done`.
