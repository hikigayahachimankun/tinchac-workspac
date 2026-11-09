# TinChắc fixture UI (T03)

Node 22.23.4 theo `.nvmrc` ở root. Từ root repo:

```bash
cd frontend
npm ci
npm run dev
npm test
npm run build
# Chỉ cần khi máy chưa có Chromium cho Playwright:
npx playwright install chromium
npm run test:browser
```

Mở http://127.0.0.1:5173. Bấm “Điền nội dung mẫu”, xác nhận đã che thông tin cá nhân rồi “Kiểm tra mô phỏng”. Mở “Tình huống mô phỏng” để chọn ba nhãn, NEI, trạng thái hết hạn hoặc lỗi. Kết quả cố định theo lựa chọn, không phân tích văn bản nhập.

Không gọi backend, OCR hoặc Gemini; không lưu nội dung vào storage. Vite đã có proxy `/api` tới localhost:8000 để task sau dùng, nhưng T03 không có HTTP client thật.

`src/api/types.ts` sinh bằng `npm run types:generate` từ `../contracts/openapi.json`. Không sửa tay types hoặc enum. Upstream T01 hiện chỉ có trong workspace, **chưa có trong lịch sử commit nhánh T03** (kiểm đầu phiên: HEAD `5f65546`). UI chờ chủ repo review cùng blocker upstream.

Mock nhập trực tiếp CheckCreated/check_result/SourcePublic/error từ `contracts/examples`. `src/api/scenarios.json` là fixture UI mở rộng từ các example đó, đã validate với Pydantic T01; không phải nguồn hay gold thật. Tình huống hết hạn chỉ minh họa `temporal_status` riêng, không bịa deadline từ snapshot tiền.

Bàn giao client cho T04: `ApiClient` trong `src/api/client.ts` có `createCheck(CheckCreate)`, `getCheck(checkId, token)`, `getSource(versionId)`. Khi nối API thật, token nằm trong memory và header `X-Resource-Token`, không dùng query string. `pollCheck` kiểm trạng thái mỗi 1,5 giây và ngừng sau 120 giây; nút kiểm tra lại tiếp tục cùng check, không tự POST mới. `ApiError` giữ ErrorDetail; failed worker và lỗi request đều là màn lỗi kỹ thuật, completed NEI vẫn là kết quả.

T04 cần bổ sung fetch/runtime validation và thử lỗi HTTP/worker thật sau khi upstream được chốt; T03 không triển khai việc đó. Không có upload ảnh; tab Ảnh vô hiệu hóa có giải thích, kiểm lỗi OCR thuộc T06.

Trên Linux thiếu thư viện hệ thống cho Chromium, dùng `npx playwright install-deps chromium` trên máy có quyền cài package. Phiên triển khai này dùng Chromium for Testing v158.0.8127.18 trong `/tmp/tinchac-chrome/` và thư viện giải nén cục bộ, không cài hệ thống. Có thể chọn browser có sẵn bằng biến `TINCHAC_CHROMIUM_PATH`; mặc định Playwright dùng browser đã cài qua lệnh ở trên.
