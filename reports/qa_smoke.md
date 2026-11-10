# T12 — QA smoke và release checklist T15

Ngày 10/11/2026 (UTC+7). R2 agent; chủ repo solo review cuối. Nhánh `task/T12-failure-privacy`, nền `1c8e8ce`, không commit/PR/push/merge/deploy. Build **`t12-f17f9a808da7a1b6`**, inventory SHA256 tại `docs/evidence/T12/build.json`; mọi hàng dưới có build B = ID này. Code/tests/config được hash; tài liệu/evidence không tham gia build ID. Các lượt baseline/reproduce trước sửa không được gán kết quả pass cho build B.

**Gate T12: BLOCKED cho nghiệm thu đầy đủ.** Diff QA độc lập và sửa client sẵn owner review. B01 crash payload API đã sửa theo quyền owner; B02 HTTP live và B03 bộ ảnh split/người sửa chưa có. Chưa cho T15 công bố live hoặc OCR benchmark đạt. Các flow fixture đã kiểm có thể dùng để diễn tập có nhãn, giữ giới hạn này trên slide/demo.

## Case / expected / actual / build

| Case và đường kiểm | Expected | Actual của phiên | Build |
|---|---|---|---|
| Upload giả MIME/không phải ảnh/truncated | 415, không raw/resource thừa | Test T06 đạt; canary Uvicorn thật 415, filename không có trong log | B |
| >5 MiB, >12M pixel, streaming không Content-Length | 413, đóng multipart spool | Test T06 đạt, cả biên 12M và 12M+3000 | B |
| OCR rỗng | Ready + chữ rỗng, nhập tay, không tự POST checks | Backend + browser 390/1440 đạt; chỉ POST sau sửa/consent | B |
| OCR exception/timeout | Failed OCR_FAILED, raw xóa, fallback text | T06/T12 đạt, exception canary không ra response/log | B |
| Token thiếu/sai/query-only | 404; token đúng mới đọc/xóa | T04/T06/T12 đạt; hash-only, raw owner-only | B |
| DELETE lúc check/OCR đang chạy; TTL lúc worker còn chạy | Không worker nào hồi sinh dữ liệu | T04/T06 race tests đạt; không giữ transaction qua công việc chậm | B |
| Restart check/OCR dở | JOB_INTERRUPTED, không tự gọi lại | T12 khởi động app mới với cùng DB: cả hai failed; raw/request bị dọn | B |
| Missing source / source silent | N + NO_SOURCE/SOURCE_SILENT | T08 + 12 tổ hợp T12 đạt; UI vẫn hiện phạm vi và bước tiếp | B |
| Source conflict | N + SOURCE_CONFLICT, giữ cả hai nguồn | Service/guard T08 và T12 đạt, giữ hai nguồn; browser kiểm evidence chung, chưa ca conflict riêng | B |
| Expired historical deadline | S nếu đúng mốc + expired riêng | Service T08/T12 đạt; T10 browser hiển thị “hết hạn không chứng minh giả mạo” | B |
| Input/source injection | Là DATA; không vượt fact/citation guard | T08/T12 scripted drafts bị guard hạ N đúng fixture; **không phải phép đo model chống injection** | B |
| Provider timeout/budget/corpus/internal | Failed/ErrorDetail, result null, không N | T12 bốn lỗi qua HTTP fixture + guard/provider tests đạt | B |
| HTTP hỏng/HTML/wrong schema/network | Technical error, không tự fallback/POST mới | Vitest + T10 browser đạt | B |
| B01: completed summary/warnings/date hoặc nested field hỏng | ApiError trước React, không blank screen | 11 payload regressions Vitest đạt; browser summary:null hiện alert, 0 verdict/pageerror | B |
| Error code `toString` / public source metadata hỏng | INTERNAL_ERROR/rejected, không React crash | 2 unit regressions đạt; citations cũ giữ qua nhánh catch hiện có | B |
| Snapshot GET lỗi / trang gốc mất | Quote/version còn; retry GET, không sửa nhãn | T10 browser đạt; mock live/replay chỉ kiểm presentation | B |
| GET lỗi/120s/cancel/POST muộn | Không tự tạo job mới; DELETE bằng capability | T10 unit/browser đạt; có nhắc chi phí không hoàn bảo đảm | B |
| URL/storage/console | Không text/token trong URL/log; không browser storage | T12 390/1440 đạt; 2 capability/flow chỉ giữ memory/header/body theo contract | B |
| App/provider/access logs | Không raw text/email/token/filename/exception riêng tư | Synthetic canaries: TestClient/provider caplog/ledger và Uvicorn localhost đạt; chỉ lưu aggregates | B |
| TTL CLI | Chỉ resource hết TTL; giữ active và ledger | 4 T12 cleanup tests đạt; missing DB không được tạo, stdout counts only | B |
| .gitignore / frontend key scan | Private/env/build paths ignored; không key trong bundle | 10/10 probes ignored; 1 JS bundle, 0 Gemini key-pattern / GEMINI_API_KEY matches; sentinel protected paths không tracked | B |
| Mobile/desktop/keyboard/axe | 390/1440, không overflow, không lỗi console | T12 ảnh tổng hợp đã xem; axe WCAG A/AA 0 violations ở flow quét; T03 còn 360 px | B |
| 12 ca đa trường | Hai field/case giữ ID, summary, nhãn/time/citations | **12/12 service flows** qua run_pipeline; extraction/retrieval/model scripted, không HTTP live/ranking/model accuracy | B |
| 20 ảnh dev/test / corrected OCR | 20 biến thể theo family/split; CER/fields/time sửa riêng | **CHƯA ĐỦ: 2 dev reference images / 1 family, 0 heldout; corrected human NOT RUN** | B |
| HTTP live T08 đầu cuối | Assets/checks → production pipeline thật với chi phí ghi nhận | **CHƯA CHẠY**: Jobs vẫn FixtureAdapter; live trả CORPUS_UNAVAILABLE | B |

