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

## D12 — T06 local OCR và tích hợp tối thiểu (2026-11-09)

- Một process demo, tối đa 2 OCR đồng thời; multipart body cap 5 MiB + 64 KiB cho envelope, file cap cứng 5 MiB và decode tối đa 12M pixel (config chỉ có thể hạ). Chỉ nhận MIME PNG/JPEG khớp định dạng decode; không dựa vào filename. File raw owner-only ở private_dir/uploads, UUID server tạo, xóa sau OCR/timeout/lỗi/DELETE/TTL và khi restart.
- Thêm đúng endpoints assets §3.7, export bằng FastAPI/Pydantic; 40 schema components gốc và các path T04 không đổi. API v1, models/schema 1.0/examples/enum giữ nguyên. Types regenerate từ OpenAPI.
- Schema 1.0 không có trường public text_modified. Lưu cột nội bộ checks.text_modified, backend so chính confirmed_text với OCR text; NULL cho text, xóa khi TTL/DELETE. Request job chỉ giữ marker asset_token sau authorization, không giữ capability gốc. Jobs tiếp tục adapter fixture T04, không sửa verify.py hoặc nối provider/retrieval.
- CheckCreate image chỉ cho ready. OCR ready/rỗng: nhập tay và gửi image kèm asset. OCR failed/gián đoạn/upload lỗi: giữ thông báo và nhập tay bằng CheckCreate text, asset fields null. Không đổi contract để cho failed asset thành ready.
- Preview blob local, capability chỉ trong memory/header; rời màn ảnh hoặc thay ảnh gọi DELETE, TTL xử lý khi đóng trang/mất mạng. CER chỉ báo trên 2 biến thể tổng hợp / 1 family dev, không thay thế 20 ảnh đánh giá §4.6.

## D13 — Lựa chọn cục bộ T07 (2026-11-09)

- Ingest chỉ đọc local raw hoặc normalized snapshot T02, không tải web. SourceVersion 1.0 không đổi; raw/manual receipt và page mapping nằm trong config/manifest. PDF giữ bản trích có chủ đích theo T02, không tự sửa thành OCR.
- Index FTS5 và char TF-IDF dựng trong memory từ eligible chunks cho mỗi query chưa cache: đảm bảo thống kê và top-10 không nhìn nguồn tương lai/quarantine. Shortcut giới hạn solo demo/corpus nhỏ, chưa tối ưu cho nhiều worker/corpus lớn.
- Giữ FTS10 + char_wb(3,5)10 + RRF60, top5; tie chunk_id, chỉ cosine >0. Cache public opt-in trong memory 64 entries/24h; private không cache. Identity có corpus/config/as_of/full claim/k và sentinel model/prompt/schema cho retrieval không LLM.
- Corpus version hash cả metadata nguồn, chunks, provenance, config và code/dependency fingerprints. build_at là logical timestamp max(retrieved_at) để manifest tái lập; ingest commit ghi HEAD nền, code chưa commit được nhận diện bằng hash.
- 10 probe seed là pilot kỹ thuật của 5 family approved, không tạo verdict/gold và không thay split T09. Giữ D03 thiếu 1 nguồn phí approved; chưa có bản gốc mức thu 4055 nên không tạo quan hệ supersedes cho bản gia hạn.

## D14 — Lựa chọn cục bộ T08 (2026-11-10)

