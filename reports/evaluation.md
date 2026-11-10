# TinChắc — đánh giá

**Chưa chạy benchmark.** Fixture/replay kiểm plumbing, không phải thành tích mô hình.

| Cấu hình / inventory | Giá trị |
|---|---|
| Commit, model/version, SDK, corpus, config/prompt hashes | chưa chạy |
| Nguồn / family / case theo split, origin, domain, label | chưa chạy |
| Split/freeze receipt, temporal subset, người chấm | chưa chạy |

| Hệ thống | Accuracy n/N | Macro F1 (support 3 lớp) | ERROR n/N | Coverage | Answerable resolution |
|---|---|---|---|---|---|
| A | chưa chạy | chưa chạy | chưa chạy | chưa chạy | chưa chạy |
| B | chưa chạy | chưa chạy | chưa chạy | chưa chạy | chưa chạy |
| C | chưa chạy | chưa chạy | chưa chạy | chưa chạy | chưa chạy |

| Hệ thống có nguồn | ECV family / micro | Citation validity | Evidence sufficiency | Recall / Hit / Complete-set@5 |
|---|---|---|---|---|
| B | chưa chạy | chưa chạy | chưa chạy | chưa chạy |
| C | chưa chạy | chưa chạy | chưa chạy | chưa chạy |

A: các chỉ số bằng chứng N/A vì không được cấp nguồn. ECV là chỉ số TinChắc, không gọi là điểm AVeriTeC; S19: https://aclanthology.org/2024.fever-1.1/ .

- C−B, paired family bootstrap2000 seed42, 95% CI, n family: chưa chạy.
- C_NO_TIME: subset chọn trước, temporal accuracy/ECV và chênh lệch với C: chưa chạy.
- Xác nhận nhầm (C/N, miền tiền), mâu thuẫn nhầm, selective error: chưa chạy.
- Lỗi kỹ thuật theo loại; missing rows; unknown usage; run dừng và phần chưa chạy: chưa chạy.
- Latency p50/p95/stage (fresh), mọi attempt, USD/VND/tỷ giá, chi phí/case thành công: chưa chạy.
- OCR CER tự động/có sửa và extraction trên bộ end-to-end riêng: chưa chạy; không lấy từ target benchmark.
- Năm lỗi tiêu biểu và giới hạn (mẫu nhỏ, synthetic, solo reviewer, corpus đóng): chưa chạy.

Tái tính bằng `python -m scripts.score_eval --run RUN_DIR --gold OWNER_GOLD --evidence OWNER_SCORES --output NEW_METRICS.json`. Gold và evidence scores ở máy owner; không chép vào provider hoặc report công khai.

## T13 — kiểm điều kiện ngày 10/11/2026, giờ Việt Nam

**Blocked; chưa có kết quả A/B/C hoặc C_NO_TIME thật.** Không suy ra C tốt hơn B, không tính ECV/CI từ fixture. Phần mẫu phía trên giữ “chưa chạy”. Dữ liệu kiểm offline và SHA-256 candidate: [t13_readiness.json](t13_readiness.json); lệnh thực chạy và checkpoint: [T13 handoff](../docs/handoffs/T13.md).

| Provenance / inventory hiện có | Giá trị đã kiểm |
|---|---|
| Branch / HEAD nền | `task/T13-benchmark-evidence` / `1c8e8ce8cce6f79d567f26c0799024dd3fdacb30`; upstream chưa commit |
| Corpus local | `corpus-7b832d58775878a57849d32ff241cc61904afadfc0299a66e3918ad82da18982`; 6 sources, 5 approved/1 excluded, 7 chunks |
| Family dev / test | 5 / 0; 4 scholarship + 1 payment ở dev; không có holdout được cấp |
| Case dev / test được cấp | 15 / 0; 12 scholarship, 3 payment |
| Origin dev | 5 source_derived, 10 synthetic_modified, 0 user_contributed; không phải tin nhắn lừa đảo thực tế |
| Gold đã nạp / phân bố nhãn | 0 / chưa biết; không tự suy nhãn từ origin |
| Split / freeze | `pilot_draft_NOT_frozen`; chưa có receipt input/gold/corpus/config/prompts/commit được owner khóa |
| Model / version / SDK | ứng viên `gemini-3.5-flash-lite`, `model_verified=false`, version chưa biết; `google-genai==3.0.0` cục bộ |
| Config / prompt hashes | raw file SHA-256 và composed-prompt/config digest ghi riêng trong `t13_readiness.json`; **candidate, không freeze** |
| n output thật / N test chốt / ERROR | 0 / chưa xác định / chưa có phép đo; không báo 0% lỗi |
| Temporal test subset / EvidenceScore thật | chưa khóa / 0; chưa chấm mù hoặc adjudication |
| Chi phí phiên T13 | 0 calls provider, 0 tokens tài khoản, 0 USD/0 VND; chưa đối soát chi phí toàn dự án |

Năm blocker dưới đây **không phải năm lỗi dự đoán của mô hình**. Chưa có run thật nên chưa thể bàn giao năm lỗi tiêu biểu theo nghiệm thu T13.

