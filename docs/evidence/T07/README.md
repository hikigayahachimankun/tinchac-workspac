# T07 — 10 public seed retrieval probes

Only five approved T02 families. This is a technical pilot; no test gold or T09 split. All probes use `as_of=2026-11-09T14:00:00Z`; no query-result cache. Query strings, source quotes/spans, exact full chunk IDs, scores and timings are in `retrieval-dev.json`.

Corpus: `corpus-7b832d58775878a57849d32ff241cc61904afadfc0299a66e3918ad82da18982`.

| Alias | Full chunk_id | PDF page |
|---|---|---|
| S | `dut_09fb9c92c9ab7b2f_e5e4f9b141b646e6_c001` | — |
| J | `dut_2a0b90b19b67872f_dbd836ad6b4251a7_c001` | — |
| T1 | `dut_344b21e393855658_921795aab925d271_c001` | 1 |
| T2 | `dut_344b21e393855658_921795aab925d271_c002` | 2 |
| A | `dut_be8a0080c11e660f_f0ef96bab2007bb9_c001` | — |
| F1 | `dut_f18730b4c4454e87_be1a2356ad0f864b_c001` | 1 |
| F2 | `dut_f18730b4c4454e87_be1a2356ad0f864b_c002` | 2 |

| Case | Query | Expected chunk / source span | FTS-only top-5 | Hybrid top-5 | Expected rank FTS / hybrid |
|---|---|---|---|---|---|
| seed01 | Học bổng Agribank Nam Đà Nẵng năm 2026 trị giá 5 triệu đồng mỗi suất. | A [482,502) | T1, A, S, J, T2 | T1, A, S, J, T2 | 2 / 2 |
| seed02 | Agrbank chắp cánh ước mơ nhận hồ sơ 14h00 đến 16h00 ngày 10/11/2026. | A [963,1043) | A, S, T2, J, F2 | A, S, F2, J, T2 | 1 / 1 |
| seed03 | Học bổng Keidanren JCCI năm học 2026-2027 cần chứng chỉ tiếng Nhật. | J [359,471) | J, T2, F1, T1, S | J, F1, T1, T2, A | 1 / 1 |
| seed04 | Keidanren JCCI nhận hồ sơ tới ngày 12/11/2026 từ 08h00 đến 11h00. | J [1452,1530) | J, F2, A, T2, S | J, F2, T2, A, S | 1 / 1 |
| seed05 | Học bổng Schneider Electric cấp 5.000.000 đồng/suất cho sinh viên Khoa Điện. | S [455,474) | S, T1, A, J, F2 | S, T1, A, J, F2 | 1 / 1 |
| seed06 | Hạn nộp học bổng Schneider Electric là 16h30 ngày 16/10/2026. | S [534,674) | S, F1, J, T2, T1 | S, F1, T1, J, T2 | 1 / 1 |
| seed07 | Học bổng Toyota Đồng hành năm học 2026-2027 có một suất 25 triệu đồng. | T1 [1077,1130) | T1, T2, A, F1, J | T1, F1, A, T2, J | 1 / 1 |
| seed08 | Nộp hồ sơ học bổng Toyota trước 11 giờ 30 ngày 13/10/2026. | T2 [2171,2250) | T2, F2, T1, F1, A | T2, T1, F2, F1, A | 1 / 1 |
| seed09 | Học phí đợt 2 học kỳ I 2026-2027 thu qua BIDV đến 08h30 ngày 30/11/2026. | F2 [1402,1459) | F1, F2, T2, T1, J | F1, F2, J, T1, T2 | 2 / 2 |
| seed10 | Học phí đợt 2 năm học 2026-2027 qua VietinBank đến 11h00 ngày 30/11/2026. | F2 [1460,1523) | F2, F1, J, T2, T1 | F2, F1, J, T1, T2 | 1 / 1 |

| Method | Recall@5 | Top-1 | Mean query latency, ms |
|---|---|---|---|
| fts5_only | 100% | 80% | 1.315 |
| fts5_tfidf_rrf | 100% | 80% | 10.158 |

Selected: FTS10 + char_wb(3,5)10, RRF60, top5. Both methods recover every expected seed chunk in top5. Neither wins top1 on these probes. Hybrid costs more CPU on this small corpus; it stays as the specified default, with no threshold tuning or claimed quality advantage. Freeze remains a later T09/T11 action.

BM25 ranks smaller scores first ([SQLite FTS5](https://www.sqlite.org/fts5.html#the_bm25_function)); character matching uses the documented [TfidfVectorizer](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html). Local PDF text extraction follows [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/recipes-text.html); the two scanned seed PDFs use reviewed manual extracts.
