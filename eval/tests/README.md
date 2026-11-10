# T11 — ví dụ tính tay

Đây là **8 outcome giả**, không phải gold DUT, không phải kết quả model. `test_metrics.py::known_data` tạo dữ liệu tạm trong tests; không đọc gold/test thật.

| Case | Family | Gold giả | B giả | C giả |
|---|---|---|---|---|
| 0 | f0 | S | S | S |
| 1 | f0 | C | S | C |
| 2 | f0 | N | N | N |
| 3 | f0 | S | N | S |
| 4 | f0 | C | ERROR | C |
| 5 | f1 | N | S | N |
| 6 | f1 | S | C | S |
| 7 | f1 | N | N | N |

S/C/N viết tắt supported/contradicted/insufficient_evidence. Citation và review giả đều hợp lệ trong vector cơ sở; test khác cố ý phá citation.

B: accuracy3/8; F1(S)=1/3, F1(C)=0, F1(N)=2/3 → macro1/3; ERROR1/8; coverage4/8; answerable1/5; selective error3/4; xác nhận nhầm2/5; mâu thuẫn nhầm1/3. ECV micro3/8. Family macro=(2/5+1/3)/2=11/30. C ECV1, delta C−B=19/30; bootstrap chỉ có hai family nên CI [.6,2/3] rất thô. Không lấy các số này điền report thành tích.

Chạy `.venv/bin/python -m pytest eval/tests -q`. Test CLI tạo fixture run và replay, rồi tái tính cùng vector hai lần để kiểm output giống từng byte. SDK mock chỉ kiểm output1200/thinking0/retry/budget/ledger; không phải live account usage.
