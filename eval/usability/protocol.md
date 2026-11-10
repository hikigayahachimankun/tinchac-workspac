# Quy trình T14 v1 — chưa tiến hành khảo sát

Mục tiêu thăm dò: sinh viên có hiểu bằng chứng và chọn bước tiếp theo phù hợp không. Người là đơn vị phân tích; 48 lượt không phải 48 người. Mục tiêu 12 sinh viên DUT tự nguyện, từ đủ 18 tuổi, mỗi người khoảng 15–20 phút. Không có thù lao/ngân sách mới trong phiên kỹ thuật này. Địa điểm dự kiến: cùng người điều phối trên máy cục bộ; không dùng biểu mẫu cloud, không thu liên hệ qua CLI.

## Tuyển và quyền tham gia

Chưa có quyền liên hệ người thật; agent không gửi lời mời. Sau khi có quyền đăng tại một kênh sinh viên hoặc có người tự nguyện chủ động đến, người điều phối có thể dùng nguyên văn lời mời sau. Không tự lấy danh sách lớp, nhắn tin hàng loạt hay suy đồng ý từ tham dự.

> Mời sinh viên DUT từ đủ 18 tuổi tự nguyện thử demo TinChắc khoảng 15–20 phút. Bạn sẽ làm 4 tình huống giả lập về học bổng/đóng tiền, không giao dịch thật. Demo có thể sai. Không thu tên, tài khoản, OTP hay ảnh cá nhân. Có thể từ chối, bỏ câu hỏi, dừng hoặc yêu cầu xóa dữ liệu bằng mã phiên; việc tham gia không ảnh hưởng quyền lợi học tập. Chỉ công bố số tổng hợp. Nếu muốn tham gia hoặc hỏi thêm, trao đổi trực tiếp với người điều phối ở buổi thử được phép tổ chức.

Người điều phối giải thích, trả lời câu hỏi rồi mới chạy form. Nội dung consent chính xác, có version/hash, ở `scripts/user_pilot.py::CONSENT`. Người tham gia tự chọn `yes`; chọn khác không thu câu trả lời. `yes` cũng tự xác nhận sinh viên DUT từ đủ 18 tuổi. Không lưu tên người consent. Không ghi âm, quay màn hình, chụp người/thiết bị cá nhân. Consent không cho phép công khai ảnh, tin nhắn hay trích nguyên văn lời nói. Chỉ dùng 4 input công khai có sẵn; ca cá nhân không thuộc pilot này.

## Gate trước buổi thử

1. `python -m scripts.user_pilot validate-allocation` phải đạt 12/48; giữ nguyên `allocation.csv`, không đổi phân bổ theo kết quả hoặc thay người sau khi xem kết quả. ID U01–U12 chỉ là slot, không là người đã tuyển. Từ chối/withdraw giữ slot, báo thiếu mẫu; không tái dùng ID.
2. Chọn **một build** TinChắc hỗ trợ đúng cả bốn input ở `tasks.json`. Fixture hiện chỉ có một family Minh Họa nên không đạt gate bốn family. Không thay task bằng bốn biến thể cùng family, không coi replay/synthetic là live. Với replay, phải có bản ghi public được phép sử dụng, cùng build và thời điểm/snapshot được nêu rõ; endpoint replay hiện chưa sẵn.
3. T10/T12 phải có QA cho **build và toàn bộ task được chọn** (đường văn bản, bằng chứng, lỗi kỹ thuật/privacy). Handoff có kiểm fixture lịch sử chưa chứng minh live hiện tại đủ điều kiện. Không gọi provider để lấp gate trong T14.
4. Định trước đáp án **hành động** từ nguồn phù hợp với scope/thời điểm, không lấy output model/benchmark làm đáp án. Agent đã chuẩn bị `action_key.draft.json` có version/hash/quote nguồn để R3/R4 kiểm rubric, ghi căn cứ ở readiness riêng. Đây là agent self-review, chưa là đánh giá độc lập của con người. Cho phép nhiều hành động hợp lý bằng `accepted_actions`, không chấm ý kiến bất đồng thành sai. Các mã hợp lệ ở `ACTIONS`. Dự thảo chấp nhận cả ba lựa chọn xác minh/đợi vì câu hỏi hiện rộng; chỉ đo chọn bước an toàn, không phân biệt mức giải quyết chi tiết và có nguy cơ ceiling effect. Cần chốt cách hỏi/rubric **trước** khóa; nếu đổi vật liệu thì tạo version mới và kiểm lại phân bổ, không ép một đáp án tùy ý để tạo hiệu quả.
5. Copy `readiness.blank.json` vào `data/private/`, ghi build, đường dẫn evidence QA, cơ sở review và action key. Chỉ đặt cờ true khi việc tương ứng đã diễn ra. Không cần owner duyệt thay đổi kỹ thuật; không giả danh người review hay điền cờ từ rehearsal. Khóa bằng `init` bên dưới. Đây là khai báo có nguồn của người điều phối, không phải chứng thư QA tự xác minh bằng mật mã.