N = `insufficient_evidence`, S = `supported`; ba nhãn hợp đồng giữ nguyên. Nguồn im lặng/nguồn thiếu không thành contradicted, lỗi kỹ thuật không có verdict, expiry là temporal riêng.

## Kiểm tra thực chạy

Môi trường: Linux/WSL hiện tại, Python 3.11.18, Node v22.23.4, Chromium headless local, Tesseract có eng/osd/vie. Không cài dependency mới. SQLite fixture `/tmp`, OCR local; SDK/provider trong tests là mock. Không preflight/live/fresh, không đọc key/.env/gold và không tải URL người gửi.

```bash
.venv/bin/python -m pytest backend/tests/test_failure_paths.py -q --tb=short
.venv/bin/python -m pytest backend/tests eval/tests -q
npm test --prefix frontend
npm run build --prefix frontend
.venv/bin/python -m scripts.export_contracts --check
git diff --check
```

- Backend/eval **300 passed (11.11s)** = baseline 274 + **26 T12**, trong đó 12 tổ hợp hai trường. T12 focused **26 passed (2.48s)**.
- Vitest cuối **37 passed / 7 files** = baseline 20 + **17 T12**, không skip/expected-failure còn lại.
- Build TypeScript/Vite đạt; JS 249.60 kB / gzip 78.06 kB, chỉ là dung lượng, không benchmark latency.
- Export **31 examples validated; OpenAPI matches**. Backend/model/contract/generated types/corpus/prompt/config và tests upstream giữ nguyên.
- Diff whitespace kiểm lại ở checkpoint cuối.

Lệnh browser bên trong wrapper bảo toàn evidence upstream:

```bash
DATABASE_PATH=/tmp/tinchac-t04-smoke.sqlite3 .venv/bin/python -m scripts.init_db
TINCHAC_CHROMIUM_PATH=/tmp/tinchac-chrome/chrome-linux64/chrome \
LD_LIBRARY_PATH=/tmp/tinchac-browser-libs/unpacked/usr/lib/x86_64-linux-gnu \
npm run test:fixture --prefix frontend
TINCHAC_CHROMIUM_PATH=/tmp/tinchac-chrome/chrome-linux64/chrome \
LD_LIBRARY_PATH=/tmp/tinchac-browser-libs/unpacked/usr/lib/x86_64-linux-gnu \
npm run test:browser --prefix frontend
```

