# Quyết định của nhóm

| ID | Owner | Trạng thái khởi tạo | Việc cần chốt | Mặc định để tiếp tục |
|---|---|---|---|---|
| D01 | Chủ repo | Đã chốt solo | Chủ repo giữ R1–R4 và review cuối | Xem quyết định D01 bên dưới |
| D02 | R1 | Mở | Project Gemini, model khả dụng, quota và chi phí hiển thị | Fixture offline |
| D03 | Chủ repo solo / agent T02 | Mở — thiếu 1 nguồn phí seed | T02 có 4 học bổng + 1 phí approved; 1 phí quarantined do danh sách cá nhân | Giữ quarantine; tìm thông báo mức thu chung không có dữ liệu cá nhân; theo ngưỡng §4.2 |
| D04 | R2 | Mở | Máy demo và OCR tiếng Việt | WSL2, CPU, ưu tiên luồng text |
| D05 | R3 | Mở | Người thử tự nguyện và quy trình đồng ý | Chưa đưa dữ liệu thật vào repo |
| D06 | R1 | Mở | Có công khai website sau demo hay không | Demo localhost |

## D01 — Triển khai solo (2026-11-09)

Chủ repo xác nhận tự triển khai TinChắc: chủ repo giữ vai trò R1–R4, quyền chốt hợp đồng và review cuối. Agent làm tuần tự từng task, đưa sang review; chủ repo quyết định commit/done. T00 được xác nhận phần repo/nhánh/phân công để mở T01; máy demo, nguồn, gold và live vẫn chưa kiểm, không coi T00 đã hoàn tất toàn bộ.

## D07 — Lựa chọn cục bộ T01 (2026-11-09)

- uv compile khóa dependency trên Python 3.11; không scaffold frontend.
- T01 chỉ có health route thật. Tất cả schema mục 3 nằm trong OpenAPI components sinh từ Pydantic; route nghiệp vụ sẽ được nối trong task sở hữu, không tạo endpoint giả.
- SQLite chỉ khởi tạo bảng metadata phiên bản DB ở T01, chưa thiết kế bảng jobs/assets/checks cho các task sau. Health mở DB có sẵn, thử FTS5 bằng bảng TEMP, không khởi tạo DB.
- Validator model kiểm cấu trúc; quote đối chiếu text NFC khi được truyền context chunks. Kiểm asset ready/token, nguồn available/scope và entailment cần dữ liệu runtime, thuộc T04/T06/T08. Không giả ghi checks_passed cho các kiểm tra chưa thực hiện.

## D03 — Checkpoint T02 (2026-11-09)

- 6 ứng viên / 6 family, 5 approved trong phạm vi đã đọc (4 học bổng, 1 gia hạn phí), 1 quarantined. Chưa đạt mục tiêu **2 nguồn phí approved**; chưa có căn cứ về ngưỡng 24–36 family của §4.2.
- DUT id12381: trang hành chính đọc được nhưng số tiền nằm trong danh sách cá nhân đính kèm. Không thu/giữ danh sách để bù số lượng: PDF tổng và ảnh các trang danh sách đã xóa khi phát hiện, không đọc/OCR các trang đó. Corpus chỉ giữ tiêu đề, facts rỗng, audience/cohort null.
- DUT id12387 đọc đủ 2 trang: đủ căn cứ cho hạn/ngân hàng và quy tắc phần trăm học phí, không phải số tiền VND cá nhân. Thông báo mức thu 4055/TB-ĐHBK được dẫn nhưng chưa mở/thu; không suy đơn giá từ thông báo gia hạn.
- Chủ repo cần kiểm tay cả 2 nguồn phí và ít nhất 2 học bổng theo `docs/source_log.md`; tìm nguồn mức thu chung không chứa danh sách cá nhân cho phần phí thiếu. Không tự hạ quarantine hoặc lấy dữ liệu cá nhân để đủ chỉ tiêu.
- Quyền: nguồn công khai để đọc, chưa xác nhận giấy phép tái phân phối; seed phục vụ nội bộ/chờ review, chưa chấp thuận xuất bản corpus/raw. Chi tiết hash, thời điểm, URL, phần thiếu tại `docs/source_log.md`.

## D08 — Lựa chọn cục bộ T02 (2026-11-09)

- Config sổ nguồn dùng JSON là tập con YAML 1.2 để không thêm dependency. Không có crawler/parser mạng tái sử dụng trong T02.
- SourceVersion PDF Toyota và phí đợt 2 có canonical_url là file Drive, parent_url là trang DUT; metadata attachment/quyền/raw hash ở source_log/config, không mở rộng hợp đồng T01.
- Các snapshot thật dùng first_seen để không gán ngược nội dung hiện tại về ngày công bố khi chưa có lịch sử sửa. PDF dùng bản trích nghiệp vụ đã đọc ảnh, không dùng OCR chưa kiểm để tạo fact.

## D09 — T03 fixture UI và upstream chưa commit (2026-11-09)