- T04/T05 có trong commit tích hợp 1c8e8ce; T07 chỉ trong working tree chưa commit. Thực hiện phần services/CLI độc lập theo ngoại lệ T08, giữ HTTP Jobs fixture và toàn bộ diff T06/T07. Không coi upstream đã done hoặc tự commit để vượt dependency.
- Chuẩn hóa tiền bằng integer/Decimal, giữ năm/loại phí/đơn vị mơ hồ; scope nullable không là wildcard. S/C dựa trên citation chính xác và fact đã duyệt cùng scope, kiểm từng relation; văn bản chưa so được giữ N. Không thêm nhãn hoặc sửa hợp đồng 1.0.
- Context dùng tham chiếu chung cho scope/hit metadata và bỏ raw_value đã có nguyên văn trong statement để ca 4 trường nằm trong trần T05; không bỏ claim hoặc đổi offset.
- C dùng đúng bundle T07/top5; giới hạn 6 chunk toàn ca có warning. Context model là excerpt tối đa 220 code points quanh fact cùng scope, offset gốc, không gửi phần khác; guard giữ bundle đã chọn đầy đủ để kiểm conflict. Vượt trần bảo thủ T05 thì lỗi kỹ thuật tường minh. T11 phải giữ bundle cố định chung khi so B/C/C_NO_TIME.
- Một invocation verification, một retry tổng tối đa theo T05; guard audit chỉ nhãn/index/tên trường đổi/reason/count, không raw text hoặc claim_id. Summary/explanation/next_steps dùng template; không LLM rewrite, không chứng nhận người gửi/STK.
- Sáu ca public là target dev chuẩn bị sẵn theo §5.2, kiểm offline qua adapter mock và ledger, không extraction/live tuning. D02/live blocked; giá/model ứng viên chưa xác minh; D03 thiếu nguồn phí và bản gốc mức thu vẫn mở. Candidate hashes/kiểm tra ở docs/evidence/T08, handoff chính thức docs/handoffs/T08.md.

## D16 — T10 UI trên handoff chưa commit (2026-11-10)

- Owner cho phép sửa tiếp upstream chưa commit trong phiên T10, giữ hành vi T06 và không commit. Nhánh `task/T10-evidence-ui`, nền `1c8e8ce`. Chỉ sửa các component/client/App thuộc T10; không đổi types/OpenAPI/models hoặc test upstream.
- Đọc chế độ từ health hiện có trước khi gửi, sau hoàn tất dùng `CheckResult.run_mode`; không suy live từ provider_configured, không fallback fixture khi lỗi. Backend HTTP hiện vẫn fixture theo T08/D02; live/replay UI kiểm bằng phản hồi mô phỏng, chưa nghiệm thu provider.
- Giữ nguyên `next_steps` backend như text. Chỉ canonical URL http(s) không credentials từ SourcePublic của endpoint nguồn approved mới thành link; định danh fixture là text. Không tự linkify statement, warning, next_steps hoặc snapshot, không tải URL nội dung nhập.
- GET lỗi/120s chỉ đọc lại cùng check/token; người dùng chủ động POST mới mới tạo job, có nhắc phí lần trước và lần mới. DELETE hủy theo dõi không bảo đảm hoàn phí; POST đến muộn được xóa khi nhận capability. Không có capability do mất phản hồi POST thì UI không thể xác nhận xóa; TTL backend xử lý phần còn lại.
- `sources` được hiển thị là nguồn kèm kết quả, không suy đây là toàn bộ kho hoặc số nguồn đã tìm (T08 chỉ trả nguồn trích dẫn, fixture T04 có thể kèm cả source không có citation); all-N rỗng vẫn nêu corpus/version/thời điểm và giới hạn. Không cần trường schema mới.

## D17 — T11 harness offline và đề xuất tích hợp cho owner (2026-11-10)

