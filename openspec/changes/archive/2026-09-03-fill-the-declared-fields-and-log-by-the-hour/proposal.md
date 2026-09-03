# Điền nốt những trường đã khai, và ghi log theo giờ

Đóng **hai** mục Master Plan cạnh nhau, vì mục sau dùng đúng dữ liệu mục trước tạo ra:

```
   STT 4 muc tieu 1   "Ghi du truong can cho dashboard ngay tai thoi diem goi"   moc 21/09
   STT 4 muc tieu 2   "Ghi log dang time-series de theo doi xu huong"            moc 30/09
```

## Why

### ① Có cột không có nghĩa là có dữ liệu

Sản phẩm của mục tiêu 1 đòi *"bản ghi mỗi request gồm 12 trường"*. Đếm cột trên `fact_call`:
**12/12 đã có**. Nhưng đếm **dữ liệu thật** trên 41 dòng gateway thì khác hẳn:

```
   truong              dien / 41     ghi chu
   token vao                41/41
   token ra                 41/41
   token cache               0/41    <- BAT BUOC, RONG TOAN BO
   chi phi                  38/41    3 luot hong, dung
   ma tra ve                41/41
   do tre                   38/41    3 luot hong, dung
   model                    39/41    2 dong bi danh, dung
   provider                 39/41    tra qua dim_model
   agent                    41/41
   nguoi dung               41/41
   phong ban                 0/41    <- BAT BUOC, RONG TOAN BO
   thoi diem                41/41
```

Hai trường bắt buộc rỗng sạch. Và **hai trường đó rỗng vì hai lý do hoàn toàn khác nhau** —
gộp chúng làm một là sẽ sửa sai một cái.

**`phong ban` (`unit_id`) — thiếu đường nạp.** Suy được ngay: tài khoản 949 thuộc đơn vị
`__technical_6__`. `db/load_ralli.py` **có** ghi cột này; `db/load_gateway.py` không khai nó
trong `COLUMNS`. Đây là chuyện của ta, sửa được.

**`token cache` (`cached_tokens`) — KHÔNG phải lỗi bộ nạp.** Đếm từng trường con của
`usage_object` trên 42 lượt thành công:

```
   prompt_tokens_details.text_tokens        42/42  <- CO SO THAT
   completion_tokens_details.text_tokens    42/42  <- CO SO THAT
   prompt_tokens_details.cached_tokens       0/42  JSON null
   cache_read_input_tokens                   0/42  JSON null
   prompt_tokens_details.audio/image_tokens   0/42  JSON null
```

Khoá **có mặt**, giá trị là `null`. LiteLLM có **hai** chỗ riêng để ghi token cache
(`cached_tokens` và `cache_read_input_tokens`) và **cả hai đều rỗng** — nên đây không phải một
chỗ đọc nhầm. Bộ nạp đọc đúng chỗ và nhận đúng thứ nó nhận được.

Chuyện này chặn một mục khác của Master Plan: STT 7 mục tiêu 2 đòi *"phép kiểm riêng đối chiếu
token cache của Gateway với SKU cache trên hoá đơn Google"* — **không thực hiện được** khi vế
Gateway luôn rỗng.

Nhưng **hai** trường ta chưa từng đọc thì lại có số thật, và chúng là **hai chiều khác nhau**:

```
   prompt_tokens_details.text_tokens        token VAO la van ban
   completion_tokens_details.text_tokens    token RA  la van ban   <- Data Out so 15
```

Data Out số 15 là `output_modality`, nên nó tra ở **`completion_tokens_details`**, không phải
`prompt_tokens_details`. Bản đầu của đề xuất này trỏ nhầm khối — đo lại mới ra.

### ② Chưa bảng nào đo theo giờ

Sản phẩm mục tiêu 2 đòi *"log chuỗi thời gian phục vụ biểu đồ theo **ngày / giờ**"*. Đếm độ mịn
thật của cả 7 bảng `fact_*`:

```
   fact_app_daily · fact_billing_daily · fact_latency_daily
   fact_perf_daily · fact_usage_daily                          -> chi co `day`
   fact_call                                                   -> ts_local (timestamp)
   fact_monitoring                                             -> ts_local (timestamp)
```

**Không bảng tổng hợp nào có giờ, và API không có endpoint nào theo giờ.** Nhưng dữ liệu thô
thì đủ:

```
   fact_call  gateway      41 dong   ->   5 gio rieng biet
   fact_call  app       8.631 dong   -> 542 gio
   fact_monitoring    651.653 dong   -> 2.965 gio
   billing                             -> KHONG CO GIO, hoa don Google chi tinh theo ngay
```

