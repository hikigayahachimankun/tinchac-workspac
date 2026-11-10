# Bằng chứng T06

- `ocr-smoke.json`: Tesseract 5.5.0 thật, `vie+eng`, timeout 20s; 2 mẫu tổng hợp/1 family dev, CER tự động trước sửa. `scripts/ocr_smoke.py` tái tạo từ fixture và font DejaVuSans, blur radius 10. Không phải số đo benchmark/gold.
- `ocr-clear-{390,1440}.png`: local preview + chữ OCR trước xác nhận, layout mobile/desktop.
- `ocr-edited-result-{390,1440}.png`: preview ảnh 7 triệu, ô sửa 5 triệu và kết quả supported cho 5 triệu.
- `network-{390,1440}.txt`: method/path không capability, kèm confirmed_text fixture và kết quả kiểm tra. Browser test đối chiếu request CheckCreate image, rồi GET check thật: amount=5000000, supported=1, contradicted=0. Backend integration test còn kiểm checks.text_modified=1; giữ nguyên text → 0.
- `ocr-blurred-manual.png`: cảnh báo chữ rỗng vẫn hiện khi nhập tay. Ca failed OCR mô phỏng GET asset qua Playwright route, POST check và pipeline vẫn thật; xác nhận input_mode=text, hai trường asset null.
- `text-regression/`: smoke T04 chạy lại trong T06, không thay bằng chứng gốc T04.

Browser: Chromium 158 / Playwright 1.65, fixture HTTP FastAPI + Vite, không Gemini. Dùng viewport 390 và 1440; keyboard Tab/Space/Enter cho xác nhận; kiểm overflow và WCAG 2 A/AA + 2.1 AA ở kết quả sau sửa (0 violations). Đã xem ảnh rõ desktop/mobile, ảnh kết quả mobile và ảnh mờ. Các test mới nằm ở `frontend/tests/smoke/ocr_review.test.tsx`. Hai regression review đã tái hiện fail trước sửa và pass sau sửa.

Không scan toàn bộ best-practice axe: banner `role=note` ngoài landmark là baseline T03/T04; không đổi phần đó trong T06. Không kiểm touch/thiết bị thật, screen reader, Firefox/WebKit, máy demo thứ hai, public/multi-process hay provider live. Không đo thời gian sửa của người dùng: thao tác browser tự động không phải pilot. Không dùng các ảnh này để tuyên bố hoàn thành bộ 20 ảnh §4.6.
