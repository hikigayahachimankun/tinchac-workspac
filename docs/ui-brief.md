# Hướng giao diện TinChắc

Brief cho T03 và T10. Dùng cùng `DESIGN.md`. R2 có thể điều chỉnh cục bộ và cập nhật token sau khi duyệt bản chạy đầu tiên.

## Bố cục

- Màn nhập mở thẳng vào công cụ kiểm tra. Tiêu đề “Kiểm tra thông báo”, hai lựa chọn “Văn bản” và “Ảnh”, một hành động chính. Mô tả phạm vi DUT bằng một câu ngắn.
- Màn OCR đặt bản xem trước cạnh ô chữ có thể chỉnh trên desktop, xếp dọc trên mobile. Nhắc kiểm số tiền và ngày trước khi xác nhận.
- Màn kết quả mở bằng kết luận thận trọng, thời điểm đối chiếu và tóm tắt số lượng theo nhãn. Mỗi hàng ưu tiên phát biểu, trạng thái, lý do và nút xem bằng chứng. Desktop dùng bảng, mobile dùng danh sách có nhãn từng trường.
- Bằng chứng trình bày giống phiếu tham chiếu. Trích đoạn rõ, tiêu đề nguồn, ngày công bố, phiên bản và lúc lưu snapshot. Link gốc và nhãn mô phỏng có vị trí nhất quán.

## Chất liệu và chữ

- Dùng màu khởi đầu từ `DESIGN.md`. Kiểm tương phản trên bản render trước khi khóa token.
- Typography hỗ trợ dấu tiếng Việt, dùng font hệ thống trước. Số tiền và ngày dùng chữ số tabular khi font hỗ trợ. Viền mảnh, khoảng trắng có chủ đích, thẻ chỉ dùng khi gom một đơn vị nội dung.
- Tránh gradient tím, glassmorphism, hero quảng cáo, dashboard KPI giả và badge trang trí. Dùng trạng thái chữ rõ cùng icon, giữ focus thấy được và tránh chuyển động làm gián đoạn thao tác.

## Nghiệm thu

- Chụp màn hình thực ở 390 px và 1440 px. Kiểm chữ tiếng Việt, URL dài, cuộn ngang, thứ tự Tab và focus sau lỗi.
- Kiểm ít nhất trạng thái nhập trống, lỗi upload/OCR, đang xử lý, kết quả hỗn hợp, toàn bộ chưa đủ bằng chứng và lỗi kỹ thuật. Dùng fixture và giữ nhãn mô phỏng.
- Mở được nguồn từ kết quả, quay lại được đúng vị trí. Link gốc hiển thị khác với snapshot.
