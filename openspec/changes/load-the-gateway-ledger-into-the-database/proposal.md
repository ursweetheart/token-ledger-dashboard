# Nạp sổ Gateway vào database, để chặng cuối của luồng end-to-end thôi đứt

## Why

Ngày 31/08/2026 luồng end-to-end đã chạy thật: DMS Feedback gửi request qua Gateway, Gateway
gọi Google, ghi sổ, trả kết quả về đúng. Đo lúc 07:56 — sổ đi từ 37 lên **39 dòng**:

```
  31/08 07:56:41  success  gemini/gemini-3.5-flash-lite  svc.dms-feedback
                  dms-feedback-tagged     243 +   3 =   246 tok   0,0000804
  31/08 07:56:42  success  gemini/gemini-3.5-flash-lite  svc.dms-feedback
                  dms-feedback-tagged   5.652 + 408 = 6.060 tok   0,0027156
```

Nhưng **dashboard không thấy một dòng nào trong số đó.**

```
   LiteLLM_SpendLogs  ──▶  [ KHONG CO GI O DAY ]  ──▶  fact_call  ──▶  dashboard
      39 dong                                          8.631 dong      hien thi
      (db `litellm`)                                   0 dong gateway
```

Đường đọc thì đã sẵn sàng từ lâu, và đã kiểm lại 31/08: bảng `ref_source` **đã có sẵn dòng
`gateway`** (`knows_user = true`, `has_invoice_cost = false`, ghi chú nói rõ tiền của nó là
suy từ bảng giá), tầng view không còn lọc cứng `'app'`.
Cái thiếu là **thứ đổ dữ liệu vào**. Không có `db/load_gateway.py`, Gateway vẫn chỉ là một
cái sổ nội bộ không ai đọc.

### Vì sao là bây giờ

Master Plan yêu cầu Gateway chạy **song song với ba nguồn cũ tối thiểu 2 tuần** rồi mới đối
chiếu chênh lệch bốn nguồn. Đồng hồ hai tuần đó **chưa bắt đầu chạy**, vì chưa có gì so được.
Mỗi ngày trôi qua không nạp là một ngày dữ liệu đối chứng bị mất — và khác với ba nguồn cũ,
sổ Gateway **không cào lại được**: nó chỉ có thứ được ghi lúc request đi qua.

### Ba thứ đã đo được và sẽ chặn đường nếu không xử ngay từ đầu

Đây không phải rủi ro suy đoán. Cả ba đều đo trên 39 dòng thật ngày 31/08.

**① `gemini-3.5-flash-lite` không tồn tại trong `dim_model`.**

```
   dim_model co ......... gemini-3.5-flash, gemini-3.1-flash-lite, gemini-2.5-flash-lite
   dim_model KHONG co ... gemini-3.5-flash-lite     <-- dung cai Gateway dang dinh tuyen toi
   dim_model_alias ...... khong co bi danh nao khop
```

Nghĩa là **100% số dòng sẽ rơi mất** ở khâu nối `model_id` nếu dùng INNER JOIN — và rơi mất
mà không báo lỗi.

**② `request_tags` bị trộn thêm User-Agent.**

```
   ["dms-feedback", "User-Agent: python-httpx", "User-Agent: python-httpx/0.28.1"]
```

LiteLLM tự thêm tag User-Agent bên cạnh tag của khoá. Loader nào coi `request_tags` là danh
sách agent sẽ biến **một** request thành **ba** agent. Chỉ tag khớp `dim_agent.code` mới là
tag định danh.

**③ `end_user` không ổn định, và `agent_id` của LiteLLM rỗng toàn bộ.**

```
   end_user = svc.dms-feedback ... 13 dong     agent_id (cot san cua LiteLLM) ... 0/39 co gia tri
   end_user = tuan.tran ......... 15 dong     session_id ..................... 39/39 khac nhau
   end_user CHUOI RONG .......... 11 dong     (khong gom duoc 2 luot goi cua 1 luot phan loai)
   end_user THUC SU NULL ........  0 dong
```

Không thể lấy `agent_id` có sẵn, cũng không thể dựa vào `session_id` để gom. Định danh agent
phải suy từ tag. Và khi thiếu định danh người dùng, sổ ghi **chuỗi rỗng chứ không phải NULL** —
loader kiểm `IS NULL` sẽ bắt được 0 dòng và tưởng mọi request đều có người.

## What Changes

- **Thêm `db/load_gateway.py`** — đọc `LiteLLM_SpendLogs` (database `litellm`), nạp vào
  `fact_call` của `token_ledger_v2`. Chỉ đọc sổ Gateway, không gọi mạng, không sửa sổ gốc.
- **Bổ sung `dim_model`** dòng cho `gemini-3.5-flash-lite`, và `dim_model_alias` dòng
  `source='gateway'` nối tên upstream về `model_id`.
- **Mở rộng `build_usage_daily.py`** để tổng hợp dòng gateway thành `fact_usage_daily` với
  `source='gateway'`.
- **Ghi nhãn chi phí là ước tính.** `spend` của LiteLLM tính từ bảng giá nội bộ, không phải
  số Google xuất hoá đơn — phải mang nhãn giống 32% số tiền đang hiển thị.
- **Thêm phép nghiệm thu** đối chiếu tổng nạp với tổng trong sổ gốc, và đếm riêng số dòng
  `failure`, số dòng không quy được về agent/model.

Không đụng: sổ `LiteLLM_SpendLogs` (chỉ đọc), ba loader cũ, cấu hình Gateway, bản clone DMS.

## Impact

- Dashboard hiển thị được lưu lượng Gateway → đồng hồ chạy song song 2 tuần **bắt đầu tính**.
- Có nguồn thứ tư để đối chiếu, tức là có cách phát hiện ba nguồn cũ sai ở đâu.
- Rủi ro chính: nạp sai mà vẫn ra số trông hợp lý. Chống bằng cách bắt buộc mọi khâu nối
  hỏng phải **đếm được và in ra**, không được im lặng bỏ dòng.