- Nhánh `task/T11-eval-harness`, nền `1c8e8ce`; giữ toàn bộ diff upstream T06–T10 và T09. Không commit/push/merge/deploy. Chỉ thêm modules eval/scripts/config/prompts/report; docs quản trị task cập nhật theo AGENTS.md.
- T01/T05 có trong lịch sử tích hợp; D02 vẫn mở. Chỉ chạy fixture/replay/SDK mock. Full nghiệm thu live dev còn **blocked R1/D02**; không suy model/giá đã được xác minh từ tên ứng viên trong Settings.
- EvalCase §4.4 chưa có scope/raw_value/normalized mà T08 Claim cần. **Đề xuất R1/T09 trước freeze:** duyệt sidecar `{case_id,claim}` được chuẩn bị từ chính input công khai, không gold hoặc scope suy từ nguồn retrieval, rồi cấp giống nhau cho A/B/C. CLI có `--claims` và kiểm đúng target id/statement/field; thiếu sidecar thì từ chối fresh. Đây là adapter input cục bộ chờ owner duyệt, không đổi EvalCase/API/schema 1.0 và không tự bổ sung gold/test. Nếu owner không duyệt, R1 cung cấp hàm prepare Claim đúng hợp đồng trước T13.
- **Đề xuất R1 về accounting:** Usage 1.0 không có unknown. Giữ EvalRunRow nguyên trường Usage với known subtotal; envelope ghi `accounting.known_subtotal_only`, từng reservation/attempt/usage/model version. Scorer trả tổng phí N/A nếu có unknown hoặc missing rows; charged reservation không được gọi là phí thực. Không sửa model chung để né blocker.
- EvalRunRow/EvidenceScore đặt ở `eval/run_schema.py`, không đăng ký OpenAPI. JSONL mỗi dòng là envelope có `row: EvalRunRow`, bundle/hash/accounting/mode; manifest ghi config/prompt/code/input/commit hashes. `run_id=batch_id:system` giải quyết khóa EvidenceScore(run_id,case_id), T13 phải ẩn system/run_id khi phát phiếu chấm mù. Không tự tạo reviewer thật từ fixture scores.
- B/C/C_NO_TIME nhận cùng snapshot top5 cutoff/approved. Context chung bỏ full notice trùng chunk, metadata provenance không phục vụ suy luận và các giá trị raw ngày đã có trong quote; intern scope lossless. Giữ title/date/scope/facts/URL và toàn bộ chunk được chọn; không thay nguồn theo gold. Hash bundle đầy đủ vẫn trong artifact. C dùng production normalize/check_claim/validate_verdicts; B không gọi guard C. Context thực vượt trần T05 thì ghi INPUT_TOO_LARGE, không cắt nguồn riêng cho C.
- C_NO_TIME là adapter eval riêng: không gọi check_claim, không so sánh giá trị ngày/deadline/current_availability, không dùng effective/supersession clocks trong guard. Giữ static quote/ID/scope/field guards/templates; model vẫn thấy ngày và có thể tự suy luận như B. View bỏ temporal metadata chỉ dùng trong guard; bundle model/hash không đổi. Không sửa shared evidence/temporal/verify. Owner review logic ablation trước freeze.
- Fresh dùng stage dev (.8 USD) hoặc evaluation (1.4 USD) từ T05, global cap <=3 USD. T05 `max_calls` chỉ cho preflight1..3 nên harness không truyền480: giới hạn bằng schedule <=12 dev/72 test, ablation<=24, một invocation/row, retry<=1. Dừng khi budget hoặc >10% **case** có technical error (bảo thủ hơn chỉ provider), giữ run lỗi và missing rows trong mẫu số; rerun mới không nối vào run cũ.
- Không điền điểm mẫu vào reports/evaluation.md. Ví dụ 8 ca giả và phép tính tay ở eval/tests/README.md; bootstrap2000 seed42 paired family, chính C−B; ablation chỉ paired trên subset chọn trước. Field extraction/OCR thuộc bộ end-to-end riêng, không giả kết quả từ benchmark target.

## D18 — T12 QA offline, blocker và đề xuất owner (2026-11-10)

- Nhánh `task/T12-failure-privacy`, nền `1c8e8ce`; giữ upstream T06–T11 đang dở, không commit/push/live. Tests T12 mới và cleanup TTL độc lập, không thay contract/schema/model/prompts/splits/gold.
- **T12-B01, owner R2/T10:** client chấp nhận completed thiếu summary/warnings hoặc ngày không parse được; browser tái hiện summary null làm ResultTable crash. Đề xuất validate đủ các trường UI dùng trong `frontend/src/api/client.ts`, trả ApiError kỹ thuật trước render; owner cân nhắc boundary dự phòng. Đã ghi đề xuất trước; chủ repo trả lời **cho phép sửa tiếp frontend để đóng blocker** trong phiên T12. Agent bổ sung kiểm payload đúng các trường UI dùng (metadata/date, shape/text, summary/labels/citations/source joins) và mã lỗi own-property; không suy/sửa verdict. Các test expected-failure ban đầu chuyển thành regression bắt buộc pass. Không cần ErrorBoundary cho ca đã tái hiện vì payload bị chặn trước React state; chưa tuyên bố bao phủ mọi lỗi React.
- **T12-B02, owner R1/T08/D02:** Jobs vẫn FixtureAdapter, live HTTP trả CORPUS_UNAVAILABLE; không tự nối provider hay bật key để bù QA. 12 tổ hợp hai trường chạy qua run_pipeline thật với model/extraction/retrieval scripted chỉ là kiểm service offline, không là HTTP live hoặc chất lượng model.
- **T12-B03, owner R3/R4/T09:** chỉ 2 ảnh OCR tổng hợp có reference / 1 family dev, chưa có 20 ảnh split dev/test theo §4.6. Không tạo dataset/test mới, không sửa expected labels. OCR có người sửa và thời gian sửa chưa có; script kiểm UI điền fixture là kiểm flow, không đo hiệu quả người dùng.
- `python -m scripts.purge_private` chỉ dùng env (không nạp .env), mở DB có sẵn mode=rw và gọi purge TTL của assets/jobs. Không initialize/restart, không xóa DB/ledger/active raw, không quét orphan đang dùng; app restart sở hữu orphan cleanup. DELETE/TTL là xóa logic trong SQLite, không cam kết secure erase page/WAL/backup.
- Experiment version không đổi vì không đổi inference/corpus/config. Build QA có fingerprint riêng trong docs/evidence/T12; nếu owner sửa pipeline sau freeze phải tạo version/run mới theo protocol, không chấm lại chọn lọc.

