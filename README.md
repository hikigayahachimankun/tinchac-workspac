# TinChắc · Bản chạy local cho sinh viên DUT

Ảnh/văn bản → OCR cục bộ và xác nhận chữ → đối chiếu từng chi tiết → nguồn và bước kiểm tra tiếp. API `/api/v1`, schema `1.0`. **Bản T15 hiện là release candidate nội bộ ở chế độ fixture; chưa nghiệm thu live/ca DUT thật; cold-start môi trường CI độc lập đã đạt.** Không dùng kết quả mẫu để quyết định đóng tiền/nộp hồ sơ. [Checklist và giới hạn](reports/release_checklist.md) · [Demo/video](docs/demo_script.md) · [Handoff T15](docs/handoffs/T15.md).

## Chạy bản demo hiện tại

Từ repo hoặc thư mục `tinchac/` đã giải nén gói RC, cần Python **3.11.18**, Node **22.23.4** (`.python-version`, `.nvmrc`), uv và Tesseract **vie+eng**. Ubuntu/WSL: `sudo apt-get install tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng fonts-dejavu-core`. Không cần key, `.env` hoặc paid hosting. Dùng thư mục mới, không đặt file `.env` trong đó.

```bash
uv venv --python 3.11.18 .venv
uv pip sync --python .venv/bin/python requirements.lock.txt
uv pip check --python .venv/bin/python
npm ci --prefix frontend
VITE_API_MODE=http npm run build --prefix frontend
tesseract --list-langs
APP_MODE=fixture GEMINI_API_KEY= LLM_LIVE_ENABLED=false \
  DATABASE_PATH=./data/private/demo.sqlite3 .venv/bin/python -m scripts.init_db
APP_MODE=fixture GEMINI_API_KEY= LLM_LIVE_ENABLED=false \
  DATABASE_PATH=./data/private/demo.sqlite3 PRIVATE_DIR=./data/private \
  FRONTEND_DIST=./frontend/dist .venv/bin/python -m uvicorn backend.app.main:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

Mở `http://127.0.0.1:8000`. Chỉ một tiến trình FastAPI phục vụ cả UI/API; không cần Vite. Chọn mẫu trong “Tình huống mô phỏng”, đồng ý rồi kiểm tra; mở “Xem bằng chứng” và snapshot. Thử ảnh tự tạo `data/fixtures/ocr/vietnamese-clear.png`, kiểm chữ/số tiền rồi xác nhận. Mẫu cố định chỉ nhận đúng các văn bản trong `data/fixtures/cases.jsonl`; không phân tích văn bản tùy ý. Nguồn im lặng → chưa đủ bằng chứng; hết hạn là trường riêng; lỗi API → lỗi kỹ thuật, không có nhãn.

Terminal khác, cùng thư mục:

```bash
.venv/bin/python -m scripts.release_smoke --base-url http://127.0.0.1:8000
```

Kết quả mong đợi: health `fixture/1.0/fixture-v1`, không provider; static/API boundary, source quote và DELETE đạt; mixed có S/C/NEI, supported có S, nei có NEI, failed không có verdict. Không mở URL do người dùng nhập. Fixture URL `.example` chỉ là định danh mô phỏng, không có nút mở nguồn gốc thật.

Đóng gói từ checkout đã build; output mới, không ghi đè:

```bash
mkdir -p artifacts/T15
.venv/bin/python -m scripts.package_release --output artifacts/T15/tinchac-rc.tar.gz
python3 scripts/cold_start_release.py --archive artifacts/T15/tinchac-rc.tar.gz \
  --output /tmp/tinchac-new-cold-start
```

Script tạo thư mục mới, kiểm hash, venv riêng, npm install/build mới, chạy một worker rồi tự dừng. Cài dependencies lần đầu cần mạng/package cache; demo fixture đã cài chạy offline. Manifest trong gói ghi commit, hash từng file/locks/config/seed, model/corpus fixture và hash manifest corpus thật tham chiếu. Gói chỉ có mã, build và fixture tự tạo; không chứa key, DB/ledger riêng, gold, raw, snapshot corpus thật hoặc vendor binaries. Quyền phân phối ngoài nhóm vẫn là gate mở.

