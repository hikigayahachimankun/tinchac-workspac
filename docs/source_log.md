# Sổ nguồn T02

Nhánh `task/T02-seed-sources`; thu ngày 09/11/2026. 6 ứng viên / 6 family: **5 approved** (4 học bổng, 1 phí/gia hạn), **1 quarantined** (thạc sĩ). `approved` là agent đã đọc/đối chiếu nội dung trong phạm vi nêu dưới; chưa phải chủ repo đã review hoặc giấy phép phân phối.

## Cách lưu và giới hạn

- `data/corpus/sources.json`: JSON array SourceVersion 1.0 gồm cả quarantine; downstream T07 phải lọc approved. `data/fixtures/sources.jsonl` chỉ có Minh Họa giả lập; không phải DUT.
- HTML trích `.wd-content-detail`, bỏ h2/ngày/badge; PDF scan đã xem từng trang và chép lại các mục nghiệp vụ trong `*.verified.txt`, bỏ đầu trang/chữ ký/nơi nhận và thông tin liên hệ hành chính. Đây là bản trích có chủ đích, không phải raw PDF hoặc bản OCR nguyên trạng. Quote/span/hash áp dụng đúng text lưu trong corpus.
- `content_sha256` = SHA-256 UTF-8 text NFC/LF. ID nguồn = `dut_` + 16 ký tự đầu SHA-256 canonical URL; version = source_id + 16 ký tự đầu hash text. Không có quan hệ supersedes đã xác nhận; các family học bổng giữ xuyên năm để T09 đánh giá leakage.
- Ngày công bố lưu precision=date; giờ HTML khác giữa các view nên không dùng làm giờ khả dụng. `available_basis=first_seen`, `available_at=retrieved_at` vì chưa xác minh lịch sử sửa trang. Không dùng snapshot này như bằng chứng có sẵn trước lần thu.
- Mọi nguồn có bản quyền DUT; chưa thấy giấy phép mở/cho phép tái phân phối trong thông báo. Truy cập công khai không phải quyền sao chép/phát hành. Chỉ lưu để chủ repo xem xét/nghiên cứu nội bộ; **chưa được duyệt xuất bản corpus/raw**. Quyền khai thác tiếp cần chủ repo chốt; không gán CC hoặc public domain.
- Raw và bản render nằm trong `data/raw/t02/` được gitignore. Không truy cập form đăng ký, cổng sinh viên hay tra cứu thanh toán cá nhân. Biểu mẫu Agribank đọc được là mẫu trống, không có hồ sơ điền.
- Google Drive connector trả text rỗng cho các PDF scan; đã tải qua connector, render bằng PyMuPDF, xem ảnh từng trang nghiệp vụ, OCR vie+eng chỉ hỗ trợ chép, không lấy OCR làm fact tự động. Preview vô danh của cả ba PDF trả HTTP 200, không chuyển đăng nhập; không suy quyền phân phối từ việc đó.

## Nguồn và checksum

### DUT 12395 — approved

