---
name: TinChắc
description: Công cụ tra cứu bằng chứng dành cho sinh viên DUT
---

# Design System — TinChắc

<!-- Hướng thiết kế đề xuất trước triển khai. Cập nhật từ giao diện sau khi R2 duyệt. -->

## Overview

Phiếu đối chiếu học vụ. Mỗi nhận định đặt cạnh căn cứ và ngày đối chiếu. Bố cục sáng, có nhịp như một tài liệu tham chiếu ngắn. Ưu tiên đọc rõ và thao tác nhanh trên điện thoại.

## Colors

- Giấy ấm `#F7F5EF` làm nền.
- Mực đậm `#172E30` dành cho nội dung.
- Xanh đậm `#165E58` dành cho hành động chính và điểm nhấn.
- Ba nhãn dùng chữ và biểu tượng. Chọn màu trạng thái sau khi kiểm tương phản trên bản render.

## Typography

Dùng font hệ thống có đủ dấu tiếng Việt. Tiêu đề ngắn, ưu tiên chữ dễ đọc ở cỡ nhỏ. Số tiền và ngày dùng chữ số tabular khi font hỗ trợ.

## Layout

Luồng nhập và xác nhận tập trung theo một trục. Trên desktop, nội dung ảnh và chữ OCR có thể đặt cạnh nhau. Trên điện thoại, ảnh và chữ xếp dọc. Chi tiết nguồn nằm gần phát biểu được đối chiếu.

## Elevation & Depth

Phân nhóm bằng khoảng trắng, đường kẻ mảnh và bề mặt phẳng. Dùng chuyển động ngắn khi có ích để hiểu trạng thái.

## Shapes

Góc bo nhẹ và nhất quán. Vùng bấm đủ rộng, đường focus dễ thấy.

## Do’s and Don’ts

- Ưu tiên bằng chứng và hành động trong từng màn hình. Xem `docs/ui-brief.md` cho nội dung và nghiệm thu.
- Tránh nền tím chuyển sắc, thẻ kính, hero marketing và bảng chỉ số mô phỏng.