Thực thi bằng `python3 /tmp/tinchac-t12-browser.py test:fixture` và `python3 /tmp/tinchac-t12-browser.py test:browser`; wrapper backup/restore toàn bộ `docs/evidence/*` trừ T12 trong finally. Các lệnh npm trên là subprocess thực, không suy kết quả từ handoff cũ. Chromium/libs `/tmp` kế thừa upstream, không đóng gói vào repo.

- Full fixture cuối: **20/20 passed (1.3m)**; không skip/expected-failure.
- Mock UI T03: **4/4 passed (43.9s)** trước sửa client, vẫn hợp lệ cho mock path không dùng HTTP validator. HTTP client cuối được full fixture kiểm lại. Không diễn giải mock live/replay là provider live/replay thật.
- T12 screenshots: `docs/evidence/T12/empty-ocr-confirmed-{390,1440}.png`; chỉ blank image + nội dung giả lập. Không raw network dump hoặc capability trong báo cáo.

Kiểm tra bổ sung đã thực chạy: `git check-ignore --no-index --stdin` với 10 path giả; static Python scan production JS và tracked source bằng pattern `AIza[0-9A-Za-z_-]{35}` (chỉ counts); `tesseract --list-langs`; inline Python OCR/CER và Uvicorn synthetic access-log audit. Mã lệnh audit/reproduction ở `docs/evidence/T12/commands.md`. Không scan `.env` hoặc gold/private contents; scan pattern không bảo đảm mọi dạng bí mật đều được phát hiện.

Lịch sử các lượt chưa đạt, đã ghi thay vì che:

- Baseline 274 backend + 20 Vitest/build đạt. Test TTL đầu 3 failed vì module chưa có; viết CLI rồi đạt.
- Test đa trường đầu 23/24 do clock thật trước `as_of` fixture; patch clock quá rộng tiếp theo fail 12/12; thu hẹp clock chỉ lúc dựng request, 26/26 cuối đạt. Không sửa expectation/fixture/contract để né lỗi.
- B01 trước sửa: Vitest 24 passed + 3 expected fail, browser 19 positive + 1 expected failure. Playwright in “20 passed” do test.fail khớp; đó là tái hiện bug, **không phải gate pass**. Owner cho sửa client, bỏ toàn bộ expected-failure.
- Build test mới có một lượt fail kiểu consent boolean; pin literal true đúng generated type rồi build đạt.
- Full browser sau sửa 19/20: một OCR test mất màn trong khi sửa type client khiến Vite reload; không sửa test gốc, chạy lại full trên mã cố định. Kết quả cuối ở trên.

## OCR tự động và có sửa được tách riêng

`docs/evidence/T12/ocr-existing.json`: dùng hai ảnh T06 có reference, công cụ/phép tạo cũ ở `scripts/ocr_smoke.py`; T12 không tạo thêm biến thể/family hoặc đổi split. NFC + gộp whitespace, giữ dấu/chữ hoa/dấu câu, mỗi reference 56 ký tự.

| Chế độ / ảnh | CER | Tiền chính xác | Ngày / URL | Thời gian sửa người dùng |
|---|---:|---|---|---|
| Tự động / rõ | 0/56 = 0 | Có: 7 triệu | N/A, reference không có | Không áp dụng |
| Tự động / mờ | 56/56 = 1 | Không, OCR rỗng | N/A | Không áp dụng |
| Có xác nhận/sửa, bộ 20 ảnh | Chưa đo | Chưa đo | Chưa đo | Chưa đo |

Browser điền tay/sửa 7→5 triệu kiểm flow, **không** là kết quả corrected OCR hoặc thời gian sửa của sinh viên. Không báo OCR accuracy chung từ 2 ảnh.

## Logs/TTL và giới hạn riêng tư

