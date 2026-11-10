# T10 — tự review bằng ponytail-review

What this change does: T10 trình bày đúng ba nhãn và thời gian riêng. Client dùng chế độ backend, cho hủy phiên, đọc lại trạng thái và không tự gửi thêm job.

Phạm vi: chỉ diff T10 trong frontend và tài liệu T10; tải dự kiến một người dùng demo local, một process backend. Đọc callers của pollCheck/createHttpClient, App, OCRReview, SourcePublic và template render.py. Không review lại thuật toán T08 hoặc thay contract.

Các lỗi tìm được và đã sửa trong phiên:

1. Metadata của mọi evidence có sẵn trong DOM dù details đóng làm truy vấn bàn phím/locator bị trùng. Chỉ đưa metadata fallback vào sau khi mở evidence. Ca browser và upstream locator xác minh lại.
2. Sau hủy POST, job có thể trả capability muộn. Giữ khóa gửi trong toàn bộ submit, bỏ kết quả muộn và DELETE bằng capability; nếu xóa lỗi giữ lại để người dùng hủy lại. Test T10 đếm DELETE, không hiện verdict muộn.
3. Lỗi GET có nguy cơ gọi lại POST từ UI cũ. Retry có session chưa kết thúc chỉ gọi pollCheck, nút tạo job mới riêng và có thông báo chi phí. Test đếm đúng một POST dù lỗi GET/120s/resume/cancel.
4. Copy mock trong regression T03 cần giữ đúng ngữ cảnh fixture; lỗi kỹ thuật ở live/replay không gọi là mô phỏng. Đã render copy theo chế độ thực.

Không thấy blocker mới cho UI fixture sau khi trace code. R1 còn sở hữu việc nối HTTP T08 và D02; kiểm simulated live/replay không thay kiểm provider thật. Không sửa tập test upstream, schema, gold hay dependency.

5. Fixture T04 ca N có thể trả source kèm kết quả dù evidence rỗng. Đổi câu đếm thành “nguồn kèm kết quả”, không khẳng định đó là source được trích dẫn hay toàn bộ kho. Đã kiểm lại 17/17 fixture, 20 unit và build sau sửa copy.

Verdict: Ship cho RC offline trong scope T10. 20 unit, 17 browser fixture, 4 browser mock đạt; không tự xác nhận task done hoặc live đã sẵn sàng.
Not checked: provider live/replay thật, screen reader, touch thật, Firefox/WebKit và máy demo của owner.
