# TinChắc

## Bắt đầu mỗi phiên

- Chạy `git status --short --branch`. Xác định đúng task và nhánh. Giữ nguyên thay đổi của đồng đội.
- Đọc hàng tương ứng trong `docs/progress.md`, quyết định liên quan trong `docs/decisions.md`, mục task Txx và các mục “Đọc trước” trong `TINCHAC_PROJECT_PLAN.md`. Đọc handoff upstream hoặc handoff của task đang dở nếu có. Đọc schema/examples thực tế khi công việc chạm API.
- Kế hoạch là nguồn cho phạm vi và hành vi. Pydantic v2, OpenAPI xuất từ Pydantic và examples phải đồng bộ với schema ứng dụng 1.0. Khi có bất đồng, ghi blocker và giữ phần độc lập chạy được. R1 sở hữu hợp đồng.
- Một phiên thực hiện một task đã giao. Với lựa chọn cục bộ, dễ đảo ngược, chọn cách đơn giản và ghi quyết định. Khi vướng quyền, chi phí, dữ liệu cá nhân, thay đổi hợp đồng hay tập test đã khóa, ghi đúng blocker và tiếp tục phần độc lập.

## Viết và kiểm tra mã

- Trace luồng và đọc các caller hiện có trước khi sửa. Tạo diff nhỏ nhất mà một người khác đọc và kiểm được. Dùng chuẩn ngôn ngữ và module đã có. Mọi abstraction/dependency mới cần một nhu cầu hiện tại trong task. Giữ hành vi caller ngoài phạm vi.
- Giữ cấu trúc §3.4 và tạo tệp khi có trách nhiệm thực. Pydantic sinh OpenAPI. Frontend dùng API types của hợp đồng. Eval dùng pipeline thật qua interface ổn định. Giữ thư mục fixtures tách khỏi dữ liệu live và gold.
- Kiểm đúng ba nhãn `supported`, `contradicted`, `insufficient_evidence`. Nguồn im lặng là thiếu bằng chứng. Lỗi provider là lỗi kỹ thuật. Trạng thái hết hạn là trường riêng. S/C cần citation hợp lệ, đúng scope và thời điểm.
- Ưu tiên fixture. Chỉ R1 vận hành preflight/live với key, ca public đã duyệt và trần chi phí đã chốt. Key và gold test để ngoài phạm vi agent. Không in bí mật, gửi ảnh riêng tư lên model, tải URL do người dùng gửi, nạp tiền, push, merge hoặc deploy trong phiên triển khai thông thường.
- Chạy kiểm tra nghiệm thu của task. Với UI, dùng viewport di động/máy tính, bàn phím và ảnh chụp từ trình duyệt; xem `docs/ui-brief.md`. Với tối ưu hiệu suất, báo số đo trước/sau trên fixture tương đương.

## Bàn giao và tiếp tục

- Ghi checkpoint sau mỗi bước đã kiểm được vào `docs/handoffs/Txx.md` theo mẫu. Ghi branch, trạng thái, kiểm tra đã chạy và kết quả, phần chưa chạy, đúng một bước tiếp theo. Ghi đường dẫn thay vì chép đặc tả hoặc dump log.
- Cập nhật hàng task trong `docs/progress.md` khi đổi trạng thái; giữ nhánh riêng và dùng Git làm nguồn về diff thực tế. Agent đưa task sang review; reviewer xác nhận done.
- Chọn skill theo việc. Dùng `$writing-plans` lúc lập kế hoạch, `$handoff` lúc rút gọn phiên dài, `$ponytail-review` khi review diff, `$impeccable` cho UI. Checkpoint chính thức luôn ở `docs/handoffs/`. Mặc định làm tuần tự trong một agent cho mỗi task.