| ID / owner | Bằng chứng và điều kiện mở chặn |
|---|---|
| T13-B01 — R3/R4/T09 | T09 chỉ có family dev, không gold/test được cấp. Hoàn tất nguồn/nhãn/split theo `eval/owner_handoff.md`; không chuyển dev thành test hoặc bù biến thể để tăng n family. Dưới 24 family chỉ báo pilot kỹ thuật theo §4.2. |
| T13-B02 — R1/D02 | Model chưa verified, config corpus `TO_BE_FROZEN`. R1 tự xác minh model/quota/giá/thinking và ledger bền vững; giữ trần evaluation 1,4 USD và trần tổng hiện có, ngân sách dự án tối đa 200.000 VND. Agent không chạy live preflight/key. |
| T13-B03 — R1/R4/T09/T11 | Hai đề xuất D17 chưa được owner duyệt: prepare Claim từ input và accounting unknown. Cần quyết định owner trước freeze; không sửa API/schema để vượt chặn. |
| T13-B04 — R4/T09 | Chưa khóa temporal subset test, lịch phân bổ và commit chứa implementation thực tế. Ghi subset trước predictions theo protocol, hash config/prompts/sidecar và owner review/commit; không sửa model/tập test trong T13. |
| T13-B05 — chủ repo/R3/R4 | Chưa có output/phiếu chấm độc lập. R3/R4 phải là người chấm thật; nếu chỉ solo thì ghi một người chấm, không báo đạt yêu cầu chấm độc lập đôi hoặc dựng reviewer bằng AI. |

Kiểm công cụ offline đã chạy: 49 tests eval đạt; corpus hợp lệ; 31 contract examples/OpenAPI khớp; fixture 27/27 và replay 27/27, predictions bằng nhau; scorer CLI chạy hai lần trên **8 outcome tổng hợp của T11**, output giống từng byte. Đây chỉ là kiểm công cụ. 32 context fixture không có trường gold và dùng bundle chung đúng yêu cầu; **chưa audit prompt logs test thật**. Family/version overlap rỗng ở inventory hiện tại nhưng test rỗng, nên **chưa nghiệm thu overlap test**. Chưa hand-check 10 ca thật, chưa tính secondary metrics/origin-domain subgroups/latency/cost thật, OCR/extraction end-to-end hoặc CI thật.

Không tạo `runs.jsonl`, `evidence_scores.jsonl`, `metrics.json`, `run_manifest.json` rỗng hoặc điền fixture thay kết quả thiếu. Raw fixture/replay/vector tổng hợp giữ trong thư mục riêng `/tmp/tinchac-t13-readiness-0bwth1z4/`; hashes và stdout/stderr/lệnh/exit codes lưu trong `t13_readiness.json`. `/tmp` có thể bị dọn; regression tái tạo được theo handoff. Chưa có run lỗi live để lưu; việc config từ chối fresh không phải lỗi dự đoán hoặc một case NEI.

Khi đủ điều kiện, R1 tính trước subset bằng đúng quy tắc sort case_id/shuffle Random(42)/tối đa 24 ca thời gian trong runner, gọi `eval.harness.schedule` và so với receipt **trước khi khởi chạy fresh**; sau run đối soát manifest. Runner hiện tự tính subset, chưa nhận danh sách private đã khóa làm đối số; nếu không khớp thì báo R4/T11, không chạy để xem kết quả rồi chọn lại. Dùng input công khai đã duyệt, output directory mới và cùng ledger. Giữ mọi attempt/reservation/error, raw/final prediction và shared bundle. Dừng khi quá 10% case lỗi kỹ thuật hoặc chạm budget; run lại toàn run bằng ID mới, giữ run cũ và mẫu số chốt.

Phiếu chấm sau run phải ẩn `system`, `run_id` (chứa tên hệ thống), tên file/thứ tự A/B/C, model/prompt/config hashes, guard_changes, accounting và timing. Dùng mã phiếu ngẫu nhiên và xáo thứ tự trước chấm; bảng ánh xạ chỉ người điều phối giữ. Cấp claim/as_of, prediction/reason/evidence và cùng snapshot nguồn/gold cho từng người chấm riêng; giữ phiếu thô, đối soát rồi xuất EvidenceScore đúng khóa thật. Chấm mọi S/C và lý do mọi N, không chỉ ca hệ thống bất đồng; A không có nguồn nên chỉ số bằng chứng N/A. Nếu bổ sung gold evidence thì version hóa và chấm lại cho mọi hệ. Chưa tạo phiếu hoặc người chấm giả trong phiên này.

Cho T16/T17: hiện chỉ có bằng chứng harness/validator offline; chưa có bằng chứng thực nghiệm ủng hộ hay bác bỏ H1. Không dùng số fixture trong hồ sơ hoặc coi tất cả N là thành công. Demo dùng case công khai riêng theo T15; không chọn ca benchmark tốt nhất để thay bảng kết quả. Hạn nội bộ vẫn 22/11/2026; nếu gate chưa đủ thì ghi phần chưa chạy và giới hạn đúng thực tế.