**Đã thử 10/11/2026:** Ubuntu26.04/WSL2 Linux6.18.58.1, Python3.11.18, Node22.23.4, Tesseract5.5.0 vie+eng. Cold-start thành công trong cây giải nén và venv mới **trên cùng host**; browser Chromium390/1440, OCR, bàn phím và injection mất kết nối/quota đạt. Sau đó cùng quy trình đạt trên **GitHub-hosted Ubuntu24.04/Azure độc lập với WSL**: [run thực tế](https://github.com/hikigayahachimankun/tinchac-workspac/actions/runs/42827045087), [receipt](docs/evidence/T15/independent-ci.json). Đây là VM khác, chưa thử laptop demo vật lý. Bằng chứng/lệnh: [T15](docs/evidence/T15/README.md).

Live dùng `gemini-3.5-flash-lite` theo cấu hình hiện có, tắt mặc định; corpus thật `corpus-7b832d58775878a57849d32ff241cc61904afadfc0299a66e3918ad82da18982` chỉ có trong checkout có quyền truy cập. [Setup/ledger thật](docs/live_setup.md) ghi preflight Free Tier đã đạt nhưng HTTP QA còn lỗi503/unknown; không chạy live từ gói fixture. HTTP replay chưa có recording cấu hình; CLI replay offline được kiểm riêng, không phải kết quả benchmark.

Các mục dưới là hướng dẫn workspace và checkpoint lịch sử. Điểm bắt đầu chạy app hiện tại là mục trên; trạng thái task ở [progress](docs/progress.md). Đặc tả gốc ở [kế hoạch](TINCHAC_PROJECT_PLAN.md).

## 1. Mở workspace trên Windows

1. Nếu chưa có WSL2, chạy `wsl --install -d Ubuntu` trong PowerShell Administrator, khởi động lại nếu Windows yêu cầu. Kiểm `wsl -l -v` để Ubuntu dùng version 2.
2. Cài VS Code trên Windows và [extension WSL](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl).
3. Vào Ubuntu. Cài công cụ hệ thống dưới đây. Cài [nvm](https://github.com/nvm-sh/nvm#installing-and-updating) và [uv](https://docs.astral.sh/uv/getting-started/installation/) theo hướng dẫn upstream trong Ubuntu, rồi mở lại terminal để các lệnh có trên PATH.

```bash
sudo apt-get update
sudo apt-get install -y git curl unzip tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng
```

4. Chạy các lệnh sau trong Ubuntu.

```bash
nvm install 22
nvm use 22
uv python install 3.11
npm install -g @openai/codex
codex login
```

5. Giải nén ZIP vào thư mục Linux, ví dụ `~/projects/`. Sửa `TEN_WINDOWS` hoặc đường dẫn ZIP bên dưới theo máy. ZIP có một thư mục ngoài là `tinchac-workspace`. Mở VS Code từ đó. Nếu nhóm đã tạo repo, clone repo vào thư mục Linux trước, rồi đối chiếu và ghép các file setup vào repo đó. Giữ nội dung nhóm đã sửa ở `AGENTS.md`, `.gitignore`, `.env.example` và `.codex/config.toml`.

```bash
mkdir -p ~/projects
unzip '/mnt/c/Users/TEN_WINDOWS/Downloads/TinChac_Codex_Workspace.zip' -d ~/projects
cd ~/projects/tinchac-workspace
git init -b main                  # Chỉ chạy khi tạo repo mới từ ZIP
bash scripts/check-dev-env.sh
code .
```

6. Kiểm góc dưới trái hiện **WSL: Ubuntu**. Cài **Codex** của OpenAI và **Python** trong cửa sổ WSL khi VS Code gợi ý. Đăng nhập Codex bằng tài khoản ChatGPT. Tin cậy đúng project sau khi xem các file cấu hình. Mở thread mới, nhập `$` hoặc mở `/skills` để thấy `writing-plans`, `handoff`, `ponytail-review` và `impeccable`. Nếu trùng tên với plugin cài toàn máy, chọn bản thuộc thư mục repo. CLI là đường chạy dự phòng nếu một lệnh slash chưa có trong bản IDE đang dùng.

7. R1 commit baseline vào repo nhóm rồi giao việc. Mỗi thành viên dùng branch riêng theo task. R1 khóa patch Node/Python đã chạy ở T01 theo đặc tả. `.venv` được tạo tại repo root khi T01 cài dependencies.

Tài liệu cài đặt · [Codex trên WSL](https://learn.chatgpt.com/docs/windows/wsl) · [Cấu hình IDE](https://learn.chatgpt.com/docs/ide/settings) · [Skills cấp repo](https://learn.chatgpt.com/docs/build-skills) · [Vite](https://vite.dev/guide/)

## 2. Bốn skill dùng theo việc

| Việc | Cách gọi | Kết quả cần kiểm |
|---|---|---|
| Viết kế hoạch trước code | `$writing-plans` trong Plan mode cho T01/T05/T08/T11 hoặc phần có nhiều phụ thuộc | Các bước nhỏ có tệp, điều kiện nghiệm thu và lệnh kiểm. Kế thừa mục Txx, giữ nguyên hợp đồng. Chốt cách thực thi tuần tự trong một agent cho mỗi task. |
| Rút gọn phiên dài | `$handoff` khi sắp chuyển phiên, dùng cùng mẫu trong `docs/handoffs/` | Đường dẫn tới code/spec, trạng thái, việc kiểm thực sự, blocker và đúng một bước tiếp. Skill upstream viết vào thư mục tạm. Ghi bản chính trong repo. |
| Review code gọn | `$ponytail-review` trên diff và các caller | Tách lỗi hành vi, rủi ro dữ liệu, test thiếu và phần thừa. Nếu chê chậm, chỉ rõ ca và đo trước/sau. |
| Thiết kế hoặc review UI | `$impeccable` kèm việc cụ thể, sau đó `$impeccable critique …` và `$impeccable audit …` | Đọc PRODUCT.md và docs/ui-brief.md. Render bằng dữ liệu fixture, chụp 390 và 1440 px, kiểm bàn phím và trạng thái lỗi. |

Mỗi skill được gọi tường minh, kèm upstream và commit trong [.agents/THIRD_PARTY.md](.agents/THIRD_PARTY.md). Impeccable có thể cần tải engine có checksum từ GitHub lần đầu. Ở terminal WSL, có thể chạy trước bằng lệnh sau. Nếu không tải được, vẫn đọc PRODUCT.md và docs/ui-brief.md và nghiệm thu giao diện trên trình duyệt.

```bash
DO_NOT_TRACK=1 .agents/skills/impeccable/scripts/impeccable context
```

### Prompt UI sau T01

```text
Triển khai T03 trên API fixture v1.
Đọc PRODUCT.md, DESIGN.md, docs/ui-brief.md, mục T03 và contracts/examples.
Giữ hướng thiết kế đã ghi. Dùng màu, typography và bố cục từ brief làm điểm xuất phát. R2 duyệt thiết kế sau khi có bản chạy.
Kiểm 390/1440 px, thứ tự Tab, lỗi upload và case có đủ ba nhãn.
Dùng Playwright khi fixture và test runner đã sẵn sàng. Đính kèm ảnh render trong handoff.
```

Khi có bản render, chạy `$impeccable critique màn nhập và bảng đối chiếu` hoặc `$impeccable audit luồng kiểm tra thông báo`. Dùng skill để review và chỉnh phạm vi nhỏ khi agent chạy một mình. Vòng thiết kế lại toàn bộ của upstream có thể yêu cầu R2 chọn hướng. Nếu sandbox chặn chạy trình duyệt hoặc dev server, khởi động chúng trong terminal WSL theo README của app và dùng fixture.

Nguồn các skill · [Superpowers](https://github.com/obra/superpowers) · [Matt Pocock](https://github.com/mattpocock/skills) · [Ponytail](https://github.com/DietrichGebert/ponytail) · [Impeccable](https://github.com/pbakaus/impeccable)

## 3. Tổ chức repo và context

| Đường dẫn | Trách nhiệm |
|---|---|
| `AGENTS.md` | Quy tắc ngắn dùng chung mọi phiên |
| `TINCHAC_PROJECT_PLAN.md` | Mục tiêu, hợp đồng, phụ thuộc và tiêu chí nghiệm thu |
| `backend/app/api`, `backend/app/services` | API và xử lý nghiệp vụ trong FastAPI |
| `frontend/src/api`, `frontend/src/components` | Client theo hợp đồng và UI React |
| `contracts/`, `config/`, `prompts/` | OpenAPI/examples, cấu hình nguồn/thí nghiệm, prompt có phiên bản |
| `scripts/`, `eval/`, `data/fixtures/` | CLI vận hành, đánh giá, đầu vào mô phỏng |
| `docs/progress.md`, `docs/handoffs/`, `docs/decisions.md` | Tiến độ, điểm tiếp tục, quyết định |
| `data/private/`, `data/raw/` | Dữ liệu cục bộ do nhóm quản lý. Gold test đặt ngoài repo. |

Tạo thư mục code theo §3.4 khi task cần. Khi sang task mới hoặc hội thoại bắt đầu lạc chủ đề, mở thread mới và đưa đúng checkpoint. Với một task dài có thể dùng `/compact` nếu client hỗ trợ, sau khi checkpoint đã được ghi. Tách việc tìm tài liệu phiên bản thư viện khỏi ghi nhớ tiến độ. Giữ log dài ngoài prompt, chỉ đưa lỗi và đường dẫn cần chẩn đoán.

Nhóm có thể bổ sung [planning-with-files](https://github.com/OthmanAdi/planning-with-files) nếu thường mất trạng thái giữa các lần compact trong cùng task và cần hook tự nạp lại. Thử trên một branch/worktree riêng, chọn rõ một plan khi có nhiều task, đọc hook trước khi bật. Bộ khởi tạo dùng checkpoint Git sẵn của dự án để tránh hai sổ tiến độ.

## 4. Chế độ Codex và hạn mức

- Mặc định **GPT-6.1 Sol / Medium / Standard** cho tính năng xuyên API, chỉnh logic và debug. Dùng **Sol / Low** cho sửa cục bộ đã có cách kiểm. Dùng **Luna / High / Standard** nếu có trong model picker cho fixture, tài liệu và thay đổi lặp lại có hợp đồng rõ.
- Dùng **Sol / High** cho schema, trạng thái job, quota/budget, logic thời gian/bằng chứng và sai số eval. Dùng Astra cho blocker khó hoặc review nhiều ràng buộc nếu tài khoản có.
- Plan mode chốt việc phức tạp. Chuyển sang chế độ chỉnh sửa cho task đã rõ. `workspace-write` + `on-request` là mặc định. Agent sửa/chạy trong workspace và hỏi khi cần quyền vượt sandbox. Việc cài package cần mạng thực hiện trước khi giao chạy lâu. Dùng tốc độ Standard trên bộ chọn model.
- `/goal` hợp với một mốc có kiểm tra và điều kiện dừng. Ví dụ chạy T01 sau T00. Với luồng fixture cần chạy vắng người và mọi dependency đã sẵn, có thể mở **một phiên CLI riêng** bằng `codex --sandbox workspace-write --ask-for-approval never`; lệnh cần vượt sandbox sẽ bị từ chối. Giữ phiên này không có key live.
- Cửa sổ ngữ cảnh, quota ChatGPT của Codex và quota Gemini là ba thứ riêng. CLI `/status` và [trang Usage](https://chatgpt.com/codex/settings/usage) cho biết thời điểm reset. Có thể còn hạn mức tuần. Chờ thời điểm tài khoản hiển thị, sau đó mở đúng thread trong IDE hoặc dùng `codex resume <SESSION_ID>` trong CLI. Nếu là goal bị pause, dùng `/goal resume` ở client hỗ trợ. Nếu phải mở thread mới, dùng mẫu ở dưới.
- Tài liệu chính thức xác nhận goal chạy qua nhiều lượt và cách resume thủ công. Chưa xác minh chế độ tự chờ reset rồi resume ổn định cho VS Code. [Codex Auto Resume Windows](https://github.com/songyb111-gachon/codex-auto-resume-windows) dành cho Codex Desktop Windows. [LUCIENIN/codex-auto-resume](https://github.com/LUCIENIN/codex-auto-resume) là supervisor CLI thử nghiệm, chưa kiểm được chu trình reset thật trên Windows/WSL. Cấu hình này giữ resume theo thread và checkpoint, chưa bật supervisor.

Tài liệu Codex · [Models](https://learn.chatgpt.com/docs/models) · [Usage và tốc độ](https://learn.chatgpt.com/docs/pricing) · [Goals](https://learn.chatgpt.com/use-cases/follow-goals) · [CLI resume](https://learn.chatgpt.com/docs/cli/reference)

### Prompt khởi động T01 sau khi nhóm chốt T00

```text
Chỉ nhận T01 trên nhánh task/T01-contract. Đọc AGENTS.md, docs/progress.md,
docs/decisions.md, mục T01 và §3.4–3.8, §7.1–7.3 của kế hoạch.
Chia bước theo hợp đồng và nghiệm thu sẵn có. Thực thi tuần tự.
Giữ API /api/v1 và schema 1.0. Dùng fixture, không gọi Gemini.
Dừng khi health chạy, examples validate, export OpenAPI không drift,
các ca validator bắt buộc đạt và docs/handoffs/T01.md đã có kết quả.
Nếu thiếu dependency hoặc quyền, làm tiếp phần độc lập rồi ghi blocker.
```

### Prompt tiếp tục

```text
Tiếp tục Txx trên đúng branch cũ. Đọc AGENTS.md, hàng Txx trong
docs/progress.md, docs/handoffs/Txx.md và mục Txx trong kế hoạch.
Kiểm git status/diff và các lệnh kiểm đã ghi. Bắt đầu từ bước tiếp theo
trong handoff. Cập nhật checkpoint sau bước kiểm được và dừng theo nghiệm thu.
```

## 5. Checklist đầu vào trước khi giao agent

| Khi | Ai | Chuẩn bị |
|---|---|---|
| Trước T01 | R1 | Repo riêng, owner/reviewer R1–R4, nhánh task, quyền clone, Git identity. Chốt ai có quyền sửa schema và ai giữ test. |
| Trước T01/T03 | R1/R2 | VS Code WSL chạy, Python 3.11, Node 22.12+ trong major 22, SQLite FTS5, Tesseract `vie+eng`, một laptop demo. Chốt ngày giờ `Asia/Ho_Chi_Minh`. |
| Trước T03 | R2 | Một case mẫu giả lập đầy đủ ba nhãn, một case hết hạn và một case lỗi kỹ thuật. Duyệt hướng giao diện. Chuẩn bị ảnh test đã che dữ liệu cá nhân và logo nhóm nếu đã có quyền dùng. |
| Song song T01 | R3 | Sáu nguồn chính thức seed có URL gốc và snapshot. Đọc attachment thật, ngày công bố, đối tượng, thời điểm lưu và quyền chia sẻ. Dùng §4.1 để khởi đầu. |
| Trước T05 live | R1 | Project/key Gemini riêng, model và structured output preflight tối đa ba call, quota và chi phí kiểm trên tài khoản, chỉ dùng văn bản công khai. |
| Trước T09/T13 | R4 | Hướng dẫn gán nhãn, family split, protocol và nơi giữ test gold ngoài repo. Giữ chứng cứ và version/hash đủ để tái lập. |
| Trước T15/T16 | Cả nhóm | Máy thứ hai chạy fixture, máy demo local, thông tin đội và minh chứng có quyền sử dụng. Dùng kế hoạch §8 cho mốc và hồ sơ. |

**Gemini chỉ dùng khi cần chạy thật.** Codex đăng nhập ChatGPT là công cụ viết mã. Gemini là model TinChắc gọi khi chạy live. T01/T03/T04 fixture không cần API key. R1 tạo authorization key (auth key) ở [Google AI Studio](https://aistudio.google.com/app/apikey) và giữ riêng, chỉ cung cấp cho tiến trình backend/preflight do R1 chạy. `.env.example` là mẫu tên biến và trần dự kiến. Key thật cần ở ngoài repo/workspace của các agent và ngoài frontend. Khi cần live, R1 truyền biến môi trường từ terminal riêng. Chạy `python -m scripts.preflight --model-check --max-calls 3` sau T05, bằng đúng key, model và một mẫu công khai. Nếu thiếu quota hoặc model, tiếp tục fixture và ghi trạng thái live trong D02.

Kế hoạch dự kiến `gemini-3.5-flash-lite`, app cap 3 USD và tổng tiền 200.000 VND. R1 xác nhận phí/thuế hiển thị, quota và mức nạp trước khi thanh toán. Nếu tài khoản yêu cầu Prepay, tài liệu Google ghi khoản nạp tối thiểu 5 USD hoặc tương đương. Cùng một model đã chốt cho A/B/C. Không dựa vào Gemini free tier để hứa tiến độ hoặc dùng dữ liệu sinh viên. Phần còn lại của stack MVP chạy local, gồm SQLite, OCR, retrieval và demo. [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key) · [Structured output](https://ai.google.dev/gemini-api/docs/structured-output) · [Pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Billing](https://ai.google.dev/gemini-api/docs/billing)

## T01 — Backend và hợp đồng 1.0

T01 chỉ chạy health. Các model nghiệp vụ được xuất vào OpenAPI components;
route assets/checks/sources chưa triển khai. Không có frontend trong task này.
Hợp đồng nằm ở `backend/app/models.py`, examples ở `contracts/examples/`.
`check_result.json` là **CheckRecord** bọc CheckResult; `CheckResult.json` là result bên trong.
Tất cả examples đều mô phỏng. Token trong examples không cấp quyền truy cập thật.

Đã thử trên máy Ubuntu 26.04.1 LTS, Python 3.11.18, Node 22.23.4,
SQLite 3.53.1, uv 0.13.7 (2026-11-09). Python/Node được khóa tại `.python-version` và `.nvmrc`.

```bash
# Từ repo root. uv dùng Python 3.11.18 đã cài.
uv venv --python 3.11.18 .venv
source .venv/bin/activate
uv pip sync requirements.lock.txt
python -m scripts.init_db
python -m pytest backend/tests -q
python -m scripts.export_contracts --check
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# Terminal khác:
curl --fail http://127.0.0.1:8000/api/v1/health
```

`.env.example` đã chứa defaults fixture, không cần tạo `.env` để chạy T01.
Settings parse tất cả biến trong mẫu và che key trong repr. Health không gọi provider;
`provider_configured` chỉ báo key có được cấu hình, không xác nhận key dùng được.
DB được tạo bằng CLI, không tự tạo khi health được gọi. Health kiểm phiên bản DB và
bảng FTS5 TEMP; DB chưa sẵn sàng trả 503 theo ErrorEnvelope. DB chỉ có metadata ở T01.
`corpus_version=fixture-v1` là định danh fixture đóng gói, chưa phải kho nguồn ingest;
mode live/replay chưa có corpus và health trả `corpus_version=unavailable`.

Tạo lại lock khi chủ động cập nhật dependencies:

```bash
uv pip compile requirements.in --python .venv/bin/python -o requirements.lock.txt
uv pip sync requirements.lock.txt
python -m pytest backend/tests -q
python -m scripts.export_contracts
python -m scripts.export_contracts --check
```

`export_contracts` validate tất cả examples trước khi export; `--check` thoát lỗi nếu drift.
OpenAPI sinh từ Pydantic/FastAPI, không chỉnh tay. Nullable fields vẫn phải có mặt;
arrays rỗng vẫn xuất. Schema diễn tả kiểu và bounds; validator quan hệ trường chạy trong Python.
EvidenceRef nhận `context={'chunks': {chunk_id: SourceChunk}}` để kiểm quote/span/version
với text NFC. Kiểm nguồn/scope/thời gian và asset ready/token cần runtime ở task sau;
parse model đơn lẻ không chứng nhận bằng chứng đúng. `checks_passed` fixture chỉ ghi `quote_exact`.

Tài liệu đã đối chiếu: [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/),
[FastAPI metadata/OpenAPI](https://fastapi.tiangolo.com/tutorial/metadata/),
[Vite prerequisites](https://vite.dev/guide/).
Danh sách dependency theo §7.1 gồm cả gói cho task sau, nhưng T01 không import/chạy pipeline đó.
Trước khi phân phối app, chủ repo cần chốt điều kiện giấy phép dependency,
đặc biệt [giấy phép PyMuPDF](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright).

Kết quả T01: `pytest backend/tests -q` đạt **55 passed** sau review (lượt đầu 48 passed).
Health qua uvicorn + curl thật trả HTTP 200. Hai lần export có cùng SHA-256 với bản
trong repo; `--check` pass và thử file drift cố ý trả exit 1 đúng dự kiến.
`uv pip check --python .venv/bin/python` xác nhận 63 packages tương thích.
Chi tiết lệnh và giới hạn kiểm tra: [handoff T01](docs/handoffs/T01.md),
[review T01](docs/handoffs/T01-review.md).

## T04 — Văn bản qua backend fixture

Frontend mặc định gửi HTTP tới FastAPI qua Vite proxy `/api`, giữ banner mô phỏng.
Chỉ các văn bản định danh trong `data/fixtures/cases.jsonl` có kết quả cố định;
không phân tích AI hay gọi URL trong nội dung. Chọn tình huống ở giao diện để điền
văn bản, hoặc dùng nút Điền nội dung mẫu. Lỗi backend hiện riêng, không fallback
sang mock frontend. Mẫu hết hạn thời gian của T03 chỉ có trong mock giao diện;
TTL tài nguyên thật được kiểm riêng bằng backend tests.

```bash
# Terminal 1, từ repo root; mặc định APP_MODE=fixture, một process.
.venv/bin/python -m scripts.init_db
.venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
# Terminal 2, từ repo root:
npm run dev --prefix frontend
# Mở http://127.0.0.1:5173
```

POST trả 202/queued; poll GET nhận CheckRecord với completed/result hoặc
failed/error. Token ngẫu nhiên chỉ giữ trong memory, gửi `X-Resource-Token`;
server lưu SHA-256, token sai/thiếu trả 404. DELETE xóa record và token;
worker không ghi lại sau DELETE/expiry. TTL 24h; dọn mỗi 60 giây hoặc khi thao tác,
hash-only tombstone thêm 24h để đúng token nhận 410, sau đó 404. Restart đánh dấu
job dở JOB_INTERRUPTED, không tự chạy lại. Đây là queue một process cho demo.

```bash
.venv/bin/python -m pytest backend/tests -q
.venv/bin/python -m scripts.export_contracts --check
npm test --prefix frontend
npm run build --prefix frontend
# Browser T03 (mock tường minh, test config tự đặt VITE_API_MODE=mock):
npm run test:browser --prefix frontend
# Browser T04: tự mở FastAPI port 8000 + Vite port 5174, không mở server trùng port.
DATABASE_PATH=/tmp/tinchac-t04-smoke.sqlite3 .venv/bin/python -m scripts.init_db
npm run test:fixture --prefix frontend
```

Playwright cần Chromium đã cài (`cd frontend` rồi `npx playwright install chromium`)
và thư viện hệ thống. Có thể đặt `TINCHAC_CHROMIUM_PATH` để dùng browser riêng.
Ảnh/log smoke sạch token ở `docs/evidence/T04/`; lệnh thực của máy này và giới hạn
ở [handoff T04](docs/handoffs/T04.md), review ở [T04-review](docs/handoffs/T04-review.md).
OpenAPI sinh thêm routes đúng §3.7, giữ nguyên components/schema 1.0/examples.

## T06 — Ảnh và xác nhận chữ

Cài Tesseract hệ thống trên Ubuntu/WSL nếu máy chưa có (pip không cài binary/ngôn ngữ):

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-vie tesseract-ocr-eng fonts-dejavu-core
tesseract --version
tesseract --list-langs
# Phải có vie và eng trước khi thử OCR thật.
.venv/bin/python -m scripts.ocr_smoke
```

Chạy backend/frontend như T04, chọn **Ảnh**, tải PNG/JPEG đã che thông tin cá nhân.
Ảnh tối đa 5 MiB/12 megapixel, được decode thật trước khi tạo asset. Tesseract chạy
cục bộ với `OCR_LANGUAGES=vie+eng`, `OCR_TIMEOUT_SECONDS=20`; ảnh raw được xóa sau
thành công, lỗi hoặc timeout. Preview dùng URL blob của trình duyệt. Token chỉ ở
memory/header; không nằm trong URL. Mỗi server dùng một process, thư mục private
riêng; không dùng nhiều process chung thư mục upload.

Kiểm tra tiền/ngày, sửa chữ, tích đồng ý rồi bấm **Xác nhận chữ và kiểm tra**.
POST check chỉ gửi `confirmed_text` và định danh/capability asset theo CheckCreate;
backend so với chữ OCR để lưu `text_modified` nội bộ. Asset phải ready: nếu OCR
failed/gián đoạn, nhập tay dùng CheckCreate text với hai trường asset null; thông báo
lỗi OCR vẫn hiện. OCR ready nhưng rỗng cho nhập tay rồi gửi image như hợp đồng.

Fixture T04 chỉ hiểu các văn bản định danh, nên thử ảnh
`data/fixtures/ocr/vietnamese-clear.png` (7 triệu), sửa thành 5 triệu để nhận
kết quả supported. Ảnh blurred trả chữ rỗng để thử nhập tay. Các mẫu này là dữ
liệu tổng hợp dev, không phải ảnh sinh viên hay benchmark. Script smoke ghi CER
chưa sửa vào `docs/evidence/T06/ocr-smoke.json`; không trộn số đo có sửa tay.

```bash
.venv/bin/python -m pytest backend/tests/test_ocr_intake.py -q
# Browser OCR + smoke văn bản T04; init DB trước như hướng dẫn T04:
npm run test:fixture --prefix frontend
```

Cách tái hiện, kết quả và giới hạn: [handoff T06](docs/handoffs/T06.md).

## Recovery quickstart — current integrated branch

Current acceptance/state: [progress](docs/progress.md), [recovery audit](reports/recovery_audit.md), [recovery handoff](docs/handoffs/recovery.md). Earlier task sections describe their original checkpoints. D19 delegates technical review/commits to the maintainer; account and human-validation gates remain real.

From repo root with Python3.11 and Node22.12+ (pinned files):

```bash
uv venv --python 3.11.18 .venv
uv pip sync --python .venv/bin/python requirements.lock.txt
npm ci --prefix frontend
npm run build --prefix frontend
APP_MODE=fixture .venv/bin/python -m scripts.init_db
APP_MODE=fixture FRONTEND_DIST=./frontend/dist \
  .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open `http://127.0.0.1:8000`. Built UI and API share one origin; no Vite process is needed. Select a fixture scenario or upload a synthetic OCR image, confirm text and open evidence. `FRONTEND_DIST` is explicit; API/asset misses remain404, private files and paths outside the build are not served. Raw user images stay local and are removed after OCR; deletion is logical, not secure erasure of disks/backups.

```bash
.venv/bin/python -m pytest backend/tests eval/tests -q
.venv/bin/python -m scripts.export_contracts --check
.venv/bin/python -m scripts.validate_corpus
.venv/bin/python -m scripts.validate_eval
npm test --prefix frontend
# Chromium installed according to prior browser instructions:
npm run test:release --prefix frontend
```

Local OCR requires Tesseract vie+eng and the font documented in the OCR scripts. Reproducible dev-only pilot (new directory, never overwritten):

```bash
.venv/bin/python -m scripts.ocr_eval --output data/raw/ocr-dev-new
.venv/bin/python -m scripts.prepare_eval --output data/private/annotation-draft-new
.venv/bin/python -m scripts.collect_sources collect --mode live --enable --dry-run
# Registry listing discovery; dry-run fetches lists, never notice bodies.
```

These commands do not create human gold, approve sources or run Gemini. Live HTTP is now implemented, guarded by `LLM_LIVE_ENABLED=false`. Read [private account setup](docs/live_setup.md) before enabling paid requests. CLI replay is supported for recorded eval runs; HTTP replay is explicitly unavailable until a recording is configured. No paid benchmark or user-study result exists yet. This local smoke was run on the current WSL environment; second-machine validation remains pending in T15.

## Verified DUT source discovery và live refresh

Registry chỉ cho phép hai kênh CTSV/KHTC trên đúng host `dut.udn.vn`; mỗi lượt kiểm robots và liên kết từ trang trường. Không fetch URL người dùng, cổng sinh viên, form hoặc link ngoài registry. Candidate, queue, review và corpus vận hành ở `data/private`, không ghi vào corpus benchmark T09/T13. [Bằng chứng vận hành](docs/evidence/source-sync/operation.json), [báo cáo](reports/source_sync.md), [checkpoint](docs/handoffs/source-sync.md).

Chạy local từ repo root, dependencies đã cài theo README:

```bash
VITE_API_MODE=http npm run build --prefix frontend
# Một lần nếu chưa có active store; không chạy lại khi đã bootstrap.
.venv/bin/python -m scripts.sync_sources bootstrap
# Dùng readiness Free Tier thật, còn hạn24h; key ở file0600 ngoài repo.
.venv/bin/python -m scripts.serve_live \
  --readiness-report docs/evidence/T05/free-tier-owner-authorization-2026-11-10.json
```

Mở `http://127.0.0.1:8000`. Launcher nạp key qua bộ đọc an toàn, không export/source file hoặc in key; dùng **cùng ledger** `data/private/tinchac-live.sqlite3`, model/prompt/budget guard cũ. Chỉ một backend worker. Readiness cũ hơn24h cần xác nhận tài khoản Free Tier thật mới; không sửa timestamp để vượt gate. Không chạy lại preflight đã dùng hết3attempts. Máy khác cần key/readiness hợp lệ của chính chủ tài khoản. Phục vụ live có thể gọi Gemini khi bấm kiểm tra; không bật billing hoặc fallback trả phí.

Scheduler độc lập, không cần root/systemd:

```bash
.venv/bin/python -m scripts.sync_sources start --mode live --enable
.venv/bin/python -m scripts.sync_sources status
.venv/bin/python -m scripts.sync_sources stop
```

`start` tách process khỏi terminal, log `data/private/source-sync/scheduler.log`; `status` kiểm khóa, PID/boot/start identity và tuổi heartbeat. Hai process không thể giữ cùng scheduler lock. Restart giữ `schedule.json`, SQLite backlog, cooldown và lease; process chết đột ngột được phát hiện khi status báo không còn sống. Đây là lifecycle CLI local, chưa có supervisor tự khởi động lại sau WSL/Windows reboot. Muốn chạy lại, dùng `start`; không xóa checkpoint. Đã đo nhiều chu kỳ DUT thật ở60giây, sau đó khôi phục3600giây/poll10giây. Host/WSL phải còn bật; không tuyên bố uptime24/7. Giữ tracked config `enabled=false` để opt-in; process đang vận hành dùng flag `--enable` rõ ràng.

Mỗi lượt mặc định≤40requests/90giây,≤6listing/12notice,≤2MiB HTML,≤1request/giây/host. Retry/robots/redirect/public-DNS/TLS được kiểm tra lại; lỗi một URL có receipt và không xóa corpus. Kiểm thu một lượt hoặc dry-run danh mục:

```bash
.venv/bin/python -m scripts.sync_sources collect --mode live --enable
.venv/bin/python -m scripts.sync_sources collect --mode live --enable --dry-run
```

Chu trình tự động: listing chính thức → candidate immutable → kiểm completeness/privacy/provenance → review agent có bằng chứng → ingest staging → đổi pointer atomic. HTML hoàn chỉnh được phân loại hẹp: tên chương trình được ghi rõ trong ngoặc kép và xuất hiện trong nội dung; fact tên chương trình và một hạn nộp ban đầu có ngày/tháng/năm rõ. Không suy số tiền, điều kiện từng nhóm, năm học từ cohort hoặc quan hệ thay thế. Trường chưa có fact vẫn có thể trả chưa đủ bằng chứng.

Emoji inline đúng mẫu được xem là trang trí; link Google Forms là thao tác đăng ký, **không mở form**. Ảnh nghiệp vụ/PDF/iframe/SVG/background chưa đọc, bảng/danh sách/nguy cơ dữ liệu cá nhân, thông báo thu tiền, gia hạn/đính chính, bản cập nhật và quan hệ programme cũ vẫn chờ review thích hợp. Receipt extractor cũ phải thu lại. Không biến mọi hình/link thành lý do quarantine vĩnh viễn; packet chỉ rõ phần còn thiếu.

`review_policy_path` trỏ tới policy private về căn cứ sử dụng nội bộ. Policy hiện có được maintainer ghi từ xác nhận thật của chủ dự án; không phải giấy phép DUT hay xác nhận human source review. Thiếu xác nhận/căn cứ hợp lệ thì không auto-publish. Người dùng chỉ trả lời câu hỏi về quyền/phạm vi khi cần; maintainer tạo packet, không yêu cầu người dùng viết JSON. Không tái phân phối corpus/raw hoặc lấy danh sách/hồ sơ cá nhân. Phí/scan/đính chính và cập nhật tiền/hạn vẫn giữ gate human thật.

Có thể chạy lại review offline sau khi gate bên ngoài được đáp ứng:

```bash
.venv/bin/python -m scripts.sync_sources review
```

Promotion dùng `corpus_store.publish_reviewed` và ingest cũ; packet/registry hash gắn với manifest. Giữ toàn bộ version/provenance cũ; duplicate canonical không thêm evidence độc lập. Mỗi check pin đúng một runtime từ extraction tới verdict; check mới nhận pointer mới. Snapshot cũ vẫn phục vụ citation sau restart/rollback; chưa tự xóa archive. Corpus benchmark và protocol không thay đổi.

On-demand chỉ từ `Jobs.run_live` khi thiếu nguồn approved cùng scope. Queue lưu **chỉ authority ID cố định**,≤2task, cooldown900giây, lease300giây; không gửi raw text/programme/year/ảnh/điện thoại/URL người dùng tới DUT. Scheduler xử lý bằng cùng collector/review; check đang chạy không chờ web và không bị sửa kết quả sau publish. Source pending không sinh supported giả. Fixture/replay/eval không enqueue hoặc crawl.

Đối soát bằng HTTP thật trên input công khai được phép, mỗi output là thư mục private mới. Lệnh này **gọi Gemini qua app live**; không dùng cho benchmark hoặc lặp để chọn kết quả đẹp:

```bash
.venv/bin/python -m scripts.source_sync_http \
  --output data/private/source-sync/http/NEW_RUN \
  --text 'PHAT_BIEU_CONG_KHAI_DA_DUOC_PHEP'
# Sau publish: thêm --expected-version VERSION_MOI --previous THU_MUC_CHECK_CU.
```

Tool kiểm citation bằng source/chunk/version/quote span thật và so JSON check cũ bất biến. Failed provider vẫn là lỗi kỹ thuật, không có verdict. Capabilities nằm private0600, không commit/push hoặc chép vào báo cáo.

Rollback offline, lấy version từ `data/private/live-corpus/active.json` hoặc snapshot cũ:

```bash
.venv/bin/python -m scripts.sync_sources rollback --version corpus-64_HEX_THUC_TE
```

Kiểm hồi quy:

```bash
.venv/bin/python -m pytest backend/tests eval/tests -q
.venv/bin/python -m scripts.export_contracts --check
.venv/bin/python -m scripts.validate_corpus
npm test --prefix frontend
VITE_API_MODE=http npm run build --prefix frontend
```

Các receipt ghi rõ phần DUT/Gemini thật và phần synthetic fault/concurrency/security tests. Full12case live QA và các gate nghiên cứu T02/T08–T15 là phạm vi khác, không được đóng nhờ một smoke nguồn mới.