- Thông báo gốc: https://dut.udn.vn/Phong/CTSV/Thongbao/id/12395
- Canonical nội dung: https://dut.udn.vn/Phong/CTSV/Thongbao/id/12395
- Đơn vị: Trường Đại học Bách khoa - Đại học Đà Nẵng / Phòng Công tác Sinh viên
- source/version/family: `dut_be8a0080c11e660f` / `dut_be8a0080c11e660f_f0ef96bab2007bb9` / `agribank`
- Ngày công bố nội dung: 2026-11-07 (date). Thu HTML: 2026-11-09T13:09:10.052838+00:00; thu nội dung canonical: 2026-11-09T13:09:10.052838+00:00.
- Hash text: `f0ef96bab2007bb962a3152ac3a4090889737570317d2da406295fc9e6c0232c`
- Raw HTML: `data/raw/t02/12395.html`; SHA-256 `a39e0cfbe4210a16c297033a19a013ee4456a5f945eb9517ba88053d4e221e04`
- Attachment: https://docs.google.com/document/d/17exz6WD3BS_r8Qeiszhya_8a_sUeyz0q/edit?usp=sharing&ouid=112054809668127454802&rtpof=true&sd=true
- Quyền: công khai để đọc; giấy phép tái phân phối chưa xác nhận; chỉ nội bộ như quy tắc trên.
- Đối soát: Đã đọc đầy đủ HTML và biểu mẫu Agribank trống (DOCX qua connector). 5.000.000 VND/suất; SV chính quy hoàn cảnh khó khăn, học tập/rèn luyện 2025–2026 từ Khá, hoạt động cộng đồng, chưa nhận hỗ trợ ngoài ngân sách. Nhận hồ sơ 14–16h ngày 09 và 10/11/2026; deadline 10/11 lúc 16h. Link forms chỉ ghi nhận, không mở/điền.
- Quote `award_amount` [482,502): “5.000.000 đồng/suất.”
- Quote `deadline` [963,1043): “Thời gian: Từ 14h00 đến 16h00, ngày 09/11/2026 (thứ Hai) và 10/11/2026 (thứ Ba).”
- Quote `eligibility` [503,790): “- Đối tượng: Sinh viên hệ chính quy có hoàn cảnh gia đình khó khăn, kết quả học tập và rèn luyện năm học 2025–2026 đạt từ loại Khá trở lên, tích cực tham gia hoạt động tình nguyện, vì cộng đồng và chưa nhận học bổng hoặc khoản hỗ trợ ngoài ngân sách khác tính đến thời điểm xét học bổng.”

### DUT 12394 — approved

- Thông báo gốc: https://dut.udn.vn/TrangSinhvien/Thongbao/id/12394
- Canonical nội dung: https://dut.udn.vn/TrangSinhvien/Thongbao/id/12394
- Đơn vị: Trường Đại học Bách khoa - Đại học Đà Nẵng / Phòng Công tác Sinh viên
- source/version/family: `dut_2a0b90b19b67872f` / `dut_2a0b90b19b67872f_dbd836ad6b4251a7` / `keidanren_jcci`
- Ngày công bố nội dung: 2026-11-05 (date). Thu HTML: 2026-11-09T13:09:23.984576+00:00; thu nội dung canonical: 2026-11-09T13:09:23.984576+00:00.
- Hash text: `dbd836ad6b4251a7b391f150042b3c463a84a94a7dd1ca01fdc30383ac18fece`
- Raw HTML: `data/raw/t02/12394.html`; SHA-256 `d77eb3bdadb3fe51582357dcc05ab65f13038b3a429de8f58caf185c0346c84d`
- Attachment: Không có.
- Quyền: công khai để đọc; giấy phép tái phân phối chưa xác nhận; chỉ nội bộ như quy tắc trên.
- Đối soát: Đã đọc đầy đủ HTML; không có attachment nghiệp vụ. 03 suất, 7.000.000 VND/suất; sinh viên đại học mọi ngành có khả năng và chứng chỉ tiếng Nhật, học tập tốt/hoạt động cộng đồng; ưu tiên khó khăn/hợp tác quốc tế. Nhận hồ sơ 08–11h từ 10 đến hết 12/11/2026; deadline 12/11 lúc 11h. Không gán deadline 23:59.
- Quote `award_amount` [306,326): “7.000.000 đồng/suất.”
- Quote `deadline` [1452,1530): “Thời gian: Từ 08h00 đến 11h00, các ngày từ 10/11/2026 đến hết ngày 12/11/2026.”
- Quote `eligibility` [359,471): “- Sinh viên bậc đại học thuộc bất kỳ ngành học nào.
- Có khả năng sử dụng tiếng Nhật và có chứng chỉ tiếng Nhật.”

### DUT 12321 — approved