Ba trong bốn nguồn xuống được tới giờ. Nguồn thứ tư thì **không bao giờ** — đó là giới hạn của
hoá đơn, không phải của ta, và bảng theo giờ phải nói thẳng điều đó thay vì ghi 0.

### ③ Phân vị chính xác — món nợ ghi từ change trước

`record-latency-and-outcome-per-gateway-call` design ⑥ đã hoãn việc này sang đúng mục tiêu 2,
và ghi rõ hai chuyện chưa chốt: ngưỡng số mẫu tối thiểu, và có gộp phân vị Gateway với phân vị
monitoring hay để cạnh nhau.

Nay đo được thêm một ràng buộc mà lúc đó chưa biết:

```
   fact_latency_daily   day, agent_id, samples, p50_seconds, p95_seconds,
                        p95_bucket_from, p95_bucket_to, p99_seconds, enough_samples
   fact_perf_daily      day, agent_id, method, response_code, calls
                        ^^^^ CA HAI DEU KHONG CO COT `source`
```

Hai bảng này **thuộc riêng nguồn monitoring**. Đổ số Gateway vào chúng là trộn hai phép đo khác
nhau vào một hàng mà không ai phân biệt được — đúng loại lỗi `source` đã sửa cho `fact_call`
ngày 31/08.

## What Changes

**Mục tiêu 1 — điền nốt hai trường bắt buộc**

- `db/load_gateway.py` khai `unit_id` trong `COLUMNS` và tra từ `account_id`.
- **Đo** vì sao `cached_tokens` luôn `null`: Gemini có báo không, LiteLLM có ánh xạ không, và
  hoá đơn Google có SKU cache cho những ngày đó không. Kết quả ghi vào tài liệu — **không** bịa
  số 0 vào chỗ chưa đo được.
- Nạp `output_modality` từ **`completion_tokens_details`** (Data Out số 15). Chiều vào
  (`prompt_tokens_details`) là một trường khác, không nằm trong 26 trường Data Out.

**Mục tiêu 2 — độ mịn theo giờ**

- Migration 008: bảng tổng hợp theo giờ, có cột `source`, khoá gồm giờ.
- `db/build_usage_hourly.py` dựng nó từ `fact_call` và `fact_monitoring`.
- Migration 008 thêm cột `source` cho `fact_latency_daily` và `fact_perf_daily`, để Gateway vào
  được mà không trộn với monitoring.
- `db/build_performance.py` tính p50/p95/p99 **chính xác** từ `duration_ms` thô của Gateway.
- Endpoint đọc theo giờ trong `backend/`, giữ kỷ luật chỉ-đọc.
- `scripts/audit_db.py`: phép kiểm tổng theo giờ phải bằng tổng theo ngày.

Không đụng: sổ `LiteLLM_SpendLogs` (chỉ đọc), tầng frontend, ba bộ số cũ.

## Impact

- Đóng **mục tiêu 1** thật sự, không phải chỉ trên giấy: 12/12 trường có cột **và** có dữ liệu.
- Đóng **mục tiêu 2**, và kéo mốc 30/09 về trước ~4 tuần.
- Gỡ chặn cho STT 7 mục tiêu 2 (đối chiếu token cache với SKU Google) — hoặc chứng minh được
  rằng nó **không** làm được, kèm lý do đo đạc.
- Phân vị độ trễ tính **chính xác** thay vì nội suy trong thùng histogram rộng 33,6 giây.
- Rủi ro chính là kích thước bảng. Bản đầu của mục này viết *"nhân lên tới 24 lần"* — **đoán,
  không đo**. Đếm thật ba cách khác nhau (khoá thiếu / khoá đủ / khoá đủ kèm bộ lọc thật) ra
  ba con số: hệ số **3,8 – 6,9 lần**, tổng khoảng **3.000 – 7.700 dòng**.

  Không cách nào chính xác tuyệt đối vì phép gộp phải dựng lại bằng tay — con số thật chỉ biết
  sau khi dựng (việc 6.5). Nhưng điều **chắc chắn** ở cả ba cách: không phải 24 lần, và bảng
  theo giờ sẽ **lớn hơn hoặc xấp xỉ `fact_billing_daily` (2.575)** — tức bảng tổng hợp lớn nhất
  hiện có. Vẫn thừa sức chịu, chỉ là không được gọi nó là nhỏ.

- Rủi ro thứ hai: `billing` **không có giờ**. Bảng theo giờ mà im lặng bỏ qua nguồn này sẽ làm
  người đọc tưởng chi phí theo giờ là đầy đủ. Phải nói rõ ở tầng dữ liệu, không phải ở tầng
  giao diện — xem design ③.
