# Mở rộng bộ kiểm tra tự động sang dữ liệu Gateway

Đóng **STT 7 mục tiêu 2** của Master Plan (mốc 14/10/2026). Nguyên văn sản phẩm:

```
   - Phep kiem moi trong scripts/audit_db.py va backend/check_api.py cho nguon
     gateway: khoa ngoai, so khop voi hoa don, khong co tai khoan la, khong co
     ngay tuong lai.
   - Phep kiem rieng doi chieu token cache cua Gateway voi SKU cache tren hoa
     don Google.
```

Mọi con số dưới đây đo trên database thật `token_ledger_v2` ngày **03/09/2026**.

## Why

### ① Danh sách khoá ngoại của audit **trôi khỏi database**, và đang trôi nhanh hơn

`scripts/audit_db.py` giữ `FOREIGN_KEYS` là một danh sách **gõ tay**. Đếm hai vế:

```
   khoa ngoai THAT trong database   36 quan he
   FOREIGN_KEYS khai trong audit    23 quan he
                                    -------------
   KHONG DUOC KIEM                  13 quan he
```

Mười ba quan hệ không ai canh:

```
   fact_usage_hourly.account_id     fact_call.source
   fact_usage_hourly.agent_id       fact_call.unit_id
   fact_usage_hourly.model_id       fact_latency_daily.source
   fact_usage_hourly.source         fact_perf_daily.source
   dim_function.agent_id            dim_model_alias.model_id
   dim_unit.canonical_unit_id       ref_budget.agent_id
   ref_price.model_id
```

**Sáu trong mười ba quan hệ đó do migration 008 tạo ra — sáng nay:**
`fact_usage_hourly` bốn khoá, cộng `fact_latency_daily.source` và
`fact_perf_daily.source`. Bảy quan hệ còn lại là nợ cũ (`fact_call.source` từ migration
004, `fact_call.unit_id` từ baseline, và năm quan hệ chưa bao giờ được khai).

Nghĩa là đây không phải một khoản nợ đứng yên: **cứ thêm một bảng là danh sách tụt lại
thêm**, và nó tụt trong im lặng, vì phép kiểm vẫn báo `Foreign keys (23 relations)` ĐẠT
— con số 23 nằm ngay trong nhãn, và nó là số quan hệ **được khai**, không phải số quan
hệ **có thật**.

Đúng hình dạng lỗi mà chính `audit_db.py` sinh ra để chống: một con số trông như phép
đo, mà thật ra là phép đo của một tập nhỏ hơn tập cần đo.

### ② Phép kiểm "không có ngày tương lai" ghim cứng một năm, và chỉ soi một bảng

```python
   # scripts/audit_db.py:629
   " WHERE CAST(day AS TEXT) > '2026-12-31'"
```

Hai vấn đề, cả hai đều nổ muộn:

- **Ghim `2026`.** Sang 2027 thì mọi dòng dữ liệu **thật** đều bị coi là ngày tương lai;
  phép kiểm chuyển từ im lặng sang kêu ầm — không phải vì hệ thống hỏng.
- **Chỉ soi `usage_resolved`.** `fact_call` (nơi Gateway ghi từng lượt),
  `fact_usage_hourly` và sổ `LiteLLM_SpendLogs` đều không được soi. Đồng hồ sai ở khâu
  nạp Gateway sẽ đi thẳng vào `fact_call` mà không ai chặn.

### ③ Phép kiểm cho nguồn `gateway` **ĐẠT cả khi không có dòng gateway nào**

Mọi phép kiểm gateway hiện có đều mang hình dạng:

```sql
   SELECT COUNT(*) FROM fact_call WHERE source = 'gateway' AND <dieu kien xau>
   -- roi:  a.check(n == 0, ...)
```

Với **0 dòng gateway**, câu này trả `0` và phép kiểm báo **ĐẠT**. Nó không phân biệt
*"Gateway ghi đúng"* với *"Gateway không ghi gì cả"*.

Đây không phải giả thiết. Ngày 02/09 `rebuild_db.py` từng để `api_readonly` mất sạch
quyền đọc mà **cả hai** bộ kiểm báo lành, vì cùng một loại nguyên nhân: phép kiểm
khẳng định một tính chất mà nó chưa từng thực sự quan sát. Và bẫy này còn đắt hơn:
bước `load_gateway.py` mà hỏng im lặng thì dashboard chỉ trông như *"chưa có lưu
lượng"*.

### ④ Đối chiếu token cache: **hai vế tồn tại, nhưng chưa từng gặp nhau**

Vế 2 của sản phẩm đòi đối chiếu `cached_tokens` của Gateway với SKU cache trên hoá đơn.
Đo cả hai vế:

```
   ve GATEWAY   fact_call source='gateway'   41 dong · cached_tokens  0/41 co gia tri
   ve HOA DON   fact_billing_daily kind='cached'
                461 dong · 252.321.118 token · 214 ngay · 6 agent · 05/01 -> 29/08
```

Vế hoá đơn **rất giàu**. Vế Gateway **rỗng sạch**. Và ngay cả khi nó có số:

```
   so ngay ma gateway VA billing cung co du lieu:  0

   gateway     31/08 -> 31/08     1 ngay
   billing     01/01 -> 29/08   240 ngay
```

**Không một ngày nào giao nhau.** Nên phép đối chiếu này **chưa chạy được**, và lý do
là dữ liệu chứ không phải công sức.

Điều nguy hiểm là cách xử lý dễ chọn nhất: viết phép kiểm, cho nó chạy trên tập rỗng,
nó báo ĐẠT, và mục Master Plan được tick xanh. Khi đó ta vừa **đóng một mục bằng một
phép kiểm chưa từng kiểm gì**.

## What Changes

**① Khoá ngoại: hỏi database, đừng gõ tay**

- `scripts/audit_db.py` dựng danh sách khoá ngoại từ `pg_constraint` thay vì hằng số
  `FOREIGN_KEYS` gõ tay. Thêm bảng mới là phép kiểm tự phủ, không phải nhớ sửa.
- Giữ một phép kiểm **đối chiếu số lượng**: nếu số quan hệ đọc được tụt xuống dưới mốc
  đã ghi thì báo động — mất một khoá ngoại cũng là một sự kiện, không được im.

**② Ngày tương lai: soi mọi bảng có cột thời gian, và bỏ ngưỡng ghim**

- Ngưỡng tính từ **ngày chạy** (`CURRENT_DATE`), không ghim năm.
- Soi `fact_call`, `fact_usage_daily`, `fact_usage_hourly`, `fact_billing_daily`,
  `fact_monitoring` — không chỉ `usage_resolved`.

**③ Phép kiểm phải phân biệt "đạt" với "không có gì để kiểm"**

- Mọi phép kiểm riêng cho một nguồn phải **khai báo số dòng nó đã quan sát**. Chạy trên
  tập rỗng thì kết quả là **CẢNH BÁO "chưa kiểm được"**, không phải ĐẠT.
- `backend/check_api.py` nhận phép kiểm cho nguồn gateway ở tầng HTTP.

**④ Đối chiếu token cache: viết phép kiểm, và cho nó nói thẳng khi chưa chạy được**

- Phép kiểm đối chiếu `cached_tokens` (gateway) với SKU cache (hoá đơn) **theo ngày ×
  agent**, chỉ trên **ngày có cả hai nguồn**.
- Không có ngày nào giao nhau → báo **CHƯA KIỂM ĐƯỢC** kèm đúng lý do đo được (hai
  khoảng ngày rời nhau), **không** báo ĐẠT.
- Ghi rõ ngưỡng chấp nhận sai lệch **trước** khi có số đầu tiên — theo đúng kỷ luật mà
  STT 7 dòng 19 đã đặt cho báo cáo đối chiếu.

**Không đụng:** sổ `LiteLLM_SpendLogs` (chỉ đọc), ba bộ số cũ, tầng frontend, và các
migration đã đóng.

## Capabilities

### New Capabilities

- `automated-check-coverage`: bộ kiểm tự động phải phủ đúng cấu trúc thật của database
  và phải phân biệt được "đã kiểm và đạt" với "không có gì để kiểm".
- `gateway-cache-reconciliation`: đối chiếu token cache của Gateway với SKU cache trên
  hoá đơn Google, kèm quy tắc xử lý khi hai nguồn chưa có ngày chung.

### Modified Capabilities

*(không có — hai capability trên đều mới; các spec hiện có không đổi yêu cầu nào.)*

## Impact

- **Đóng STT 7 mục tiêu 2**, hoặc chứng minh được vế 2 **chưa** đóng được kèm lý do đo
  đạc — và đó cũng là một kết quả, miễn là nó nói ra thay vì tick xanh.
- Bịt một khoảng mù đang lớn dần: **13/36 khoá ngoại**, trong đó 6 sinh ra chỉ trong
  hôm nay.
- Gỡ một quả bom hẹn giờ: ngưỡng ngày ghim `2026`.
- Sau change này, thêm một bảng vào database **không** làm bộ kiểm tụt lại phía sau.

**Rủi ro ①: đọc `pg_constraint` là gắn bộ kiểm vào PostgreSQL.** Dự án đã bỏ SQLite từ
change `drop-the-sqlite-escape-hatch` nên đây không phải mất mát mới, nhưng phải ghi rõ
ở chỗ đọc — không để người sau tưởng `audit_db.py` còn chạy đa hệ.

**Rủi ro ②: đổi "ĐẠT" thành "CẢNH BÁO" trên tập rỗng sẽ làm báo cáo audit đổi màu.**
Mốc hiện tại là 68 phép / 64 đạt / 4 lưu ý / 0 hỏng. Số lưu ý **sẽ tăng**, và đó là
đúng — chúng đang phơi ra những chỗ trước nay báo đạt mà chưa quan sát gì. Phải đo và
ghi lại con số mới, **không** hạ tiêu chuẩn để giữ màu cũ.

**Rủi ro ③: dễ tự lừa ở vế 2.** Cám dỗ lớn nhất của change này là để phép đối chiếu
cache chạy trên tập rỗng rồi tick xanh mục Master Plan. Thiết kế phải làm điều đó
**không thể xảy ra**, chứ không phải dặn nhau đừng làm.