Không cần tạo bản ghi khảo sát thật trống để tuyên bố sẵn sàng. Template chưa đủ gate phải bị từ chối, không tạo workspace. Thay build/câu chữ/rubric sau khóa phải mở pilot version riêng; không gộp chênh lệch giữa hai build thành hiệu quả UI. Không thay model/schema/test hoặc run benchmark trong T14.

## Chạy form cục bộ

Chạy từ root repo bằng terminal Linux/WSL Python 3.11. Không chạy `collect` qua CI, tool chat, ghi log terminal hay chia sẻ màn hình ra dịch vụ. Chỉ một người điều phối dùng workspace; khóa OS chặn hai phiên cùng lúc.

```bash
.venv/bin/python -m scripts.user_pilot validate-allocation
.venv/bin/python -m scripts.user_pilot init --readiness data/private/pilot-readiness.json --work data/private/user_pilot
.venv/bin/python -m scripts.user_pilot collect --work data/private/user_pilot --participant U01
.venv/bin/python -m scripts.user_pilot summary --work data/private/user_pilot
.venv/bin/python -m scripts.user_pilot withdraw --work data/private/user_pilot --participant U01
```

Form consent → `start` → lộ input + chạy đồng hồ monotonic → chọn mã hành động → nêu chi tiết cần kiểm/bằng chứng. Hai trường cuối dùng cùng deadline **180 giây**, không reset khi nhập sai. Chỉ hành động giả định; không đăng nhập/thanh toán/liên hệ người gửi. Manual: tra kênh chính thức theo cách thường dùng, không mở TinChắc. TinChắc: dùng đúng build/mode đã khóa. Thời gian bao gồm tra cứu và nhập câu trả lời; không trừ thời gian chờ API. `technical_error` ghi lỗi kỹ thuật, không ghi nhãn `insufficient_evidence`.

Hết giờ lưu `timeout`, 180 giây, chưa hoàn thành, hành động đúng = false; vẫn ở mẫu số. `skip` bỏ câu hỏi hành động, giữ lượt/thời gian thực và chưa đúng. Nhập `stop` để dừng ngay tại bất kỳ câu hỏi, `withdraw` để xóa nội dung phiên. Ctrl-C trong lượt giữ lượt đã bắt đầu ở trạng thái dừng; Ctrl-C ở phần nhận xét không đổi thời gian/hành động đã hoàn thành. Nếu tiến trình chết, lượt đã bắt đầu còn `interrupted`, thời gian chưa biết; không điền 0 thành thời gian thực hoặc tự chạy lại cùng người để có số đẹp. Lượt chưa bắt đầu không được điền kết quả.

Sau mỗi lượt, dừng đồng hồ rồi ghi số nguồn **thực sự mở** (blank nếu không biết, 0 chỉ khi thật sự không mở) và nhận xét tự do, kể cả trái chiều. Người điều phối không giải thích đúng/sai hoặc gợi hành động giữa các lượt. Sau cả bốn lượt, mới hỏi cách hiểu nhãn ở các lượt TinChắc hoàn thành, trước khi giải thích; nhắc lại input, ghi nhãn thực sự đã thấy từ màn hình/bản ghi cục bộ, không suy nhãn từ gold. Blank = bỏ câu hỏi. Không có nhãn khi lỗi API. Đo này là hồi tưởng có lựa chọn sau phiên, có thể có recall bias; không tuyên bố đo tự nhiên đầy đủ. Các câu hỏi mở T10 ở `docs/handoffs/T10-questions.md` dùng sau primary tasks. Đặc biệt hỏi NEI, hết hạn, lỗi kỹ thuật; ghi nguyên ý trái chiều trong dữ liệu riêng, không sửa để khớp kỳ vọng.

## Lưu và rút consent