- Thông báo gốc: https://dut.udn.vn/Phong/CTSV/Thongbao/id/12321
- Canonical nội dung: https://dut.udn.vn/Phong/CTSV/Thongbao/id/12321
- Đơn vị: Trường Đại học Bách khoa - Đại học Đà Nẵng / Phòng Công tác Sinh viên
- source/version/family: `dut_09fb9c92c9ab7b2f` / `dut_09fb9c92c9ab7b2f_e5e4f9b141b646e6` / `schneider`
- Ngày công bố nội dung: 2026-10-06 (date). Thu HTML: 2026-11-09T13:09:51.086419+00:00; thu nội dung canonical: 2026-11-09T13:09:51.086419+00:00.
- Hash text: `e5e4f9b141b646e668b29d17204614ffe7569b6a9d28ac4ee487513506453f95`
- Raw HTML: `data/raw/t02/12321.html`; SHA-256 `1fe4a3fdfc09a7b4473288e5c1ef5d1a1fd1a19c8a850e83623dd766b9d5a04f`
- Attachment: Không có.
- Quyền: công khai để đọc; giấy phép tái phân phối chưa xác nhận; chỉ nội bộ như quy tắc trên.
- Đối soát: Đã đọc đầy đủ HTML; không có attachment nghiệp vụ. 10 suất, 5.000.000 VND/suất; sinh viên năm 3–5 Khoa Điện. Nhận hồ sơ 08–16:30 ngày 16/10/2026. Đây là nguồn cũ đã qua hạn; không đổi nhãn nguồn vì hết hạn.
- Quote `award_amount` [455,474): “5.000.000 đồng/suất”
- Quote `deadline` [534,674): “🔹 Thời gian tiếp nhận hồ sơ: Từ 8h00 đến 16h30, ngày 16/10/2026 tại Phòng Công tác Sinh viên (Phòng S06.08) gặp chuyên viên Đới Phương Thanh”
- Quote `eligibility` [278,423): “🔹 Đối tượng: Sinh viên năm 3 đến năm 5 tại Khoa Điện, đáp ứng các tiêu chí về học tập, hoạt động học thuật, ngoại khóa và định hướng nghề nghiệp.”

### DUT 12327 — approved