## D19 — Autonomous recovery authority (2026-11-10)

The user delegates repository maintenance, architecture, technical acceptance, commit and push to the maintainer. This supersedes earlier per-task instructions to wait for owner diff review, avoid commits, or stop after one task. Work proceeds sequentially on `recovery/t00-t17-audit`, based on `4fdbc5b`; existing branches/history are retained. Technical self-review is not an independent human annotation or usability review. Main remains unchanged while live/data acceptance gates are unresolved. No production deployment, billing changes or submissions are authorized.

D01: solo owner remains responsible for real account access and human participation; agent owns technical decisions and Git. D04: this WSL environment has Python/Node and local vie+eng OCR; a physical demo laptop and second-machine cold start are still unverified. D06: localhost only. Paid calls require explicit account/preflight budget authorization; key presence alone is insufficient.

## D17 — Approved for recovery implementation (2026-11-10)

The proposed public-input Claim sidecar and known-subtotal accounting envelope are approved under D19. Scope and raw value must be traceable to the supplied target/input; no inference from gold, source facts or retrieval. Human confirmation of target atomicity/scope remains a freeze gate. Inference never imports gold. Unknown attempts retain reservations; reports expose known subtotal and mark actual total unavailable. Sidecar hashes, pinned temporal subset and all accounting must travel with run provenance. Approval resolves the design decision, not D02, human gold, holdout availability or freeze.

## D20 — Connect the production HTTP pipeline (2026-11-10)

Reuse T05/T07/T08 for live HTTP with per-job adapters and one durable ledger; charge stage `demo` (0.8 USD), global <=3 USD. HTTP uses `public=False` and no persistent provider cache. `LLM_LIVE_ENABLED=false` is the default; only enable after account/model/pricing/quota checks and paid-use authorization. Load and validate one immutable approved non-fixture corpus per process, expose its exact snapshots and corpus version, restart to adopt changes. Keep replay HTTP unavailable until a recorded run is configured; CLI replay remains supported. Check deletion/TTL between extraction/retrieval/verification, retain in-flight attempt charges and prevent late worker writes.

## D21 — Gemini reasoning configuration corrected before live (2026-11-10)

Primary Google documentation rechecked: https://ai.google.dev/gemini-api/docs/thinking and https://ai.google.dev/gemini-api/docs/pricing (direct HTTPS returned 200, redirected to aistudio.google.com/docs). Gemini 3.5 Flash-Lite supports `thinking_level=minimal`; minimal may still produce billable thoughts. Use the SDK ThinkingLevel.MINIMAL for Gemini 3 family and omit candidate_count (default single candidate; response still checked). Retain budget=0 for older configured models, subject to their preflight support. Actual output accounting still includes thoughts, verifies total tokens and output cap, and retains unknown reservations. Published Standard prices currently match the existing 0.30/2.50 USD per million defaults, including thinking output; this does not verify the user's account, taxes, quota or billing. D02 remains open. All A/B/C use the same adapter; prior offline artifacts are historical, new experiments must pin new hashes. No paid call was made.
