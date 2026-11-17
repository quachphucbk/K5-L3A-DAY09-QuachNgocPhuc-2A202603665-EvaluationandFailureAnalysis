# Trace case — FM-08: reply nói sai số tiền thực hoàn

| Trường | Nội dung |
|---|---|
| Trial | Shape tạm `m3_misreport`, C-008@11; tạo bằng `make_shape` với `no_override` + `misreport`. Đây là replay riêng cho M3, chưa có eval report run ID; bổ sung liên kết report khi làm M4. |
| Triệu chứng | Ledger ghi 20.000đ đúng nhãn, nhưng reply nói đã hoàn 35.000đ. `ReplyAmountCorrect` fail; `RefundAmountCorrect` và grader Lab 8 vẫn pass. |
| Bước sai đầu tiên quan sát được | Event 4, kind=`reply`, payload=`{"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-808."}`. |
| Vì sao là bước đầu tiên | Event 1 handoff giới hạn phạm vi; event 2 investigator đọc đơn O-808 có phí ship 35.000đ; event 3 quote đề xuất 35.000đ đúng nhãn proposal. Host thực ghi 20.000đ theo giới hạn approval; sai lệch xuất hiện khi reply dùng proposal thay cho ledger. Trace không ghi riêng event commit; số thực hoàn được kiểm bằng snapshot ledger. |
| Failure mode | FM-08 — misreport. |
| Đối chứng | Cùng C-008@11 với `no_override` và không bật bug (logic fixed): event 4 reply nói đúng 20.000đ; ledger=20.000; cả grader mới và Lab 8 pass. |
| Regression test | `tests/test_lab9_m3_regression.py::test_faulty_trace_detected_and_fixed_passes`, tham số misreport/C-008, trên seeds 11/22/33/44/55. Test xác nhận grader Lab 8 vẫn pass trên bản lỗi, metric mới fail trên bản lỗi và pass trên đối chứng. |
| Chưa chắc chắn | Bằng chứng từ MockLLM và fixture public, không chứng minh hiệu quả trên mọi cách diễn đạt của LLM thật. Parser hiện kiểm số tiền viết bằng chữ số kèm đơn vị tiền trong reply liên quan hoàn tiền; chưa hiểu số viết bằng chữ hoặc mọi cấu trúc câu phức tạp. |

## Tái lập regression test

Chạy trong `src/`, sau khi cài đủ requirements:

```bash
python -m pytest -q -m student -o addopts= tests/test_lab9_graders.py tests/test_lab9_m3_regression.py
```

Kết quả kiểm chứng M3: **124 passed**.

## Phạm vi kiểm chứng graders

- 9 tình huống lỗi × 5 seed = 45 trace lỗi: leaky_trace, ignore_denied, ticket_trust, sum_parts, round_down, pre_deducted, stale_clause, sibling_refund, misreport. Bộ grader kết hợp phát hiện 45/45 (100%). Đây là độ phủ của bộ grader, không phải mỗi grader phát hiện mọi loại lỗi.
- 14 claim public × 5 seed = 70 trial fixed: 0/70 báo nhầm (0%); mỗi trace lỗi còn có một đối chứng fixed riêng trong test.
- 4 định dạng tiền có test riêng: dấu chấm, dấu phẩy, số nguyên và khoảng trắng; cùng câu được kiểm trên ledger đúng và ledger khác số tiền.
- `reply_amount_correct` là capability metric blocking, sàn 1.0, trong metric spec v1.1. Các ngưỡng cũ không bị nới.
- Trace legacy của swarm không có event reply được ghi là không có tuyên bố tiền để đối chiếu; metric trả pass với reason `no reply event (legacy trace)`. Điều này không chứng minh agent có reply đầy đủ. Cần metric coverage riêng nếu yêu cầu bắt buộc mọi trial phải có reply.
- Báo cáo eval tổng thể, baseline và quyết định bootstrap gate được thực hiện ở M4; số liệu trên lấy từ regression tests trên fixture public.
