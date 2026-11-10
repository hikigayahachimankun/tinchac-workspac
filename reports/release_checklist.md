# T15 — Internal fixture RC, chưa đủ điều kiện release chính thức

Ngày 10/11/2026, R1 agent tự nghiệm thu kỹ thuật; R2 là trách nhiệm hỗ trợ trong kế hoạch solo, không giả reviewer độc lập. Nhánh `task/T15-release-candidate`, nền `64b726e`. Tag chỉ mang hậu tố `-rc.1`; không đánh T15 done. [Handoff](../docs/handoffs/T15.md), [lệnh/evidence](../docs/evidence/T15/README.md), [video](../artifacts/T15/tinchac-demo-rc.mp4).

| Gate | Thực tế | Trạng thái |
|---|---|---|
| Locks/build/model/config/corpus | Python3.11.18, Node22.23.4, exact Python/npm locks. Manifest SHA256 từng file/locks/config, seed42, model/corpus fixture-v1; live model gemini-3.5-flash-lite tắt mặc định; corpus thật chỉ pin manifest tham chiếu | Đạt cho RC |
| Same-origin, one worker | FastAPI serve dist; API/private/traversal/symlink/missing assets404; regression extensionless assets trước đây fallback HTML | Đạt |
| README môi trường sạch | Extract archive, venv mới, npm ci/build mới, SQLite/FTS5, Tesseract vie+eng, một worker; health/4 case/quote/source/DELETE đạt | WSL đạt, CI độc lập đạt (receipt bên dưới) |
| UI/browser | Chromium390/1440: 4 tình huống, OCR thật/sửa chữ/consent, keyboard evidence, snapshot; 0 overflow/JSerror/external request/storage | Đạt fixture |
| Offline/quota/cap | Chặn POST + chèn429 trong browser; backend HTTP dùng GeminiAdapter/ledger thật và SDKmock429/cap0: không verdict/retry/paid fallback/real call | Đạt injection, không ngắt mạng vật lý |
| Fixture/replay | CLI27/27 fixture +27/27 replay có mode/origin, 0 provider calls | Đạt offline, không benchmark |
| Regression | Backend/eval397 passed, Vitest37 passed, build,31 examples/OpenAPI matches, corpus6 sources/7 chunks valid | Đạt |
| Video3–4 phút | Browser capture thật, caption/watermark fixture, giọng Việt tổng hợp local; metadata/frame/privacy audit trong evidence | Tài sản RC, không human pilot |
| Source links | Snapshot/quote spans qua HTTP; HEAD3 URL DUT approved đều200 | Availability, không xác nhận nội dung/quyền |
| Cold-start **môi trường thứ hai độc lập** | GitHub-hosted standard Ubuntu24.04/Azure run42827045087 thực build/install/4 HTTP ca/source/delete/OCR thành công; [receipt](../docs/evidence/T15/independent-ci.json) | **Đạt VM độc lập**; laptop demo vật lý chưa thử |
| Ca DUT thật được hỗ trợ đạt QA | Free Tier preflight trước T15 đã đạt; HTTP upstream run2 chỉ2/12 completed đều NEI rồi503 unknown. Video S là fixture | **BLOCKER T12/T15** |
| Phân phối ngoài nhóm | Không bundle snapshot thật/private/gold/key/ledger/vendor binary; quyền nguồn/dependency gồm PyMuPDF chưa chốt | **BLOCKER external release** |
| Nghiên cứu/con người | Thiếu human gold/holdout/freeze/evidence scoring, human OCR correction; pilot n=0 | **T13/T14/T16/T17**, không suy diễn từ demo |

Không public hosting/deploy, merge main, paid request, top-up hoặc nộp hồ sơ. Trần vẫn 200.000 VND; phiên T15: **0 provider calls,0 tokens,0 USD/0 VND**. Ledger lịch sử có21 response +2 unknown503 tại checkpoint T05; known Free Tier estimate0 USD nhưng actual total chưa biết. Không reset ledger/đổi unknown thành0.

API/schema1.0, ba label, model và benchmark protocol giữ nguyên. Gói nội bộ cài dependencies từ lock ngoài gói; không coi việc không bundle binary là đã giải quyết giấy phép.

T16 nhận video/script/manifest/checklist, chỉ trình bày kết quả thực. T17 nhận gate list, không dùng tagRC làm chứng nhận nghiệm thu. Bước tiếp theo duy nhất: đóng QA cho một ca DUT thật được hỗ trợ theo upstream T12, giữ laptop demo vật lý/rights mở trước stable tag.