- Đọc `main.py`, validation handler bỏ input/ctx; Jobs/OCR chuyển unexpected exceptions thành message chung; adapter chỉ log attempt ID/outcome/state. Tests canary xác minh không prompt/text/key/filename/token trong response/log/ledger tương ứng.
- Audit Uvicorn thật ở localhost:8012: POST 202, validation 422, invalid upload 415, DELETE 204; scan raw log tạm có 0 canary/capability, xóa log/DB tạm sau kiểm. Đây là request body/header bình thường; không hứa che được token nếu một client khác cố nhét token vào query rồi access log ghi nguyên URL.
- Raw ảnh xóa sau OCR/lỗi/delete/TTL/restart. Resource TTL mặc định 24h, sweep app 60 giây; tombstone hash thêm một TTL để trả 410 đúng token. Worker writes có điều kiện ngăn phục hồi dữ liệu.
- CLI cleanup chỉ chạy **sau khi owner chọn đúng DB của demo**; không dùng để reset ngân sách, không xóa ledger hoặc active resources. `Settings(_env_file=None)`, nhận cấu hình qua env. Chỉ CLI trên DB fixture test đã chạy, chưa chạy trên DB riêng tư của owner.

```bash
# Ví dụ vận hành sau khi owner chọn DB; CHƯA chạy lệnh này trên dữ liệu owner.
DATABASE_PATH=/path/to/demo.sqlite3 PRIVATE_DIR=/path/to/private \
  .venv/bin/python -m scripts.purge_private
```

DELETE/TTL được kiểm ở mức dữ liệu logic. Chưa kiểm secure erase page/WAL/backup, disk encryption, multi-user host hay public deployment. POST mất phản hồi trước khi nhận capability vẫn cần TTL; client không biết ID để xóa chắc chắn (giới hạn T10 giữ nguyên).

## Blocker và giao owner

| ID | Mức độ / cách kiểm | Owner / yêu cầu |
|---|---|---|
| T12-B01 | **Đã sửa trong phiên**: API completed summary:null trước đây crash; 11 shape cases + browser bắt buộc pass | R2/T10 review phần validation client đã được owner cho phép; không đổi nhãn/schema |
| T12-B02 | **Blocker nghiệm thu live**: health live không có pipeline jobs T08; fixture không phân tích input bất kỳ | R1/T08 hoàn tất HTTP integration và tự xác minh D02/public/cost; sau đó R2 chạy lại 12 ca HTTP đa trường bằng build mới |
| T12-B03 | **Blocker nghiệm thu ảnh**: thiếu 20 ảnh đúng family/split/reference và human correction session | R3/R4/T09 cung cấp tập được duyệt, giữ test/gold ngoài agent; R2 chạy theo manifest, không tự sinh test bù; ghi thời gian sửa và CER/fields hai chế độ |
| T12-L01 | Chưa máy thứ hai, pilot/screen reader/touch, Firefox/WebKit | T15/R2 xác minh trên máy demo; T14 chỉ thử các flow fixture đã qua kiểm và ghi giới hạn |

Gửi R4: chưa quan sát lỗi model thật vì 0 live calls; injection và 12 multi-field chỉ dùng scripted outputs. Không sửa prompt/model/gold/test đã khóa, không tune theo kết quả QA. Experiment version giữ nguyên; build frontend/QA mới có fingerprint riêng. Nếu sau freeze phải sửa thuật toán, owner tạo version/run riêng theo §5.6, không vá số cũ.

## Checklist T15

- [x] Upload hỏng/cap, OCR rỗng/manual, token, delete/restart/TTL đã kiểm offline.
- [x] Ba nhãn/time riêng; source silence/missing/conflict, snapshot lỗi, API failed khác N.
- [x] Canary log/URL/storage và bundle scan; không ghi ảnh riêng tư/key/gold vào evidence.
- [x] B01 client crash đã có fix và regression phải pass; không còn expected-failure che bug.
- [x] Gói evidence có build ID, từng expected/actual và lệnh đã chạy; upstream evidence được restore.
- [ ] Owner review diff T12; chưa tự đánh task done.
- [ ] B02 HTTP live + D02 do R1, kiểm 12 ca đa trường thật và mọi S/C có quote/scope/thời điểm đúng.
- [ ] B03 20 ảnh/split + automatic/corrected/time sửa; không dùng 2 ảnh dev thay benchmark.
- [ ] T15 dựng lại trên máy demo theo README, diễn tập fixture/replay có nhãn, không nói đã gọi live.

Chi phí tài khoản: **0 provider calls, 0 tokens thực, 0 USD / 0 VND**. Mock accounting trong tests không là chi phí thật. Tổng ngân sách 200.000 VND không bị sử dụng trong phiên.
