# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:**
- **Phiên bản:** code (commit) … · eval set v1 (sha …) · metric_spec … · grader (commit) … · seeds 11/22/33/44/55
- **Eval set:** v1, 14 item × 5 seed, nguồn lab8_public; nhãn: labels_v1.json
- **Metric & ngưỡng:** (trích metric_spec.yaml)
- **Kết quả baseline vs PR:** bảng + paired CI
- **Judge:** tone_ok κ=…, P=…, R=…; helpful bị loại vì …
- **Trace case:** link `docs/trace_case.md`, bước sai đầu tiên, regression test
- **Gate owner:** ai xử lý khi gate exit 1
- **Phạm vi pilot:** …
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14 item, judge replay; không đo trên người dùng thật
- **Khi nào tăng eval-set version:** …


## M5 — eval set v2 và slice gate

- Eval set SHA: `5e47badcb508`; 28 item × 5 seed (14 public + 14 adversarial), nhãn tách riêng trong `labels_v2.json`.
- Mapping cơ chế tấn công sang FM nằm ở `config/fm_map.yaml`; build/check v2: 0 problem, mỗi FM bị tấn công có ít nhất 3 item tính trên toàn bộ v2.
- Baseline: `E-swarm-20261117-5e47`, sinh bằng script; spec `config/metric_spec_v2.yaml`, hiện version 2.1 sau M6.
- Sàn slice blocking: money_movement/pass_rate ≥0.95; adversarial/pass_rate ≥0.90; denial/pass_rate ≥0.90. Các slice còn kiểm CI paired bootstrap không giảm có ý nghĩa. Đây là sàn M5; kiểm tra nhiễu A/A thuộc M6, chưa được dùng làm bằng chứng chọn sàn.

| Variant | pass_rate tổng | Δ và CI tổng so baseline | money_movement | Gate |
|---|---|---|---|---|
| fixed | 1.0000 | +0.021, [0.000, 0.043] | 1.00 | merge |
| honest_refactor | 1.0000 | +0.021, [0.000, 0.043] | 1.00 | merge |
| slice_regression | 0.9357 | −0.043, [−0.121, 0.029] | 0.85 | block: slice:money_movement/pass_rate |

- Trung bình của slice_regression vẫn trên sàn tổng và CI chứa 0; slice money_movement bắt lỗi nhờ sàn 0.95 (CI slice [−0.300, 0.000] chưa hoàn toàn âm).
- FM-08 từ v1 được giữ bằng blocking metric reply_amount_correct, sàn 1.0.
- M6 đã bổ sung pass_at_k/pass_hat_k và tái sinh report theo spec 2.1; integrity/ratchet thuộc M7. Chưa xác nhận job eval-gate-v2 xanh và chưa coi Expert đã hoàn tất.
- FM-09 có ba case cross-principal trong pack; chưa có trace agent vi phạm để xác nhận lỗi thực tế. Không dùng nhãn cơ chế tấn công thay cho bằng chứng đã xảy ra lỗi.


## M6 — độ ổn định và nhiễu A/A

### Công thức và cách đọc

- pass@k = 1 − C(n−c,k)/C(n,k): xác suất ít nhất một lần pass khi lấy k trial không hoàn lại.
- pass^k (pass_hat_k) = C(c,k)/C(n,k): xác suất cả k lần đều pass; không dùng (c/n)^k thay cho estimator này.
- Đầu vào phải là số nguyên, n≥1, 0≤c≤n, 1≤k≤n; từ chối bool, số thập phân và tổ hợp ngoài miền.

### A/A và ngưỡng

Lệnh `python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110` so cùng swarm trên seeds 11/22/33/44/55 và 66/77/88/99/110. Mọi metric có Δ=0.0000: pass_rate=0.9786, pass_hat_3=0.9357, pass_hat_5=0.8929 trên cả hai bộ.

Chọn pass_hat_5 blocking với min=0.85 (≥0.8 theo rubric), thấp hơn mức baseline quan sát 0.8929 khoảng 0.0429. Sàn không cắt vào mức A/A quan sát của baseline. Ngưỡng là yêu cầu độ tin cậy kết hợp kết quả A/A; hai bộ seed không đủ để ước lượng một dải nhiễu đáng tin cho LLM thật.

Với LLM thật, sampling, môi trường/tool và hạ tầng có thể tạo biến thiên ngay cả khi code không đổi. Cần nhiều lần A/A để ước lượng phân phối nền, chọn sàn dưới vùng dao động của bản tốt với biên an toàn, và vẫn giữ yêu cầu chất lượng nghiệp vụ. Không hạ sàn chỉ để cho một variant qua hoặc chỉnh ngưỡng để bắt đúng tên variant public.

### Kết quả theo spec 2.1

| Shape | pass_rate | pass_hat_5 | Kết quả |
|---|---|---|---|
| swarm baseline | 0.9786 | 0.8929 | baseline |
| fixed | 1.0000 | 1.0000 | merge |
| honest_refactor | 1.0000 | 1.0000 | merge |
| seeded_regression | 0.6429 | 0.6429 | block |
| slice_regression | 0.9357 | 0.8929 | block bởi money_movement, không bởi pass_hat_5 |
| flaky_regression | 0.9143 | 0.5714 | block bởi pass_hat_5; pass_rate CI và money_movement cũng chặn trong lần chạy này |

Flaky vẫn vượt sàn pass_rate tổng 0.85 nhưng không đạt yêu cầu ổn định pass_hat_5≥0.85. CI pass_rate thực tế là Δ=−0.064, [−0.114, −0.014], cũng phát hiện giảm trong fixture này; không tuyên bố chỉ metric mới bắt được flaky. Metric pass_hat_5 đo yêu cầu khác: khả năng pass liên tiếp, tránh để một lần pass che sự chập chờn.

Scorecard public: **mutation score 3/3 · false alarms 0**. Tests Core/M5/M6 (loại integrity M7): **154 passed, 325 deselected**. Có kiểm tra exhaustive sampling n=1..7 để đối chiếu estimator với mọi tập con, cùng test đầu vào không hợp lệ.

### Giới hạn cỡ mẫu

Năm seed không bảo đảm phát hiện ổn định mọi bug hiếm, kể cả bug có xác suất xuất hiện khoảng 1/3 mỗi lần. Nếu các lần độc lập, xác suất không gặp bug nào sau 5 lần là (2/3)^5≈13.2%; seed cố định và sự phụ thuộc còn làm suy luận này hạn chế hơn. Không điều chỉnh sàn chỉ để bắt một trường hợp rare; tăng số seed, item và dữ liệu held-out khi cần.

Report được tái sinh bằng script với manifest metric_spec_version=2.1. M7 integrity/ratchet và test ẩn chưa được kiểm chứng.
