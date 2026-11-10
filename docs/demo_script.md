# T15 — Demo và video dự phòng 3 phút 40 giây

Video là tài sản dự phòng do agent quay thao tác trình duyệt thực, không phải yêu cầu thời lượng BTC đã xác minh. Bản ghi dùng **fixture**, ảnh/chữ tự tạo, không gọi provider. [Video MP4](../artifacts/T15/tinchac-demo-rc.mp4), [storyboard/lời thuyết minh](demo_storyboard.json), [evidence và lệnh](evidence/T15/README.md). Giọng Việt tổng hợp bằng espeak-ng chạy local; phụ đề quay cùng màn hình và watermark fixture suốt video. Đây là diễn tập tự động, không giả người dùng thật.

Chuẩn bị: chạy quickstart ở đầu README, một worker localhost:8000; kiểm `scripts.release_smoke`. Chỉ mở app trong browser sạch, không terminal, AI Studio, key, ledger riêng, ảnh sinh viên hoặc hồ sơ cá nhân. Quyền phân phối ngoài nhóm và dependency vẫn cần chốt; nguồn công khai không đồng nghĩa quyền tái phân phối.

## Bốn tình huống tự tạo

| Input | Thao tác / expected | Điều phải giải thích |
|---|---|---|
| `data/fixtures/ocr/vietnamese-clear.png` | Chọn Ảnh, đọc OCR, sửa về văn bản `original` trong `frontend/src/api/fixture-texts.json`, consent, xác nhận → C; mở quote 5 triệu. Sửa thành `supported`, gửi → S | OCR thật cục bộ, verdict cố định. Sửa tiền minh họa thao tác, không đo độ chính xác sửa tay |
| Văn bản `nei` | Chọn Văn bản, mẫu toàn bộ chưa đủ bằng chứng, consent, kiểm → NEI | Nguồn im lặng về phí 300.000 đồng không chứng minh sai/lừa đảo |
| Văn bản `mixed` | Chọn mẫu ba nhãn, kiểm → S/C/NEI; Tab/Enter mở bằng chứng, đọc snapshot | Nguồn mô phỏng có phiên bản/thời điểm; `.example` không là DUT thật |
| Văn bản `failed` | Chọn mẫu lỗi kỹ thuật, kiểm → PROVIDER_TIMEOUT, không verdict | Lỗi kỹ thuật khác NEI; không tự đổi thành kết quả an toàn |

Chữ/ảnh đều synthetic dev fixture có sẵn, tách khỏi live/gold; không thêm ca hoặc nhãn benchmark. HTTP smoke còn kiểm `supported` riêng để cho thấy app không chỉ cảnh báo.

## Timeline và lời nói

| Thời điểm | Cảnh / thông điệp |
|---|---|
| 0:00–0:25 | Mở app có banner fixture; giới thiệu DUT/phạm vi, không gọi Gemini, không là benchmark |
| 0:25–0:50 | Upload ảnh, kiểm/sửa OCR, consent; 7 triệu khác nguồn 5 triệu; mở quote/snapshot |
| 0:50–1:25 | Sửa thành 5 triệu → S trong fixture; chưa nghiệm thu ca DUT thật được hỗ trợ |
| 1:25–1:55 | Phí 300 nghìn → NEI, hướng hỏi kênh chính thức |
| 1:55–2:25 | Ba nhãn, mở bằng chứng bằng bàn phím; snapshot khác trang gốc; expired không chứng minh giả mạo |
| 2:25–2:50 | Worker lỗi, 0 verdict; adapter/ledger được kiểm với provider mock |
| 2:50–3:10 | Chặn POST bằng Playwright → lỗi kết nối, không NEI; fixture/video dự phòng có nhãn |
| 3:10–3:25 | Chèn HTTP429 → RATE_LIMITED, 0 verdict; không dùng quota thật/paid fallback |
| 3:25–3:40 | Một worker local; cold-start WSL + CI Ubuntu độc lập đạt; còn laptop vật lý, ca thật QA, benchmark/người thử/quyền phân phối; T15 chưa done |

Lời thuyết minh đầy đủ: `docs/demo_storyboard.json`. Không dùng bảng A/B/C hoặc số pilot giả. Expired chỉ có trong mock T03, không thuộc bốn ca HTTP/video này; video giải thích nguyên tắc, không dàn dựng ca expired thật.

## Dự phòng và replay

Mất Internet nhưng localhost còn chạy: fixture/OCR đã cài vẫn chạy; link gốc online có thể không mở. Mất backend: giữ lỗi, khởi động lại một worker; không tự thay kết quả. MP4 cục bộ là dự phòng độc lập với app. Chặn POST là diễn tập lỗi kết nối bằng injection, **không phải** tắt mạng vật lý.

CLI đã chạy 27/27 fixture và 27/27 replay. Đây là **replay của fixture**, mode/origin ghi rõ, không phải recording model live, bốn HTTP case hay benchmark. Trên checkout đầy đủ, hai output phải mới:

```bash
.venv/bin/python -m scripts.run_eval --mode fixture --output /tmp/tinchac-demo-fixture
.venv/bin/python -m scripts.run_eval --mode replay \
  --cases /tmp/tinchac-demo-fixture/cases.jsonl \
  --replay /tmp/tinchac-demo-fixture/runs.jsonl --output /tmp/tinchac-demo-replay
```

HTTP replay chưa cấu hình recording nên trả 503; không bật `APP_MODE=replay` rồi giả app có kết quả. Bằng chứng thật trước T15 ở `docs/evidence/T12/free-tier-http-dev-fixed-2026-11-10/`: hai ca completed đều NEI, ca 3 lỗi 503. Không dàn dựng thành ca S. HEAD ba URL DUT approved trả 200 trong T15 chỉ kiểm availability; chưa đóng gate ca thật được hỗ trợ/quyền phân phối.

## Tái diễn tập/quay

Dùng Chromium đã cài theo hướng dẫn Playwright của repo; `TINCHAC_CHROMIUM_PATH` nếu binary ngoài. Server fixture đang chạy port 8000:

```bash
node scripts/record_demo.mjs --output /tmp/tinchac-demo-browser-new
# Quay khoảng 220 giây, output mới:
node scripts/record_demo.mjs --output /tmp/tinchac-demo-record-new --record
# ffmpeg/espeak-ng là công cụ authoring ngoài app:
.venv/bin/python -m scripts.render_demo \
  --video /tmp/tinchac-demo-record-new/RECORDING.webm \
  --output /tmp/tinchac-demo-new.mp4
```

Tên `.webm` thực ở `result.json`, không copy nguyên placeholder. Quay/render từ checkout đầy đủ; runtime package không kèm authoring tools. Render dùng Pillow đã có trong lock và font DejaVu ở bước OCR. Metadata/hash/privacy audit nằm trong evidence T15. T16/T17 chỉ dùng tài sản này với nhãn fixture/RC và các gate chưa đạt trong checklist.

Cập nhật sau quay: [CI Ubuntu độc lập](evidence/T15/independent-ci.json) đã thực chạy thành công. End card và đoạn giọng cuối được biên tập lại theo kết quả này, không dựng lại hành vi ứng dụng. Chưa kiểm laptop demo vật lý.
