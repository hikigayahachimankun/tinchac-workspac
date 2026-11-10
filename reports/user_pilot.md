# T14 — Bộ công cụ pilot sẵn; chờ dữ liệu thật

Cập nhật 10/11/2026, giờ Việt Nam. R3, kỹ thuật R2 hỗ trợ do cùng maintainer thực hiện tuần tự. **T14 blocked cho nghiệm thu người dùng**, không đánh dấu done.

**n thực tế = 0 người**, 0 consent thật, 0 lượt quan sát thật. Kiểm tra các đường dẫn pilot riêng hiện có không tìm thấy kết quả/consent/readiness thật. U01–U12 trong bảng là slot dự kiến, không phải người đã tuyển. Không gửi lời mời hoặc liên hệ ai; chưa có quyền liên hệ. Không dùng AI/synthetic làm người tham gia.

| Hạng mục | Mục tiêu / kế hoạch | Kết quả người thật |
|---|---|---|
| Người tự nguyện | 12 sinh viên DUT, từ đủ 18 tuổi | 0; chưa tuyển |
| Lượt | 12 × 4 = 48; 2 manual/2 TinChắc mỗi người | 0/48; chưa chạy |
| Family | 4 family khác nhau/người, không lặp biến thể | Chưa có quan sát |
| Hành động đúng | Đáp án hành động định trước từ nguồn | Chưa chấm; mẫu số 0, tỷ lệ không tính |
| Thời gian | Tối đa 180 giây/case, giữ timeout | Chưa đo; không điền 0 giây |
| Hiểu nhãn / mở nguồn | Debrief sau 4 lượt / số nguồn mở thật | Chưa đo |
| Chênh lệch theo người | Median của delta TinChắc − manual | Chưa tính; 0 cặp |
| Ba ca hiểu sai nhãn | Review ba ca thật đầu tiên nếu có | **Chưa thực hiện**, không có ca thật |

## Vật liệu và công cụ có thể dùng lại

- Quy trình, lời mời chưa gửi, consent/quyền dừng/xóa và rubric: `eval/usability/protocol.md`, `scripts/user_pilot.py::CONSENT`, `eval/usability/readiness.blank.json`.
- `eval/usability/tasks.json` giữ nguyên bốn public DEV family đã lộ: học bổng, sửa một giá trị, phí chưa xác minh và hạn học phí. `action_key.draft.json` có rubric dự thảo được agent đối chiếu snapshot/version/hash/quote approved; chưa có review độc lập hoặc khóa rubric. Cách hỏi rộng khiến ba lựa chọn xác minh/đợi đều có thể an toàn; cần chốt rõ giới hạn ceiling effect trước pilot. Không đọc gold, không lấy dự đoán model làm đáp án hoặc gán expected labels để bù chỗ trống.
- `eval/usability/allocation.csv` giữ nguyên phân bổ định trước: 12 × 4, hai lượt mỗi điều kiện, sáu người bắt đầu mỗi cách, mỗi task sáu lượt mỗi điều kiện. CLI kiểm tự động trước thu thập. Không thay phân bổ theo kết quả.
- Collector terminal cục bộ, không network/provider: consent → timer chung cho hành động/bằng chứng → số nguồn/nhận xét → debrief hiểu nhãn sau primary tasks. Lưu timeout, lỗi kỹ thuật, dừng và process crash; không chuyển lỗi API thành `insufficient_evidence`.
- CSV đúng bảy cột `participant_id,case_id,condition,order,duration,action_correct,comments`; duration giây. Dữ liệu thật dưới ignored `data/private/user_pilot/`, JSON riêng giữ consent/status/hiểu nhãn/số nguồn; không commit raw CSV/nhận xét. Summary chỉ in số tổng hợp, tính delta trên người đủ bốn lượt; người thiếu lượt vẫn ở số quan sát. Timeout giữ 180 giây và hành động chưa đúng. Interrupted có thời gian không biết được báo riêng.

## Quan sát, ý kiến và kỳ vọng

**Quan sát người thật:** chưa có. Kết quả kỹ thuật synthetic chỉ chứng minh collector/validation/arithmetic hoạt động trên input giả lập, không chứng minh sinh viên hiểu UI hoặc TinChắc cải thiện hành động.

**Ý kiến người thử:** chưa có; không có quote, lời khen hoặc bất đồng nào được gán cho sinh viên. Công cụ có trường nhận xét riêng và giữ ý kiến trái chiều.

**Kỳ vọng cần kiểm:** người dùng phân biệt được nguồn im lặng với mâu thuẫn, hết hạn với giả mạo, lỗi kỹ thuật với thiếu bằng chứng, và chọn bước tiếp theo phù hợp với scope/thời điểm. Đây là câu hỏi nghiên cứu, chưa phải kết quả.

**Thay đổi UI:** không có. Chưa có minh chứng người thật để sửa câu chữ/hiển thị. Khi có, ghi observation ID riêng, phân biệt quan sát hành vi và ý kiến, sửa tối thiểu rồi kiểm mobile/desktop/keyboard/browser theo UI brief. Không dùng dữ liệu pilot để chỉnh model từ benchmark đã freeze. API/schema/model/dataset/test benchmark không đổi; không đổi experiment run version.

## Gate còn thiếu và bàn giao T15/T16

T10/T12 có bằng chứng fixture/browser lịch sử, nhưng fixture hiện chỉ hỗ trợ family Minh Họa, không chạy được bốn input pilot này. Hai batch HTTP live ở upstream chưa hoàn tất đủ case (D25); không nhận là QA pass của pilot. Replay HTTP cũng chưa có bản ghi được cấu hình. Cần build hỗ trợ toàn bộ task và evidence QA tương ứng, action key có căn cứ được review, rồi mới khóa manifest và thu consent. Cờ readiness là khai báo có nguồn của điều phối viên, không tự chứng minh con người/QA đã xảy ra.

T15 có thể diễn tập **kỹ thuật synthetic** bằng CLI; T16 dùng đúng n=0 và giới hạn trên, không tuyên bố tăng tốc/độ đúng/hài lòng. Không đưa số rehearsal vào bảng kết quả người dùng. Nếu thu dưới 12 người thì ghi **pilot nhỏ, mẫu thuận tiện** và n thực tế; không chờ vô hạn hoặc bù dữ liệu giả trước hạn nội bộ 22/11/2026. Không dùng ca cá nhân, ảnh hay trích nguyên văn nhận xét nếu chưa có quyền riêng.

Lệnh/kết quả kỹ thuật ở `docs/handoffs/T14.md`; self-review ở `docs/handoffs/T14-review.md`. **Chi phí T14: 0 calls provider, 0 tokens, 0 USD / 0 VND.**

Bước tiếp theo: hoàn tất gate QA/action key cho đúng build và tổ chức pilot tự nguyện qua kênh được phép liên hệ, dùng quy trình đã khóa; cập nhật kết quả chỉ khi có dữ liệu thật.
