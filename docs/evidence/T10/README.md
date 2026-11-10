# T10 — bằng chứng kiểm UI

Tất cả dữ liệu kiểm tra là fixture tổng hợp của repo; không dữ liệu người dùng, không provider calls. `live.png` và `replay.png` **chỉ mô phỏng phản hồi hợp đồng** bằng Playwright routes; không phải bằng chứng model/live hay nguồn DUT thật đã được mở. URL public trong mock chỉ dùng kiểm cấu trúc link; không truy cập mạng ngoài.

- `input-{390,1440}.png`: màn nhập.
- `evidence-{390,1440}.png`: HTTP fixture thật; ba nhãn, bản snapshot, ngày/phiên bản.
- `image-result-{390,1440}.png`: OCR local thật, sửa tiền 7 → 5 trước xác nhận, HTTP fixture hỗ trợ trường đã sửa.
- `all-N.png`, `failed.png`: kết quả N tách khỏi lỗi worker. Fixture backend hiện trả một source kèm kết quả ngay cả ca N; ca sources=[] kiểm riêng bằng unit render.
- `slow.png`: clock mô phỏng vượt 120 giây; nút đọc trạng thái/hủy, không POST mới.
- `live.png`, `replay.png`: phản hồi mô phỏng có warning, expired, retry snapshot GET, escaped HTML, link công khai mở tab mới với rel an toàn.

Test: `frontend/tests/smoke/t10.spec.ts`. Viewport 390/1440 cho text/OCR; 1280 mặc định cho ca lỗi/mode. Upstream T03 còn kiểm 360/390/1440, bàn phím và 200% text. Axe chỉ quét nhóm WCAG A/AA ở đường text/evidence; không phải chứng nhận toàn bộ accessibility.

Đã xem ảnh evidence ở hai cỡ, image result mobile, all-N, live mock và slow. Không thay token/theme/styles/dependency. Bản gốc upstream T04/T06 được backup/restore khi regression, không ghi đè bằng chứng của task khác.

Giới hạn: Chromium headless trên Linux, viewport mô phỏng; chưa thiết bị/touch thật, screen reader, Firefox/WebKit, mạng/provider live hoặc máy demo owner. Không đo tốc độ/độ chính xác model.
