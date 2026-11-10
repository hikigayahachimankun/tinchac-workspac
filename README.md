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

Feature vận hành riêng với benchmark, tắt mặc định. [Báo cáo thật](reports/source_sync.md), [kế hoạch/audit](docs/superpowers/plans/2026-11-10-verified-source-sync.md), [handoff](docs/handoffs/source-sync.md). Không đổi T09/T13, corpus đã khóa, API1.0 hoặc nhãn. Candidate chưa duyệt không được dùng làm bằng chứng; chạy collector không đồng nghĩa corpus đã cập nhật.

`config/source_authorities.json` đăng ký đúng host/path của CTSV và KHTC. Mỗi lượt đối chiếu link từ trang trường; không mở subdomain khác, cổng SV, form hoặc URL người dùng. Listing CTSV có kênh alias `/Phong/Sinhvien`; redirect chỉ theo tối đa2hop, cùng authority và đúng registry/robots. Tốc độ≤1request/giây,40requests/90giây/lượt mặc định; tối đa6listing/12notice,2MiB/response. Khi robots/403/backoff/giới hạn chặn, receipt ghi lý do. Không fetch attachment tự động; PDF/ảnh/link chưa đọc giữ quarantine.

Chạy tại repo root với dependencies hiện có, không key:

```bash
# Chỉ tìm link: vẫn có network tới robots/trang trường/listing, không tải notice.
.venv/bin/python -m scripts.collect_sources collect --mode live --enable --dry-run
# Thu incremental, tự resume backlog và nhận ETag/Last-Modified nếu có.
.venv/bin/python -m scripts.collect_sources collect --mode live --enable
.venv/bin/python -m scripts.sync_sources status
```

`--state` mặc định `data/private/source-sync`, `--store` mặc định `data/private/live-corpus`. Giữ các process cùng state/store, một worker. Thư mục trong repo phải nằm dưới `data/private`; có thể chọn thư mục private ngoài repo. State SQLite, candidate text/HTML đã làm sạch, review queue và receipts đều local/ignored. Không lưu transport HTML hoặc ảnh nhúng; receipt có hash. Không commit/push các thư mục này. Screen PII bảo thủ không thay việc đọc kiểm; không OCR/tải danh sách cá nhân. `config/source_candidates.json` và các receipt recovery cũ là lịch sử; CLI cũ `--output data/raw/...` được thay bằng `--state` private và enable live tường minh.

Lịch độc lập với FastAPI:

```bash
.venv/bin/python -m scripts.sync_sources daemon --mode live --enable
```

`config/source_sync.json`: `enabled=false`, interval3600giây, poll queue10giây; `--enable` bật cho process này. Terminal phải còn chạy; Ctrl-C dừng, restart giữ cadence/checkpoint. Có thể để local supervisor gọi đúng lệnh này với working directory repo; không cần Redis/Celery hoặc GitHub Actions. **Phiên triển khai chưa cài/bật service thường trực**; user systemd tại môi trường này báo `offline`. Không chạy khi máy/WSL tắt. `scheduler.json` là receipt, không chứng minh process còn sống. Không coi dry-run là đã đồng bộ.

Để live app nhận các lần publish, bootstrap store từ nguồn hiện đã duyệt rồi cấu hình cùng store:

```bash
# Một lần, offline; giữ nguyên data/corpus và trạng thái review hiện có.
.venv/bin/python -m scripts.sync_sources bootstrap
# Thêm vào cấu hình local của process live (các gate LLM trước đây vẫn áp dụng):
# SOURCE_SYNC_STORE=./data/private/live-corpus
# SOURCE_SYNC_STATE=./data/private/source-sync
# SOURCE_LOOKUP_ENABLED=true
```

On-demand chỉ chạy trong `Jobs.run_live` khi thiếu nguồn approved cùng scope, trước khi cắt context. Nó lưu **chỉ ID authority cố định**, không lưu/gửi raw message, scope, ảnh, số điện thoại hoặc URL. Mỗi unit gộp thành một task, queue≤2, cooldown900giây, lease300giây. Daemon mới xử lý network; không giữ request kiểm chứng chờ crawler. Nguồn chưa duyệt không tạo S/C; warning hiện qua UI sẵn có. Kết quả cũ không bị sửa. Fixture/replay/eval không enqueue/crawl, kể cả khi cấu hình on-demand bật.

Promotion cần review thực tế:

1. Đọc candidate `receipt.json`/`text.txt`, xem phần thiếu và quyền sử dụng nội bộ. Agent review ghi đúng danh tính agent. Phí/đính chính, attachment/scan/link ngoài và cập nhật tiền/hạn cần bằng chứng review con người thật; không điền một danh tính giả để vượt gate.
2. Chuẩn bị private `reviewed-sources.json` theo SourceVersion1.0 và `reviewed-register.json` theo `config/sources.yaml`. Bắt đầu bằng **toàn bộ** sources/register của active snapshot, thêm versions mới, giữ nguyên records cũ. Dùng source_id theo canonical URL/hash text, quote/span chính xác, available_basis=first_seen và available_at=retrieved_at không sớm hơn candidate.first_seen. Giữ family đã có; không suy supersedes từ lần tải mới.
3. Copy `config/source_review.example.json` vào private, chỉ tạo packet cho versions mới. Từng gate phải có bằng chứng và passed=true sau kiểm thực tế; bind SHA256 receipt/text. Mọi gate mặc định false. PDF text dùng `scripts.ingest_sources.extract_pdf`; scan dùng OCR local hiện có hỗ trợ đọc kiểm và `manual_pdf`/page spans/manual_text/hash, không tự chứng nhận OCR. Attachment phải có parent DUT, canonical URL có trong receipt và file local/hash đã được kiểm. Nếu không được phép đọc đủ hoặc có danh sách cá nhân, giữ quarantine.
4. Paths raw/manual/reviewed_files trong register/packet phải nằm trong repo private, có hash chính xác. Gate content_use chỉ xác nhận phạm vi sử dụng đã có quyền, không tự cấp giấy phép tái phân phối. Nguồn trùng text khác URL cần giải quyết canonical/family, không index như bằng chứng độc lập.

```bash
.venv/bin/python -m scripts.sync_sources publish \
  --snapshot data/private/reviewed-sources.json \
  --register data/private/reviewed-register.json \
  --reviews data/private/source-reviews.json
```

Publish dùng ingest cũ để dựng staging, validate/index, lưu review trong provenance gắn manifest hash, fsync rồi đổi `active.json` atomic. Không sửa thư mục đang phục vụ; mỗi job giữ một runtime đến cuối, job mới nhận snapshot mới. Lỗi build/publish giữ active trước. Giữ snapshots cũ để citation còn mở sau restart/rollback; chưa có tự xóa archive. `bootstrap` chỉ chuyển seed cũ vào store, không bổ sung nguồn đã duyệt.

Rollback không mạng, không sửa benchmark:

```bash
# Lấy previous/corpus_version từ data/private/live-corpus/active.json.
.venv/bin/python -m scripts.sync_sources rollback --version corpus-REPLACE_WITH_64_HEX
```

Kiểm offline riêng feature:

```bash
.venv/bin/python -m pytest backend/tests/test_source_sync.py backend/tests/test_source_publication.py -q
```
