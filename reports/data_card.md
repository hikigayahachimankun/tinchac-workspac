# TinChắc — data card pilot T09 v0.1

**Draft, NOT frozen, chưa có gold do người gán, chưa chạy benchmark.** Ngày 10/11/2026 (Việt Nam). Bộ closed-corpus DUT nội bộ; không là tập tin nhắn lừa đảo thực tế và không đo truy tìm nguồn mới ngoài web.

| Inventory | Scholarship | Payment | Tổng |
|---|---:|---:|---:|
| Approved family | 4 | 1 | 5 |
| Dev family (đã dùng T07) | 4 | 1 | 5 |
| Test family độc lập | 0 | 0 | 0 |
| Case dev nháp | 12 | 3 | 15 |
| Case test đã niêm phong | 0 | 0 | 0 |
| Gold do người gán | 0 | 0 | 0 |
| Quarantined family, không đủ điều kiện | 0 | 1 | 1 |

Chuẩn 12 dev /24 test family (khoảng108 case), fallback8/16 (khoảng72) chưa đạt. 15 case không phải15 family. Dev có5 source_derived và10 synthetic_modified, không có user_contributed, chưa có phân bố nhãn thật. Mỗi case một target, text sạch, origin ghi từng dòng; cùng as_of `2026-11-10T00:00:00+07:00`. Metadata target do người soạn, chưa đo extraction/OCR. Gold không suy từ biến thể.

Nguồn: `docs/source_log.md`, `config/sources.yaml`, snapshots `data/corpus/{sources,chunks,manifest}.json`; version tại `eval/split_manifest.json`. 6 version nguồn ứng viên, 5 approved/indexed, 7 chunks; không tính HTML parent và attachment PDF là hai nguồn độc lập. Canonical/source hash/date/available basis trong corpus, không dùng first_seen để giả kiểm lịch sử trước khi thu. Có nguồn quá deadline; expired là thuộc tính riêng.

Family: Agribank, Keidanren & JCCI, Schneider, Toyota (cả Đồng hành/Tiếp sức), học phí HKI2026 đợt2. Thông báo mức thu4055 được gia hạn6075 dẫn nhưng chưa thu, không tạo family gốc ảo. Học phí thạc sĩ quarantined vì phụ lục chứa danh sách cá nhân, không lấy dữ liệu đó. Nguồn phí approved không xác nhận tiền VND tuyệt đối. Bản mẫu đăng ký trống và danh mục tìm nguồn không tính family.

Audit cả10 cặp nguồn approved: không trùng canonical/hash, similarity che số tối đa0,399192 (ngưỡng gợi ý0,65); đã đối chiếu tên chương trình/scope/parent. Không thấy cùng chương trình nhiều năm trong snapshot; chưa khảo sát nguồn ngoài snapshot. `docs/evidence/T09/family_audit.json` chỉ có thống kê nguồn, không câu hỏi/nhãn test. Giữ cùng family cho gốc/gia hạn/đính chính/repost hoặc mẫu xuyên năm khi có. Cần review lại khi mở rộng.

Split theo family, stratify miền, seed42; hiện cả5 buộc dev vì đã dùng T07. Không có holdout/test đánh giá độc lập. Xem `eval/protocol.md` cho quota mở rộng và giới hạn contamination. Chưa có temporal subset test; chỉ2 case dev deadline (không phải2 family), không có OCR benchmark/user study trong T09.

Gán nhãn: chủ repo tự đọc nguồn theo `eval/annotation_guide.md`; single-annotator pilot, annotator_2/agreements null; **không có agreement/kappa**. Nêu cụ thể nguồn thiếu chứng cứ, S/C có quote/span đủ scope/thời gian. Không dùng output AI làm gold. Validator không đánh giá entailment; nguồn tiền/đính chính và >=20% nguồn còn cần chủ repo spot-check, không dựng kiểm tra thứ hai đã hoàn tất.

Quyền/riêng tư: nguồn public để đọc, quyền tái phân phối chưa xác nhận; corpus dùng nội bộ. Không thu dữ liệu cổng đăng nhập/danh sách cá nhân, không có dữ liệu người dùng thật. Test input/gold tương lai giữ ngoài repo và workspace agent; nguồn tài liệu test được có trong corpus. Chưa có artifact private thực tế nào được agent tạo/đọc.

Giới hạn: pilot5 family, payment chỉ1, không đủ ngoại suy chất lượng thu phí/thiệt hại lừa đảo, không power claim. Chưa đủ 12 dev có nhãn hoặc6 seed approved; D03 mở. Không báo metric/CI từ dữ liệu chưa gán, không tăng n bằng chunk/gia hạn/biến thể. Hướng dẫn owner validate/hash trong `eval/owner_handoff.md`; không có hash freeze hoặc commit chốt vì điều kiện còn thiếu.
