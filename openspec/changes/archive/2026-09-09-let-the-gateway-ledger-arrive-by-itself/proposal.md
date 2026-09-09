# Để sổ Gateway tự đi vào dashboard

## Why

Sau khi một agent gọi qua Gateway, dữ liệu vào `LiteLLM_SpendLogs` **ngay** (bất đồng bộ
~4 giây, không ai phải làm gì). Nhưng dashboard thì không đổi cho tới khi **có người chạy
tay** `scripts/refresh_gateway.py`. Đo 08/09/2026:

```
   LiteLLM_SpendLogs                    444 dong,  29/08 -> 08/09   <- tu dong, luon moi
   fact_call  WHERE source='gateway'     41 dong,  31/08 -> 31/08   <- dung o mot ngay
```

Trong 444 dòng ấy, 80 dòng không mang tag định danh nên bị tầng nạp bỏ **đúng theo thiết
kế**. Còn lại khoảng 360 dòng đáng vào sổ, mà sổ chỉ có 41. Tám ngày lưu lượng Gateway đã
nằm trong database mà dashboard không thấy — **và không có
dấu hiệu nào nói rằng nó không thấy**. Đây đúng là chế độ hỏng mà `scripts/audit_db.py`
tự cảnh báo trong chính docstring của nó:

> `load_gateway.py` hỏng im lặng thì `fact_call` không có dòng gateway nào, MỌI phép kiểm
> gateway vẫn xanh

**ĐÍNH CHÍNH 09/09/2026** — bản đầu của proposal này viết rằng "không phép nào so
`fact_call` với `LiteLLM_SpendLogs`, vì `audit_db.py` không hề mở kết nối sang sổ Gateway".
**Sai.** `scripts/audit_db.py` nhóm J (`group_j_gateway_row_accounting`, dòng 1348) mở
đúng kết nối ấy qua `connect.GATEWAY_DSN`, tự tính lại tag định danh bằng SQL của riêng
nó, và đã có sẵn cả ba kết cục kể cả "chưa kiểm được khi không mở được sổ nguồn". Khẳng
định sai đến từ một lần `grep` bị cắt bằng `head`.

Nên khoảng hở thật **hẹp hơn**, và phải nói đúng nó:

- Nhóm J so theo **tập dòng**: dòng nào của nguồn chưa vào `fact_call` mà không có lý do
  gọi tên được thì HỎNG. Nó **đủ** để bắt việc "chưa ai chạy refresh" — nhưng chỉ **khi có
  dòng mới trong nguồn**.
- Không phép nào đo độ trễ theo **thời gian**. Nên một đường làm mới đã chết **trong lúc
  vắng lưu lượng** vẫn xanh, cho tới khi lượt gọi tiếp theo tới. Ta biết sau, không biết
  trước.
- Và cả hai phép kiểm ấy chỉ chạy khi **có người chạy `audit_db.py`**.

Việc này gấp lên từ ngày mai: agent thứ hai (`crm-feedback`) đi qua Gateway. Hai agent
chạy thật mà sổ chỉ cập nhật khi có người nhớ ra thì con số trên dashboard không dùng để
ra quyết định được.

## What Changes

- **Chạy đường làm mới nhanh như một dịch vụ**, thay vì trông vào việc có người gõ lệnh.
  `scripts/refresh_gateway.py` **đã có sẵn chế độ `--every`** và đã được đặc tả ở
  `gateway-refresh-completeness` là chỉ đọc từ database. Change này không viết lại nó —
  chỉ cho nó chạy.
- **Thêm phép đo độ trễ theo thời gian vào nhóm J đang có** — dùng lại kết nối sổ
  nguồn mà nhóm ấy đã mở, không mở thêm. Chỉ thêm ba thứ nhóm J chưa có: so mốc thời gian
  mới nhất, nêu độ trễ bằng số, và ngưỡng suy ra từ nhịp làm mới. **Không** viết lại năm
  phần nhóm J đã làm đúng (kết nối, ba trạng thái, loại trừ dòng bị bỏ có tên, không sập
  khi mở sổ nguồn thất bại).
- **Phơi độ trễ ra chỗ người nhìn thấy**, để số cũ không bao giờ trông giống số mới.
- **KHÔNG** viết lại `db/load_gateway.py` sang SQL. Xem "Đã cân nhắc và loại" ở
  `design.md` — đường `postgres_fdw` đã được **đo là chạy được**, và vẫn bị loại.

## Capabilities

### New Capabilities
- `gateway-ledger-freshness`: sổ dashboard phải tự hội tụ về sổ Gateway mà không cần người
  can thiệp; và độ trễ giữa hai sổ phải đo được, phải phân biệt được với "không có dữ
  liệu", phải nhìn thấy được.

### Modified Capabilities
<!-- Khong co. `gateway-refresh-completeness` quy dinh duong lam moi nhanh phai dung lai
     NHUNG BANG NAO; change nay quy dinh no PHAI CHAY va do tre phai lo ra. Hai chuyen
     khac nhau, khong sua yeu cau nao dang co. -->

## Impact

- `docker-compose.yml` — thêm một dịch vụ chạy vòng lặp làm mới. **Bẫy đã biết**:
  `connect.GATEWAY_DSN` dựng từ `PG_HOST` mặc định `localhost`; trong container thì
  `localhost` là chính container đó, nên dịch vụ mới **phải khai `GATEWAY_DSN` tường
  minh**, giống cách `tools` phải khai `TOKEN_LEDGER_DSN`.
- `scripts/audit_db.py` — thêm phép kiểm cần **kết nối thứ hai** sang database `litellm`
  bằng vai `gateway_readonly`.
- `scripts/refresh_gateway.py` — có thể phải chỉnh cách báo lỗi cho hợp chế độ dịch vụ.
- **Không** đụng `db/load_gateway.py`, không đụng schema, không đụng sổ gốc của Gateway.
- Phụ thuộc thứ tự: change `read-the-gateway-columns-we-still-ignore` (38/44) đang sửa
  `db/load_gateway.py`. Change này không sửa file đó nên chạy song song được, nhưng phép
  kiểm độ trễ phải tôn trọng luật của nó — dòng `cache_hit = true` **có** trong
  `fact_call` mà **không** vào `fact_usage_daily`.