- Thông báo gốc: https://dut.udn.vn/Phong/CTSV/Thongbao/id/12327
- Canonical nội dung: https://drive.google.com/file/d/1fMZ6as3DNjI3WwLJ_wAFnehvKHgRC2M-/view
- Đơn vị: Trường Đại học Bách khoa - Đại học Đà Nẵng / Phòng Công tác Sinh viên
- source/version/family: `dut_344b21e393855658` / `dut_344b21e393855658_921795aab925d271` / `toyota`
- Ngày công bố nội dung: 2026-10-06 (date). Thu HTML: 2026-11-09T13:09:48.220000+00:00; thu nội dung canonical: 2026-11-09T13:11:05.702010+00:00.
- Hash text: `921795aab925d271910da89d908e238589015ddf90834e1687665e0663418553`
- Raw HTML: `data/raw/t02/12327.html`; SHA-256 `098ccc2cc326d40c1adf741c6d1ec3a91c05ce1b9f51450a149079c8e58e432e`
- Attachment: https://drive.google.com/file/d/1fMZ6as3DNjI3WwLJ_wAFnehvKHgRC2M-/view?usp=sharing
- Quyền: công khai để đọc; giấy phép tái phân phối chưa xác nhận; chỉ nội bộ như quy tắc trên.
- Đối soát: Đã đọc HTML và cả 2 trang PDF 5469/TB-ĐHBK, ngày 06/10/2026 (ngày trang là 07/10). Trang 1: Đồng hành 01 suất 25.000.000; Tiếp sức 09 suất 6.000.000, 08 cho Ô tô/Cơ khí, 01 Môi trường. Scope riêng từng loại trong facts: Tiếp sức 2 năm cuối, GPA >=8/10 hoặc >=3,2/4, rèn luyện Tốt; Đồng hành GPA cao nhất trong nhóm trường đề xuất, có ưu tiên khi bằng điểm. Trang 2: nhận 08:00–11:30 ngày 13/10/2026. Không dùng giá trị Đồng hành cho Tiếp sức.
- Raw PDF: `data/raw/t02/12327.pdf`, SHA-256 `2161224fe24a88badeeb0fa8c8be056c26a51c17117e8fd5452548cfb873a718`; trích đã đọc kiểm: `data/raw/t02/12327.verified.txt`.
- Quote `award_amount` [1077,1130): “Học bổng Đồng hành: 01 suất, trị giá 25.000.000 đồng.”
- Quote `award_amount` [1133,1297): “Học bổng Tiếp sức: 09 suất, mỗi suất trị giá 6.000.000 đồng, gồm:
+ 08 suất dành cho nhóm ngành Kỹ thuật Ô tô, Kỹ thuật Cơ khí;
+ 01 suất dành cho ngành Môi trường.”
- Quote `deadline` [2171,2250): “Thời gian tiếp nhận hồ sơ: Từ 08 giờ 00 đến 11 giờ 30 ngày 13/10/2026 (thứ Ba).”
- Quote `eligibility` [112,661): “1.1. Học bổng Tiếp sức
- Là sinh viên đang học 02 năm cuối thuộc các ngành, chuyên ngành sau: Kỹ thuật Ô tô, Kỹ thuật Cơ khí và Môi trường; ưu tiên sinh viên thuộc Khoa Cơ khí Giao thông và Năng lượng.
- Có điểm trung bình học tập của năm học 2025-2026 từ 8,0 trở lên theo thang điểm 10 hoặc từ 3,2 trở lên theo thang điểm 4.
- Có kết quả rèn luyện năm học 2025-2026 được xếp loại Tốt trở lên.
- Ưu tiên sinh viên thuộc một trong các trường hợp sau:
a) Có hoàn cảnh khó khăn;
b) Là người dân tộc thiểu số;
c) Có thành tích trong nghiên cứu khoa học.”
- Quote `eligibility` [662,1042): “1.2. Học bổng Đồng hành
- Sinh viên có điểm trung bình học tập năm học 2025-2026 cao nhất trong số các sinh viên do Nhà trường đề xuất.
- Trường hợp kết quả học tập bằng nhau, thứ tự ưu tiên được xác định như sau:
a) Có thành tích trong nghiên cứu khoa học; đạt giải các cuộc thi hoặc đạt giải thưởng cấp quốc gia, quốc tế;
b) Có hoàn cảnh khó khăn hoặc là người dân tộc thiểu số.”

### DUT 12387 — approved

