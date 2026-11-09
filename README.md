# TinChắc · Workspace cho Codex và VS Code

Gói chuẩn bị repo, quy tắc làm việc, checkpoint và bốn skill đã ghim phiên bản. Đặc tả gốc nằm tại [TINCHAC_PROJECT_PLAN.md](TINCHAC_PROJECT_PLAN.md). T00 xác nhận đầu vào của nhóm. T01 tạo API/schema và bộ khung. T03 tạo frontend. Các lệnh của app trong §7.1 chỉ dùng sau khi task tương ứng đã tạo tệp.

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
