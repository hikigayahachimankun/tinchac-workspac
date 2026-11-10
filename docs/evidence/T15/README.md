# T15 — Lệnh, môi trường và giới hạn kiểm tra

Ngày 10/11/2026, nhánh `task/T15-release-candidate`, từ clean `64b726e`. R1 agent làm tuần tự, dùng local writing-plans/ponytail-review, tự review kỹ thuật. Không independent human review, không key/live/paid calls. OS Ubuntu26.04/WSL2, Linux6.18.58.1, Python3.11.18, Node22.23.4, npm10.9.9, Tesseract5.5.0 vie+eng.

Media và gói chạy là artifact local bị Git ignore, có checksum trong receipts: [video MP4](../../../artifacts/T15/tinchac-demo-rc.mp4), [contact sheet](../../../artifacts/T15/video-contact-sheet.png), ảnh mobile/desktop tại `artifacts/T15/browser/`. Không coi việc đẩy source/checks lên GitHub là công bố binary/video hay cấp quyền phân phối. `artifacts/` không chứa key hoặc dữ liệu sinh viên trong phiên này.

## Thực chạy

```bash
git status --short --branch
git switch -c task/T15-release-candidate
.venv/bin/python -m pytest backend/tests eval/tests -q
.venv/bin/python -m scripts.export_contracts --check
npm test --prefix frontend
```

Baseline392 pytest/37 Vitest,31 examples/OpenAPI matches. Sau sửa và regression mới: **397 pytest/37 Vitest**,31 examples/OpenAPI matches. Full pytest cuối trước docs:30.19s, không skip/xfail. Static extensionless asset test đã FAIL200 trước sửa, sau sửa404. Hai package test ban đầu FAIL do setup mock/thiếu file, đã sửa test setup; không đổi expected nhãn/schema hoặc locked protocol.

```bash
VITE_API_MODE=http npm run build --prefix frontend
.venv/bin/python -m pytest backend/tests/test_static_release.py backend/tests/test_release_packaging.py backend/tests/test_live_http.py -q
.venv/bin/python -m scripts.package_release --output /tmp/tinchac-t15-draft1.tar.gz
python3 scripts/cold_start_release.py --archive /tmp/tinchac-t15-draft1.tar.gz --output /tmp/tinchac-t15-cold1
.venv/bin/python -m scripts.validate_corpus
.venv/bin/python -m scripts.validate_eval
```

Focused13 passed. Build JS249.60kB/gzip78.06kB. `cold-start-draft.json` và `cold-start-draft-commands.json`: archive117 files từ working tree, venv/npm install mới,0npm vulnerabilities, Python dependencies compatible, health/4 cases/source quotes/static/private/API/DELETE đều đạt, one worker tự dừng. Đây là **cùng host**, không máy thứ hai. Corpus6 sources/7 chunks valid; eval15 cases/5 dev families/0gold, validated_NOT_frozen; không benchmark. Các receipt final bổ sung sau khi docs/build cuối.

Server cho diễn tập/quay dùng tree đã giải nén/venv riêng:

```bash
APP_MODE=fixture GEMINI_API_KEY= LLM_LIVE_ENABLED=false \
  DATABASE_PATH=/tmp/tinchac-t15-cold1/tinchac/data/private/demo.sqlite3 \
  PRIVATE_DIR=/tmp/tinchac-t15-cold1/tinchac/data/private \
  FRONTEND_DIST=/tmp/tinchac-t15-cold1/tinchac/frontend/dist \
  /tmp/tinchac-t15-cold1/tinchac/.venv/bin/python -m uvicorn backend.app.main:app \
  --app-dir /tmp/tinchac-t15-cold1/tinchac --host 127.0.0.1 --port 8015 --workers 1
TINCHAC_CHROMIUM_PATH=/tmp/tinchac-chrome/chrome-linux64/chrome \
  LD_LIBRARY_PATH=/tmp/tinchac-browser-libs/unpacked/usr/lib/x86_64-linux-gnu \
  node scripts/record_demo.mjs --base-url http://127.0.0.1:8015 --output /tmp/tinchac-t15-browser1
# Cùng env Chromium/libs:
node scripts/record_demo.mjs --base-url http://127.0.0.1:8015 --output /tmp/tinchac-t15-record1 --record
```

`browser.json`:390/1440, OCR → original C → sửa S, NEI, mixed, failed; keyboard evidence/snapshot, không overflow,0pageerrors/external requests,localStorage/sessionStorage/cookie rỗng. `recording.json`:1280x900,220giây actual capture; không ảnh dựng thay quay. Mọi URL/log dùng ID công khai, không capability. User images chỉ synthetic fixture. Screenshot mobile evidence và desktop quota được xem trực tiếp.