- Nhánh `task/T03-fixture-ui` lúc bắt đầu chỉ có HEAD `5f65546` baseline; `git ls-tree -r --name-only HEAD contracts backend` rỗng. Hợp đồng T01 chỉ có trong cây làm việc untracked, không xác nhận đã có trong lịch sử commit. Không tự commit T01/T02 để vượt điều kiện này.
- Theo ngoại lệ phần độc lập của T03, dựng UI fixture dựa trên OpenAPI/examples hiện có và giữ blocker upstream khi review. Chưa ghép backend thật.
- Types sinh bằng openapi-typescript; ba nhãn, trạng thái và mã lỗi dùng enum T01. Các tình huống UI mở rộng từ example được gắn mô phỏng và validate bằng Pydantic, không phải source/gold mới. Bản T01 original nhập trực tiếp từ examples.
- Chọn bố cục phiếu học vụ theo DESIGN.md: form một trục; bảng desktop chuyển thành hàng dọc mobile; bằng chứng mở inline bằng details/summary để giữ vị trí và bàn phím. Không sửa PRODUCT.md/DESIGN.md.
- Không phân tích nội dung nhập: mock trả tình huống cố định và giải thích ngay trong banner/phần chọn mẫu; không HTTP, storage, upload, OCR hoặc Gemini. `ApiClient` là ranh giới bàn giao T04; token chỉ trong memory.

## D10 — Ngoại lệ upstream và lựa chọn T04 (2026-11-09)

- Nhánh T04 chỉ có baseline `5f65546`; chủ repo trả lời “Cho phép dùng upstream chưa commit”, cho phép ghép T01/T03 working tree và vẫn cấm commit/push. Không diễn giải là upstream đã được commit hoặc owner đã xác nhận done.
- Model/schema 1.0/examples/enum giữ nguyên. Route checks/sources theo §3.7 được sinh vào OpenAPI bằng FastAPI, không sửa tay; kiểm components cũ bằng nhau.
- Adapter chỉ nhận 5 mẫu định danh từ data/fixtures/cases.jsonl; mẫu expired chỉ kiểm presentation trong mock T03, expiry tài nguyên kiểm riêng; unknown text → NO_CHECKABLE_CLAIM, lỗi worker → failed/ErrorDetail, không NEI giả. Historical trước source available_at là completed/NEI. Dùng snapshot/ID T02 fixture, không ghép citation ID example T01 với snapshot khác.
- Client mặc định HTTP qua Vite proxy. VITE_API_MODE=mock chỉ bật mock T03 tường minh cho regression; lỗi HTTP không chọn mock. Backend fixture không phục vụ thay live/replay.
- Một process demo, BackgroundTasks + SQLite WAL; tối đa 2 worker; 24h TTL, dọn mỗi 60 giây hoặc lúc thao tác. Tombstone chỉ hash/ID/thời gian, tồn tại thêm 24h để trả 410 với đúng token; DELETE xóa token/text/result và worker dùng conditional update để không khôi phục.

## D11 — T05 adapter/budget và giới hạn nghiệm thu (2026-11-09)

- Đúng nhánh `task/T05-llm-budget`, HEAD vẫn `5f65546`; không có commit T04 trong lịch sử. T01/T04 có trong working tree. Theo phần độc lập của T05, chỉ xây adapter/extract/preflight; không tự commit upstream và không tuyên bố dependency đã done.
- Chủ repo yêu cầu dừng sau mock/review và tự chạy preflight. **D02 chưa xác minh**; giữ model/giá ứng viên theo Settings, không tự đổi model hoặc xác nhận giá/quota tài khoản.
- Không sửa config, models, job flow, API hoặc OpenAPI. Jobs tiếp tục fixture-only; T07/T08 sở hữu ghép retrieval/verification live. `extract_claims(request, *, llm, corpus_version, stage='dev', public=False)` trả ExtractionResult hoặc ServiceError chứa ErrorDetail.
- Retry tổng tối đa 1 cho mỗi invocation (transport hoặc sửa schema); SDK attempts=1, timeout mặc định 30s. Schema provider bỏ metadata/constraint không cần thiết, đổi const thành enum; server validate toàn bộ bằng model gốc, kiểm span trên text chưa che/đổi NFC. Che email/SĐT/STK, span null khi text đổi; không cache dữ liệu riêng tư.
- Ledger dùng integer nano-USD/Decimal, BEGIN IMMEDIATE trên connection riêng; không giữ lock qua provider I/O. Trần tổng là min(config, 3 USD), dev .8/evaluation 1.4/demo .8; retry tính vào stage của caller. Ước lượng đầu vào bảo thủ theo UTF-8 bytes + overhead, context <=6000 và output <=2400 kể cả thinking; yêu cầu thinking_budget=0 phải được preflight xác minh.
- Mỗi attempt có reservation riêng. Timeout, cancellation, lỗi transport/HTTP không có usage, hoặc usage thiếu/không khớp giữ nguyên khoản giữ chỗ, actual/tokens NULL; không tự release. Retry thành công sau attempt chưa rõ phí vẫn trả lỗi kỹ thuật vì Usage 1.0 không có kiểu unknown; ledger giữ riêng attempt đã biết/chưa biết. Không giả 0 để vừa schema. Đối soát dashboard do chủ repo thực hiện.
- Cache chỉ public được caller xác nhận, trong memory, tối đa 64 entries, TTL theo cấu hình; không có cache bền vững hoặc cache riêng tư. Key đủ model/prompt_hash/schema_version/input_hash/corpus_version/as_of và thêm hash schema/config. Hit có attempts/tokens/cost mới bằng 0, cache_hit=true; không giả latency live.
- Preflight không list model/count_tokens hoặc gọi URL; dùng 3 trích đoạn seed T02 public approved. Một run_id, trần <=3 attempt trong cùng ledger transaction, gồm cả retry/repair. Không cache preflight; không tải .env trong CLI, key lấy từ môi trường riêng của chủ repo.