- Thông báo gốc: https://dut.udn.vn/Phong/Taichinh/Thongbao/id/12387
- Canonical nội dung: https://drive.google.com/file/d/1n-92p9gKSBVY0jzFZQPqJKAdq6WsZhXq/view
- Đơn vị: Trường Đại học Bách khoa - Đại học Đà Nẵng / Phòng Kế hoạch - Tài chính
- source/version/family: `dut_f18730b4c4454e87` / `dut_f18730b4c4454e87_be1a2356ad0f864b` / `tuition_hki_2026_dot2`
- Ngày công bố nội dung: 2026-11-03 (date). Thu HTML: 2026-11-09T13:09:33.447062+00:00; thu nội dung canonical: 2026-11-09T13:10:53.089033+00:00.
- Hash text: `be1a2356ad0f864bbb1eb41bdafaf2dd3422c62bc9e9e56b5442c56177e606fa`
- Raw HTML: `data/raw/t02/12387.html`; SHA-256 `c4736f6d132bada07d6ea782709e5c776d7d0bda46405a71d067937cc46429fb`
- Attachment: https://drive.google.com/file/d/1n-92p9gKSBVY0jzFZQPqJKAdq6WsZhXq/preview
- Quyền: công khai để đọc; giấy phép tái phân phối chưa xác nhận; chỉ nội bộ như quy tắc trên.
- Đối soát: Đã đọc HTML và cả 2 trang PDF 6075/TB-ĐHBK. Trang 1 dẫn 4055/TB-ĐHBK ngày 05/8 về mức thu, **không có số tiền VND tuyệt đối**. Quy tắc 40% đợt 2 / 100% nếu chưa nộp 60% đợt 1; khóa 2026 có quy tắc chênh lệch riêng. Không suy số tiền cá nhân. Trang 2: BIDV 04/11 đến 08:30 ngày 30/11/2026, VietinBank đến 11:00 cùng ngày; khóa 2019–2022 BIDV, 2023–2026 VietinBank, <=2018 liên hệ phòng. Hai deadline có scope ngân hàng/khóa riêng. Không truy cập sv.dut.udn.vn. Mức thu VND theo chương trình cần thông báo 4055 ở task nguồn sau; không dùng nguồn này làm evidence số tiền tuyệt đối.
- Raw PDF: `data/raw/t02/12387.pdf`, SHA-256 `a48eab4e6c746f9f7c795282078e7ae0b0fe1938b150e88496e8dda349c12cf3`; trích đã đọc kiểm: `data/raw/t02/12387.verified.txt`.
- Quote `deadline` [1402,1459): “- Qua BIDV: từ ngày 04/11/2026 đến 08h30 ngày 30/11/2026.”
- Quote `deadline` [1460,1523): “- Qua VietinBank: từ ngày 04/11/2026 đến 11h00 ngày 30/11/2026.”
- Quote `payment_requirement` [500,701): “+ Số tiền học phí phải nộp đợt 2 bằng 40% học phí học kỳ I, năm học 2026-2027. Trường hợp sinh viên chưa hoàn thành nghĩa vụ nộp 60% học phí đợt 1 thì phải nộp 100% học phí học kỳ I, năm học 2026-2027;”
- Quote `eligibility` [1541,1768): “- Sinh viên khóa 2019 đến khóa 2026: nộp qua tài khoản Ngân hàng tích hợp cùng thẻ sinh viên (Ngân hàng BIDV cho khóa 2019-2022, Ngân hàng VietinBank cho khóa 2023-2026). Nhà trường phối hợp với Ngân hàng thực hiện thu tự động.”

### DUT 12381 — quarantined

- Thông báo gốc: https://dut.udn.vn/Phong/Taichinh/Thongbao/id/12381
- Canonical nội dung: https://dut.udn.vn/Phong/Taichinh/Thongbao/id/12381
- Đơn vị: Trường Đại học Bách khoa - Đại học Đà Nẵng / Phòng Kế hoạch - Tài chính
- source/version/family: `dut_5612e8ebaf4a8bfe` / `dut_5612e8ebaf4a8bfe_d00f8e6c84db7050` / `tuition_masters_hki_2026_k51`
- Ngày công bố nội dung: 2026-11-02 (date). Thu HTML: 2026-11-09T13:09:53.131167+00:00; thu nội dung canonical: 2026-11-09T13:09:53.131167+00:00.
- Hash text: `d00f8e6c84db70504bd5e9cc58b2d665628e99313f4e0f98408d96eb97743ab9`
- Raw HTML: `data/raw/t02/12381.html`; SHA-256 `f241f81c28810064e802e5cbbedb1bcb17a84272df12a9db1fac60a33ce5c288`
- Attachment: https://drive.google.com/file/d/1gOVIKBh5y6rQpWlucYPYOhKJRBvpusui/preview
- Quyền: công khai để đọc; giấy phép tái phân phối chưa xác nhận; chỉ nội bộ như quy tắc trên.
- Đối soát: QUARANTINED: chỉ HTML tiêu đề/ngày và trang hành chính 1/3 đã đọc. Trang 1 ghi số tiền học phí phải nộp ở danh sách kèm theo. PDF tổng tải về trước khi phát hiện có danh sách; đã xóa PDF tổng và ảnh trang 2–3, **không đọc/OCR/trích danh sách**. Giữ duy nhất ảnh trang hành chính 1. Không có facts, scope audience/cohort null vì corpus chỉ giữ tiêu đề; chưa xác nhận tiền cá nhân và không thu để bổ sung. Trang 1 nhìn thấy hạn 03/11 đến hết 26/11/2026, đối tượng thạc sĩ <=khóa 51: chỉ là thông tin kiểm tay, không nhập fact khi nguồn chưa đủ. Đề nghị người review xác nhận metadata/hạn và tìm thông báo mức thu chung không chứa danh sách cá nhân thay vì thu danh sách này.
- Hash PDF trước khi xóa: `4652aaa956c839af4acac6d810e38ce25d7cca66a4b623970c4ce5688c3f64cb` (không còn bytes). Trang 1 giữ ở `data/raw/t02/12381-p1.png`; SHA-256 `45524fe6743c6f5fa6c6d695ef1c0ac5561290c0b0f4a42d34c6f3b01008acb9`.

