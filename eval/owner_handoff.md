# Bàn giao người giữ gold — chưa gán nhãn, chưa freeze

Đây là hướng dẫn để chủ repo tự thực hiện, **không** phải yêu cầu agent đọc private file. Dùng thư mục riêng ngoài `/home/truong/projects/tinchac-workspace`, hạn chế quyền OS cho chính bạn. Gitignore không phải cơ chế niêm phong; không đặt gold test vào `data/private`, worktree khác của agent hoặc đường dẫn symlink trong workspace. Không gửi nội dung file vào chat. Hiện chưa có input/gold test để niêm phong.

## Worksheet một case (không phải GoldRecord hợp lệ)

Tạo bảng riêng với các cột sau; giữ nhãn trống tới khi bạn đọc nguồn:

| Mục | Người đọc điền |
|---|---|
| case_id / target claim | Lấy từ input đúng phiên bản |
| Scope / as_of | Program, year, audience/cohort, fee kind/bank, thời điểm |
| Nguồn đã đọc | Version, chunk, trang; approved và available_at |
| label / reason_codes | Một trong ba enum; lý do phù hợp |
| acceptable_evidence_sets | Danh sách bộ chunk đủ, hoặc [] nếu N không cần evidence |
| reference_quotes / quote_spans | Quote nguyên văn + chunk_id + span [start,end) tương đối trong chunk NFC |
| temporal_status / rationale | Trạng thái riêng; nếu N ghi cụ thể thiếu gì và nguồn nào đã kiểm |
| annotator_1 | Mã người thực sự đọc |
| annotator_2 / agreement_before_adjudication | null / null trong pilot solo |
| adjudication_note | Giới hạn solo, điểm khó hoặc kết quả đối soát thật |

`eval/schema.py:GoldRecord` là schema thực để xuất JSONL, không tự điền nhãn AI. Dùng `EvalCase` cho cả dev/test input, không thêm gold hoặc evidence hints ngoài whitelist. `quote_spans` là extension local để kiểm §4.4; không thay enum API. Ghi nguồn origin: source_derived là bạn soạn theo nguồn (không phải tin nhắn thực); synthetic_modified phải mô tả thay đổi; user_contributed chỉ khi có ca thật đã che dữ liệu và consent. Không gán origin từ label.

Lưu log loại/sửa trước freeze riêng: case_id, version cũ, ngày, lý do nguồn/quyền/scope/đa claim, hành động; không chứa prediction. Với test, log cũng giữ riêng. Không ép đủ ba nhãn bằng cách gán sai.

## Kiểm dev (chủ repo chạy sau khi gán)

```bash
.venv/bin/python -m scripts.validate_eval \
  --dev-gold data/dev/gold.jsonl --require-gold
```

Mặc định không có file gold dev; bạn tạo sau khi đọc nguồn. Lệnh không in nhãn/quote. S/C phải được bạn kiểm entailment và scope; validator không làm thay phần đó. Solo không có agreement/kappa liên người.

## Kiểm test riêng (chỉ chủ repo chạy)

Thay đường dẫn ví dụ bằng file thật ngoài workspace. Các file phải tồn tại, không dùng placeholder trong dữ liệu thật.

```bash
.venv/bin/python -m scripts.validate_eval \
  --dev-gold data/dev/gold.jsonl \
  --test-cases /duong-dan-rieng-ngoai-workspace/test_input.jsonl \
  --test-gold /duong-dan-rieng-ngoai-workspace/test_gold.jsonl \
  --require-gold
```

Chưa chạy lệnh này ở T09. Test family chưa có trong manifest hiện tại, nên cần thu nguồn approved mới, review family, chốt manifest trước khi soạn test. Không dùng năm mới/bản repost của family dev làm test độc lập. Không chạy lại `scripts.eval_inventory` trên corpus mở rộng để tự chọn split: script bảo vệ inventory hiện tại; quota mới cần review và version hóa.

## Receipt hash khi đủ điều kiện khóa

Chuẩn bị config thật T11, toàn bộ prompt A/B/C/C_NO_TIME dùng thực tế, temporal subset chọn trước (giữ private, có thể đặt trong config), commit tương ứng sau khi bạn review và commit các thay đổi. Script từ chối working tree bẩn; không tự commit. D02/model version còn thiếu phải giải quyết trước, không dùng tên dự kiến để coi đã xác minh.

Copy object dưới vào `attestation.json` riêng, đổi **từng false thành true chỉ sau khi thực sự kiểm**. Đây là lời xác nhận của bạn; không phải kết quả tự động. Chấp nhận pilot không được trình bày thành đạt 24/36 family. Nếu chỉ có solo, ghi rõ hạn chế trong báo cáo cuối, không tích true để ngụ ý có hai người.

```json
{
  "human_gold_reviewed": false,
  "one_claim_per_case": false,
  "scope_entailment_reviewed": false,
  "source_spotcheck_complete": false,
  "test_sealed_until_T13": false,
  "no_test_tuning": false,
  "temporal_subset_selected": false,
  "config_resolved": false,
  "pilot_limits_accepted": false
}
```

Sau đó chủ repo tự chạy, bổ sung mọi prompt thực bằng cách lặp `--prompt`:

```bash
.venv/bin/python -m scripts.validate_eval \
  --dev-gold data/dev/gold.jsonl \
  --test-cases /duong-dan-rieng-ngoai-workspace/test_input.jsonl \
  --test-gold /duong-dan-rieng-ngoai-workspace/test_gold.jsonl \
  --config /duong-dan-rieng-ngoai-workspace/run_config.json \
  --prompt /duong-dan-rieng-ngoai-workspace/prompt_A.txt \
  --prompt /duong-dan-rieng-ngoai-workspace/prompt_B.txt \
  --prompt /duong-dan-rieng-ngoai-workspace/prompt_C.txt \
  --prompt /duong-dan-rieng-ngoai-workspace/prompt_C_NO_TIME.txt \
  --attestation /duong-dan-rieng-ngoai-workspace/attestation.json \
  --receipt /duong-dan-rieng-ngoai-workspace/lock_candidate.json
```

Receipt ghi SHA-256 byte thật của input/gold/manifest/corpus 3 files/protocol/guide/schema/validator/config/prompts/attestation và commit HEAD. Nó không overwrite receipt cũ và không in gold. Trạng thái luôn `validated_candidate_NOT_frozen`; chủ repo đối chiếu checksum, xác nhận đủ dữ liệu và bước kiểm, rồi tự ghi quyết định lock/version/ngày 16/11 hoặc ngày thực tế. Nếu thiếu dữ liệu/nhãn, để draft. Hiện **không đủ điều kiện** ghi receipt freeze: 0 test, 0 gold, thiếu spot-check, config/model chưa chốt, upstream chưa commit.

Tới T13 chỉ mở test input sau khóa, giữ gold riêng để chấm. Sau freeze sửa hạ tầng có log; tuning từ lỗi test làm run mới exploratory, không thay thế run đăng ký. Hash phiên bản cũ và run lỗi phải giữ.