```bash
TINCHAC_CHROMIUM_PATH=/tmp/tinchac-chrome/chrome-linux64/chrome \
  LD_LIBRARY_PATH=/tmp/tinchac-browser-libs/unpacked/usr/lib/x86_64-linux-gnu \
  TINCHAC_EVIDENCE_ROOT=/tmp/tinchac-t15-release-browser \
  npm run test:release --prefix frontend
```

Built FastAPI-only smoke **2/2 passed (23.9s)**,390/1440, axe và keyboard; evidence redirect nên không ghi đè ảnh/log T04. Chặn POST và chèn429 chỉ trong browser. Hai HTTP regressions còn chạy real pipeline/adapter/ledger với SDKmock quota/cap0, assert không verdict/retry/paid fallback, không real SDK call.

```bash
.venv/bin/python -m scripts.run_eval --mode fixture --output /tmp/tinchac-t15-fixture
.venv/bin/python -m scripts.run_eval --mode replay \
  --cases /tmp/tinchac-t15-fixture/cases.jsonl \
  --replay /tmp/tinchac-t15-fixture/runs.jsonl --output /tmp/tinchac-t15-replay
```

Mỗi lượt27/27,0technical errors. `fixture-summary.json`/`replay-summary.json` giữ manifests/config/mode/events. Run đầy đủ local tại `artifacts/T15/{fixture,replay}`. Replay từ fixture, không live/benchmark; không nhập gold.

`source-links.json`: Python httpx HEAD ba URL DUT approved từ corpus, cả ba200; không tải URL người dùng gửi, không giữ page bodies. Lượt đầu dùng system python thiếu httpx rồi chạy lại bằng `.venv/bin/python`; chỉ lượt sau là kết quả. HEAD không xác nhận nội dung mới/quyền.

Video: `scripts/render_demo.py`, storyboard9 đoạn, local espeak-ng1.52 tiếng Việt + ffmpeg9.0.2 + Pillow/DejaVu. Tools được tải ngoài app lock; không cloud TTS/model. Cài thử espeak ban đầu thiếu ALSA/pulse/mpg123 libs, đã giải nén dependency vào `/tmp/tinchac-t15-voice`, không thay requirements/system Python. Lệnh render thực:

```bash
LD_LIBRARY_PATH=/tmp/tinchac-t15-voice/unpacked/usr/lib/x86_64-linux-gnu:/tmp/tinchac-browser-libs/unpacked/usr/lib/x86_64-linux-gnu:/tmp/tinchac-t15-voice/unpacked/usr/lib/x86_64-linux-gnu/pulseaudio \
  .venv/bin/python -m scripts.render_demo \
  --video /tmp/tinchac-t15-record1/page@d45a7cfeff2a48e076eb83d7aba9b58c.webm \
  --output /tmp/tinchac-t15-demo.mp4 \
  --ffmpeg /home/truong/.cache/uv/archive-v0/3w3KreQXtSbmeZlt/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v9.0.2 \
  --espeak /tmp/tinchac-t15-voice/unpacked/usr/bin/espeak-ng \
  --espeak-data-parent /tmp/tinchac-t15-voice/unpacked/usr/lib/x86_64-linux-gnu
```

`video-audit.json`: SHA256/bytes,220s,H264/AAC, full audio/video decode exit0,9 sampled frames with fixture watermark/OCR/key-pattern scan. Narration synthesized from public storyboard, no microphone/person. Visual contact-sheet review is separate; no human listening claimed. Count-only secret scans are limited detectors, not proof against every possible secret; inputs/browser were restricted to self-created fixture content.

## Gates chưa chạy

- Không máy thứ hai/VM độc lập: Docker command báo chưa WSL integration; no access to another host. Receipt `second_machine_verified=false`.
- Không tự gọi live quota hoặc reset ledger. Actual DUT supported case chưa QA đạt; upstream real run2 hai completed đều NEI rồi503.
- Không human pilot/correction/gold/evidence scoring/freeze; không sửa model/corpus/test protocol.
- Không external rights clearance/public hosting/deploy/merge/submission.
- Native `git push --dry-run` exit128: thiếu HTTPS username/credential, không phải auto-review rejection. Dùng connected GitHub Git Data API cho source branch nếu khả dụng; annotated RC tag local và Git bundle giữ được nếu connector không có tag API. Kết quả Git cuối xem handoff và Git, không gọi push tag thành công khi chưa chạy được.
