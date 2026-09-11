## Why

Ô 2.1 của change `standardize-kpi-card-insights` mở từ 22/07 và đến nay vẫn chưa đóng được. Câu hỏi gốc: **hoá đơn của Google có tách riêng token suy nghĩ ra khỏi token ra không?** Nếu có, và dashboard không cộng phần đó, thì tổng token đang thiếu — đúng hạng lỗi cache ngày 15/08 làm rơi 26% token mà không ai thấy.

Đến 10/09 câu hỏi mới trả lời được **một nửa**. Qua Gateway thì không có ngăn thứ ba: suy nghĩ nằm trong `completion_tokens` và bị tính tiền theo giá token ra. Nhưng đó là `spend` do LiteLLM tự tính từ bảng giá của nó, **không phải hoá đơn Google**. Cả dự án này tồn tại vì hai nguồn đó từng lệch nhau.

Ngày 11/09 kiểm lại thì phép đối chiếu **làm được ngay**, và lý do hoãn trước đây đã hết: `fact_monitoring` có 11.440 dòng bật suy nghĩ từ 24/04 đến 29/08, `fact_billing_daily` phủ 240 ngày tới 29/08, và riêng `gemini-2.5-flash` có 128 ngày chung. Thêm một dấu hiệu chưa ai theo đuổi: hoá đơn có SKU mang thẳng chữ **`non-thinking`** trong tên, nghĩa là bảng giá của Google CÓ phân biệt suy nghĩ.

## What Changes

- Dựng phép đối chiếu giữa `fact_billing_daily` và `fact_monitoring` cho phần token ra, trên những ngày và model mà cả hai nguồn cùng có dữ liệu.
- Trả lời dứt điểm: token suy nghĩ được hoá đơn xếp vào `kind` nào, và dashboard có đang bỏ sót phần đó không.
- Ghi kết quả vào tài liệu rồi đóng ô 2.1 bằng con số, không bằng lập luận.
- **KHÔNG** đổi công thức `ti + to + cached` của dashboard trong change này. Đổi hay không là việc của change sau, sau khi đã biết câu trả lời.

## Capabilities

### Modified Capabilities

- `provider-ledger-reconciliation`: thêm yêu cầu về việc truy token suy nghĩ nằm ở đâu trong hoá đơn, và về việc SKU chưa biết không được rơi âm thầm.
