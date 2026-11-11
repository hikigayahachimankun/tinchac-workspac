# Verified DUT Source Discovery & Auto-Sync — vận hành đã kiểm chứng

**11/11/2026, môi trường local WSL.** Pipeline thật đã tự phát hiện, duyệt bằng agent theo gate hợp lệ, publish và sử dụng một nguồn DUT mới trong check Gemini/HTTP. Đây là nghiệm thu phạm vi vận hành đã thử; không phải benchmark, human source review độc lập hay bảo đảm độ chính xác tuyệt đối. Trạng thái task theo quy ước repo: review.

Bằng chứng chính: [operation.json](../docs/evidence/source-sync/operation.json), [retrieval](../docs/evidence/source-sync/retrieval-live.json), [rollback/restart](../docs/evidence/source-sync/rollback-restart.json), [từng ứng viên cũ](../docs/evidence/source-sync/candidate-dispositions.json), [metadata attachment](../docs/evidence/source-sync/attachment-metadata.json). Receipt `smoke.json` và báo cáo trong commit5c57b0e là checkpoint lịch sử18URL/8quarantine/0newapproved, không phải trạng thái cuối hiện tại.

## Nguồn mới và corpus thực tế

Nguồn mới: [AIDA Engineering Okayama Japan Scholarship, DUT CTSV12218](https://dut.udn.vn/Phong/CTSV/Thongbao/id/12218), phát hiện qua danh mục CTSV được registry cho phép, không đoán ID hoặc theo URL người dùng. HTML hoàn chỉnh; chỉ có Google Forms đăng ký, không mở form; không thấy PII/danh sách cá nhân hoặc attachment nghiệp vụ trong phần đã đọc. Chương trình có các nhóm đối tượng và số tiền Yên; bộ duyệt hẹp chỉ tạo fact **tên chương trình và hạn nộp ban đầu**, không suy tiền VND hoặc điều kiện từng nhóm.

| Mục | Trước | Sau |
|---|---|---|
| Corpus vận hành | `corpus-6b5cb0eb9e0b4f5029857ffe83259f77290af8585d05aa50216fee0d122142e5` | `corpus-b64622385341477a6afb164f2a171dd3942e1d3372e27f318210668665db5e11` |
| Versions / approved / chunks | 6 / 5 / 7 | 7 / 6 / 8 |
| Source mới | — | `dut_39c806ec6715272c_0294c3ba0dc48e23` |
| Hash text mới | — | `0294c3ba0dc48e237abcd5ff35fdfb4a6b91c3f5f8d1f0dedfe81ab4f9d8f5c5` |

Corpus benchmark giữ nguyên `corpus-7b832d58775878a57849d32ff241cc61904afadfc0299a66e3918ad82da18982`. Không sửa corpus/reference register, split/protocol, gold, A/B/C/C_NO_TIME, model, prompt, retrieval hoặc ngân sách. Snapshot vận hành được dựng bằng ingest cũ; packet/registry hash gắn manifest, giữ mọi record cũ.

Gate content-use được mở bằng **xác nhận thật của chủ dự án trong chat về quyền/căn cứ sử dụng nội bộ**. Policy private ghi đúng đây là owner attestation, không phải giấy phép DUT được kiểm độc lập hoặc quyền tái phân phối. Reviewer của nguồn là `TinChac machine review v1 (agent)`, không gán human. Gate financial/scan/amendment không bị bỏ qua. Hạn15/9/2026 là lịch sử; không tuyên bố học bổng đang mở.

## Tám ứng viên ban đầu

| Notice | Kết luận có bằng chứng |
|---|---|
| CTSV12395 Agribank | Trùng notice/text/version seed đã giữ; không đếm nguồn mới. Mẫu trống đã được T02 đọc; không tải hồ sơ đã điền. |
| CTSV12394 Keidanren & JCCI | Cùng notice/programme/năm seed; HTML có emoji và poster nghiệp vụ. Không đếm alias/reformat là nguồn mới; poster chưa được dùng để suy fact. |
| CTSV12373 quyết định cấp học bổng | Metadata PDF cho thấy quyết định cấp với MSSV đã che,16.9MB. Không tải/OCR danh sách; che MSSV chưa chứng minh không còn tên. Loại khỏi auto-approval. |
| KHTC12387 gia hạn | Parent/file ID chính là6075 đã nằm trong seed, cùng family học phí. Không khẳng định cùng Drive ID chứng minh bytes chưa đổi. Không nhân đôi evidence. |
| KHTC12381 thạc sĩ | T02 đã xác định phụ lục cá nhân; không mở lại. Giữ quarantine, không retrieval. |
| KHTC12340 thu phí gốc | Đã đọc đủ2trang scan5631, OCR local có thống kê chất lượng. Hạn30/10 khác bản gia hạn6075/30/11; cùng tham chiếu4055, cùng family. Chờ human financial/scan review; không suy mức thu từ4055 chưa đọc. |
| KHTC12337 cập nhật nhập học | Đã đọc đủ2trang scan5574, xác định scopeK2026 và nhiều fee-kind, tham chiếu4179/3066/4055. Chờ human financial/scan review, không auto-publish tiền. |
| KHTC12319 tiến sĩ | Metadata xác nhận PDF5450/năm2026–2027; privacy/completeness phụ lục chưa được xác lập. Không tìm lấy danh sách cá nhân; chưa đủ điều kiện tài chính để auto-approve. Đã dùng nguồn HTML khác hợp lệ cho luồng hoàn chỉnh. |

Không giả rằng mọi candidate đều được duyệt hoặc đã có human review. Hai PDF được đọc là tài liệu hành chính scan, native text rỗng, không có danh sách cá nhân trong các trang đã xem. Mean OCR confidence từng trang93.02–95.28%, vẫn có từ confidence thấp; đó không phải chứng minh số tiền/ngày chính xác. Raw/PDF/render/OCR nằm private và không được gửi Gemini hay Git. Các PDF/list không đủ privacy gate không được tải để ép tăng số approved.

## On-demand và scheduler thật

Hai chu kỳ DUT định kỳ ở lịch thử60giây có receipt thật; sau đó phục hồi3600giây/poll10giây, hiện chạy bằng user-owned detached CLI. Tổng5chu kỳ scheduler đã quan sát gồm định kỳ và queue;7collector receipts mới ghi176HTTP requests. Các lượt web/Drive/inspection bổ trợ có ghi riêng, không cộng số request chưa lưu đầy đủ vào tổng này. Registry, homepage, robots, DNS/TLS pinning, redirect, giới hạn và pacing cũ được giữ.

Check AIDA trước publish trả NEI trên corpus cũ, runtime enqueue đúng `dut_ctsv`. Queue chỉ lưu authority/state/timing; không có raw text, programme/year, ảnh hoặc URL người dùng. Lượt on-demand `2f9b466e-d525-471e-a805-e7833acd6609` nhận đúng CTSV, thu DUT qua path cố định và **tự publish** AIDA khi policy sử dụng nội bộ đã có. Candidate còn pending không được làm supported giả. Check đang chạy pin corpus cũ; không được hồi tố sửa verdict.

`start/stop/status` kiểm exclusive lock, PID+boot/start identity, heartbeat, restart_count và last-cycle receipt. Đã chạy start/stop/restart thật nhiều lần, giữ lịch, backlog, cooldown và lease. User systemd báo offline nên dùng CLI, không cần root. Process chết được phát hiện, nhưng chưa có supervisor auto-start sau reboot/crash; dùng `start` để chạy lại. Không chạy khi máy/WSL tắt, không tuyên bố24/7 hosting.

## Kết quả ứng dụng và lỗi đã sửa

Check Gemini/HTTP thật sau sửa context đã trả **supported**, đúng source/version mới, chunk `dut_39c806ec6715272c_0294c3ba0dc48e23_c001`, quote tên chương trình nguyên văn tại span `[81,123)`. Truy xuất độc lập qua runtime/index thật cũng tìm thấy source mới. Health/live/frontend HTTP200, source API có URL/hash/chunk đúng.

Giữ nguyên các lần thất bại chất lượng trước đó: model từng trích cả excerpt với span sai nên guard trả NEI/INVALID_CITATION; một lần gán publisher trường vào audience nên thiếu scope phù hợp. Không ép guard pass và không thay kết quả cũ. Một observer QA local chỉ ghi output thật từ SDK, không thay model response. Sửa tối thiểu upstream: context của fact program cung cấp quote nguyên văn cạnh q; không đổi prompt, corpus fact đã publish hoặc strict validator. Actual check kế tiếp phát citation hợp lệ. Một thành công này không chứng minh độ chính xác tổng quát, và input mơ hồ vẫn có thể NEI.

Các lỗi kỹ thuật khác được sửa và có regression: plain document URL lọt completeness; CSS/picture/SVG chưa đọc; blanket quarantine nhầm emoji/form; receipt extractor cũ có thể được tái dùng; null confirmation bị stringify thành evidence; queue bị đánh dấu done khi dừng giữa chừng; mất last-cycle receipt sau restart; QA helper ép mọi phép kiểm history phải đổi corpus; capability file cũ có thể chứa URL ngoài local API. Mặc định config vẫn opt-in sau khi regression phát hiện thay đổi không phù hợp.

Rollback thật về corpus trước, cold restart backend trong trạng thái đó, đọc citation nguồn mới qua archive, rồi restore snapshot mới đều đạt. JSON check NEI cũ và check supported mới không đổi; source mới không mất sau restart. Lỗi build/atomic publication, đồng thời/pinned requests, mạng/robots/quota/refusal được fault-test bằng synthetic fixtures; không giả rằng đã gây quota429 thật của Google. Hai503unknown cũ giữ nguyên reservation.

## QA, chi phí và vận hành

- Full backend/eval **505passed/23.87s**; [QA receipt](../docs/evidence/source-sync/qa.json) ghi lệnh và giới hạn. Frontend37unit/build đạt.31examples/OpenAPI khớp; corpus benchmark6sources/7chunks valid. Locked research files không có diff. Parser fixture1500link cùng host giảm median166.18ms→121.24ms do tái dùng một membership set; không suy hiệu suất model từ số đo này.
- Browser thật390/1440 trên build HTTP/live: keyboard, không overflow/page error; ảnh ở private browser evidence. Kết quả thực tế từng lượt được ghi riêng, không thay bằng mock.
-8curated HTTP/browser checks/16actualmodelattempts:5,822input/2,602output,0USD ước tính Free Tier. Browser thật đã gửi request, mở evidence/snapshot AIDA và xác nhận supported tại390/1440, không interception/mock. Shared ledger còn5attempts local khác trong khoảng đo, không đọc input riêng tư hoặc nhận là curated test; giữ2unknown holds cũ tổng0.0122415USD paid-equivalent. Không reset ledger hoặc tăng phí/billing, không chạy lại preflight.
- Hướng dẫn start/stop/health/review/HTTP/rollback ở [README](../README.md#verified-dut-source-discovery-và-live-refresh). Key/readiness hợp lệ, private state/store và một worker phải được duy trì. Không commit private corpus/source/capability. Code đã push tại [20e1201](https://github.com/hikigayahachimankun/tinchac-workspac/commit/20e1201e92d422e83819d0b18443a69342ab5b9f); [Git receipt](../docs/evidence/source-sync/git-operation.json) xác nhận tree local/remote giống nhau, không force/merge/deploy.

Acceptance ở đây là luồng local đã quan sát. Full12case upstream QA, benchmark/freeze/gold, independent human source review, financial candidates và quyền tái phân phối vẫn là gate riêng, không được tự đóng.

Sau gián đoạn môi trường, backend và scheduler được phát hiện đã dừng rồi khởi động lại từ state cũ. [Resume receipt](../docs/evidence/source-sync/resume.json) xác nhận health/live/frontend/source HTTP200, hai check cũ bất biến, thêm1chu kỳ DUT thật: tổng6scheduler cycles/8collector receipts/199recordedHTTP requests. Không có lượt Gemini mới trong bước resume; không tuyên bố chạy xuyên thời gian máy/WSL ngừng.