`data/private/user_pilot/manifest.json` khóa tasks/allocation/readiness/consent và hash mã collector/scorer, SHA-256 phát hiện thay đổi vô ý (không chống người cố ý sửa cả hash). Dùng lại đúng version mã đã khóa khi tổng hợp; không nới guard để trộn version. `sessions/Uxx.json` là dữ liệu gốc có consent, status, số nguồn, bằng chứng và hiểu nhãn; mỗi bước ghi atomic. `user_pilot.csv` là bản dẫn xuất đúng bảy cột, duration tính bằng giây; interrupted chưa biết thời gian lưu JSON null/CSV trống, không phải 0 giây. `summary` tái sinh CSV khi cần. Không nối với bản CSV cũ có schema khác. Dấu bắt đầu công thức trong comments CSV được thêm apostrophe; JSON giữ nguyên nhận xét.

Tệp thật chỉ được tạo dưới `data/private/` đã Git-ignore; quyền thư mục 0700, tệp 0600. Không backup vào cloud/AI, không `git add -f`, không in nội dung dữ liệu thật vào chat/log CI. Git-ignore và Unix permissions không phải mã hóa; chỉ điều phối viên dùng máy riêng được khóa. `withdraw` bỏ consent, câu trả lời, bằng chứng, nhận xét khỏi cả JSON và CSV, giữ tombstone chỉ ID/trạng thái để không tái dùng slot. Nếu đã tự sao chép/export tệp riêng, phải xóa cả các bản sao; Git/CLI không quản lý bản sao ngoài workspace. Không thể rút từng dòng khỏi số đã tổng hợp không truy ngược.

Mốc giữ dữ liệu thô: xóa trước **22/12/2026 giờ Việt Nam**, hoặc ngay khi có yêu cầu hợp lệ bằng mã Uxx. Điều phối viên chịu trách nhiệm xóa workspace/bản sao riêng tại mốc này, chỉ giữ báo cáo tổng hợp đã rà riêng tư; không có cron tự chạy hoặc lời hứa đã xóa dữ liệu chưa thu.

## Tổng hợp và quyết định UI

`summary` chỉ in số tổng hợp, không in ID/nhận xét/bằng chứng. Kiểm n consented, declined, withdrawn, người dừng, số lượt quan sát/hoàn thành, timeout/lỗi, family/condition và các mẫu số. Action rate theo điều kiện = số đúng / mọi lượt đã bắt đầu; lỗi kỹ thuật/timeout/dừng không thành thành công. Thời gian giữ timeout=180; interrupted báo riêng và loại khỏi duration do không biết thời gian. Report n và mẫu số ngay cạnh tỷ lệ.

Mỗi người đủ 4 lượt không bị stop/interrupted: tính tỷ lệ hành động đúng trong 2 lượt mỗi điều kiện, chênh lệch TinChắc − manual, và chênh lệch thời gian trung bình mỗi điều kiện. Báo **median của chênh lệch theo người**. Timeout/lỗi vẫn tính trong cặp nếu đủ 4 lượt; người chỉ làm một phần chỉ bị loại khỏi cặp, vẫn ở tổng quan sát. Tỷ lệ gộp các lượt chỉ là mô tả, không dùng 48 làm đơn vị độc lập. Hiểu nhãn: số câu chọn nghĩa đúng / số lượt TinChắc đã thấy nhãn; báo riêng số không thấy/không trả lời, không suy đoán nhãn model đúng chỉ vì người hiểu nhãn.

Nếu n < 12 ghi **pilot nhỏ, mẫu thuận tiện**, không khẳng định quan hệ nhân quả hay đại diện sinh viên DUT. Chưa có dữ liệu = chưa tính hiệu quả, không thay null bằng 0%. Review tối đa ba ca hiểu sai nhãn **thật**, chọn theo thứ tự thu đầu tiên và mô tả scope/nhầm lẫn/bước tiếp theo bằng diễn giải tổng hợp đã rà riêng tư; nếu có ít hơn ba ghi đúng số. Không công khai raw quote/case cá nhân mặc định. Sửa copy chỉ khi có evidence ID riêng và căn cứ quan sát/ý kiến rõ; chụp/kiểm UI theo `docs/ui-brief.md`. Logic model cần decision, version/run mới theo protocol, không sửa benchmark freeze.

## Rehearsal kỹ thuật

```bash
.venv/bin/python -m scripts.user_pilot rehearse --work /tmp/tinchac-T14-synthetic
.venv/bin/python -m scripts.user_pilot summary --work /tmp/tinchac-T14-synthetic
.venv/bin/python -m pytest eval/tests/test_user_pilot.py -q
```

Output phải ở thư mục mới; không ghi đè. Rehearsal dùng chính collector với input/clock synthetic, không mở UI/provider và không chứng minh usability. Mọi số của rehearsal ghi rõ synthetic, `actual_real_participants=0`. Không import vào dữ liệu thật hoặc điền báo cáo kết quả người dùng.
