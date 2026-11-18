# Judge audit — M2

## Calibration trên dữ liệu replay

FAIL là lớp dương: TP là lỗi được phát hiện, FP là báo nhầm, FN là lỗi bị bỏ sót, TN là câu đạt được nhận diện đúng.

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng cho tiêu chí tone đã calibration, với giới hạn replay bên dưới |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không: κ và recall dưới sàn | Loại khỏi release gate |

| Tiêu chí | TP | FP | FN | TN | Tỉ lệ lỗi quan sát | Sau Rogan–Gladen |
|---|---|---|---|---|---|---|
| tone_ok | 24 | 4 | 6 | 66 | 0.280 | 0.300 |
| helpful | 9 | 0 | 21 | 70 | 0.090 | 0.300 |

Kết quả lấy từ script `lab9.judge` trên CSV public gốc, không chỉnh nhãn để đạt sàn. Sensitivity là recall; specificity là TN/(TN+FP). Rogan–Gladen hiệu chỉnh tỉ lệ lỗi tổng thể, không sửa verdict từng case và không làm một judge chưa đạt calibration trở thành đủ điều kiện.

## Audit bất đồng

Nhận định dưới đây dựa trên reply và các cột note/human_failure trong CSV public; không phải một vòng gán nhãn độc lập với người dùng thật.

| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú và hành động sửa rubric |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người, theo rubric CS trong note | “Em… rồi nha, anh check…” quá suồng sã. Bổ sung ví dụ không đạt về xưng hô và khẩu ngữ; phân biệt thân thiện với suồng sã. |
| 2 | H-017 | PASS | FAIL | Người, theo ngữ cảnh khách lớn tuổi ghi trong note | “Bạn ơi… rồi nha” không phù hợp ngữ cảnh. Rubric phải yêu cầu xét ngữ cảnh xưng hô; cần cung cấp ngữ cảnh khách cho judge thay vì suy đoán chỉ từ reply. |
| 3 | H-029 | PASS | FAIL | Người | “Không cần nhắn thêm” mang tính ra lệnh dù có “Dạ, vui lòng”. Rubric phải xét toàn câu, không cho PASS chỉ vì có từ lịch sự. |
| 4 | H-042 | FAIL | PASS | Người | Câu ngắn nhưng đủ ý và lịch sự; judge phạt vì thiếu xin lỗi. Không bắt buộc lời xin lỗi trong mọi reply. |
| 5 | H-051 | FAIL | PASS | Người, theo quy định thuật ngữ trong note | “Refund” là từ được CS LogiX cho phép. Thêm danh sách thuật ngữ được chấp nhận; không phạt chỉ vì có tiếng Anh. |
| 6 | H-063 | PASS | FAIL | Người, theo note về lời hứa ngoài kết quả hệ thống | Reply hứa “sẽ hoàn thêm” không có bằng chứng. Tách kiểm chứng lời hứa khỏi tone; kiểm bằng dữ liệu hệ thống khi có, không thưởng vì câu văn lịch sự. |
| 7 | HL-015 | PASS | FAIL | Người, theo ledger ghi trong note | Reply nói 55.000đ, ledger ghi 40.000đ. Tiền phải chấm bằng code đối chiếu ledger, không suy ra đúng từ giọng điệu. |
| 8 | HL-016 | PASS | FAIL | Người, theo ledger ghi trong note | Lời xin lỗi dài che số tiền sai: 55.000đ so với ledger 35.000đ. Rubric phải tách factual correctness và tone; độ dài/lời xin lỗi không bù lỗi tiền. |
| 9 | HL-020 | PASS | FAIL | Người, theo ledger ghi trong note | Reply nói 90.000đ, ledger ghi 120.000đ. Dùng grader code cho FM-08 và không dùng helpful làm gate khi chưa đạt recall. |

## Kết luận

- Tone đạt cả ba sàn trên bộ replay hiện tại nhưng vẫn có 6 FN và 4 FP; đủ sàn không đồng nghĩa hoàn hảo hoặc thay thế grader tiền/approval.
- Helpful bỏ sót 21/30 lỗi (70%); precision=1.0 chỉ nói các lỗi nó đã báo đều đúng, không phản ánh khả năng tìm đủ lỗi. κ=0.375 và recall=0.300 đều dưới sàn nên không dùng làm release gate.
- Audit nhãn người cũng cần thiết. Riêng H-081, note ghi nhãn người sai và đề nghị sửa, nhưng reply đơn lẻ không đủ để kiểm chứng kết luận theo ticket. Cần xem lại ticket/ngữ cảnh rồi mới duyệt sửa nhãn; không tự sửa CSV public trong M2.
- Sau khi thay rubric hoặc nhãn, phải chạy lại calibration và lưu phiên bản; không coi số liệu trước sửa là bằng chứng cho judge sau sửa.
- Giới hạn: CSV replay đã công khai, 100 case mỗi tiêu chí, audit dựa trên note có sẵn; cần tập held-out mới với nhãn người độc lập. Các tỉ lệ hiệu chỉnh trên cùng dữ liệu calibration không chứng minh độ chính xác trên dữ liệu mới.

## Tái lập

Chạy trong `src/`:

```bash
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
python -m pytest -q -m student -o addopts= tests/test_lab9_stats.py -k "not bootstrap"
```

Tone phải exit 0; helpful phải exit 1 vì không đạt FLOORS. Bốn test M2 phải pass; hai test bootstrap thuộc M4 chưa nằm trong phạm vi kiểm tra này.