## Attachment bổ trợ và điểm bắt đầu

- Agribank mẫu trống: https://drive.google.com/file/d/17exz6WD3BS_r8Qeiszhya_8a_sUeyz0q/view; thu 2026-11-09T13:13:38.306125+00:00; text connector SHA-256 `ea4cd57b57e020cd14949cebd965c47fbc76007533b76375fedcbc16a9ce9c70`, tại `data/raw/t02/agribank-blank-form.txt`. Không lưu raw DOCX; không phải SourceVersion độc lập vì không dùng làm fact tiền/hạn.
- S03/S24 chỉ để tìm nguồn, không đưa danh mục/menu vào corpus.
- S07 mở trực tiếp trả 502, không dùng nội dung search hay suy diễn thiệt hại; ngoài sáu seed. URL: https://fpm.dut.udn.vn/thong-bao/chi-tiet/CANH-BAO-LUA-DAO-CHIEM-DOAT-TAI-SAN-LIEN-QUAN-DEN-SINH-VIEN-2347

## Danh sách chủ repo cần kiểm tay (chưa thực hiện)

Ưu tiên tất cả nguồn phí, sau đó ít nhất hai nguồn học bổng; đây là hàng chờ review, không phải xác nhận đã có người thứ hai kiểm.

1. **12387 / phí:** mở thông báo gốc và PDF ở mục trên. Trang 1 quy tắc 40%/100%, ngoại lệ khóa 2026; trang 2 hai quote BIDV/VietinBank và khóa tương ứng. Xác nhận chép đúng dấu/số, ngân hàng/scope. Không dùng làm số tiền VND.
2. **12381 / phí, quarantined:** chỉ xem trang hành chính 1; kiểm đối tượng thạc sĩ <=51, thời gian 03–26/11/2026. Không lấy danh sách kèm theo. Tìm nguồn mức thu chung không có dữ liệu cá nhân để bù nguồn phí còn thiếu.
3. **12395 / Agribank:** đối chiếu ba quote facts tiền/hạn/đối tượng và mẫu đăng ký trống; giữ hạn 16h ngày 10/11.
4. **12394 / Keidanren & JCCI:** đối chiếu 7 triệu/suất, điều kiện tiếng Nhật và khung 08–11h tới 12/11.
5. **12327 / Toyota:** đối chiếu PDF cả hai trang, hai loại học bổng/scope và hạn 11:30 ngày 13/10; bản trích gõ tay cần spot-check.
6. **12321 / Schneider:** đối chiếu 5 triệu, năm 3–5 Khoa Điện, 16:30 ngày 16/10.

## Kiểm tra tự động

Lệnh tái kiểm trong handoff T02: SourceVersion.model_validate cho 6 real + 1 fixture; hash/NFC/spans/ID/separation; không gọi mạng hoặc đọc gold. T02 không tạo crawler, ingest/chunks/index hoặc validator T07.
