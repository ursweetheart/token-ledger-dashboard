# Làm mới mọi bảng mà Gateway chạm tới

`scripts/refresh_gateway.py` chạy **2 bước** trong khi đường dẫn Gateway nay đi qua **4**.
Hai bảng dẫn xuất bị bỏ lại, và chúng cũ đi **im lặng**.

Mọi con số đo trên database thật `token_ledger_v2` ngày **03/09/2026**.

## Why

### ① Hai bảng bị bỏ lại, và mỗi bảng chỉ có ĐÚNG MỘT người ghi

```
   rebuild_db.py         10 buoc  (day du)
   update_dashboard.py   goi rebuild_db.py       ->  KHONG dinh
   refresh_gateway.py     2 buoc  load_gateway · build_usage_daily
```

Đếm người ghi vào hai bảng dẫn xuất mới:

```
   fact_usage_hourly    <-  CHI db/build_usage_hourly.py    (4 lenh ghi)
   fact_latency_daily   <-  CHI db/build_performance.py     (3 lenh ghi)

   refresh_gateway.py goi KHONG CAI NAO
```

Hai bảng đó ra đời **sáng 03/09** (migration 008). `refresh_gateway.py` viết từ 31/08, khi
đường dẫn Gateway mới có hai bước — nó không sai lúc viết, nó **bị bỏ lại**.

### ② Hệ quả: dashboard nói sai, và không có dấu hiệu gì

```
   ① mot luot goi moi qua Gateway
   ② refresh_gateway   ->  fact_call +1 · fact_usage_daily DUNG LAI
   ③ fact_usage_hourly   KHONG dung lai  ->  so cu nam nguyen
      fact_latency_daily  KHONG dung lai  ->  phan vi cu nam nguyen
   ④ /api/usage-hourly va /api/performance phuc vu SO CU — IM LANG
   ⑤ lan chay audit_db.py ke tiep:
      "Hourly totals match daily totals (gateway)"  HONG
```

`audit_db.py` **có** bắt được — nhưng chỉ khi ai đó chạy nó. Giữa hai lần, dashboard trả về
số cũ mà không cột nào, không cảnh báo nào nói ra.

**Và chế độ mà chính docstring khuyến nghị làm cửa sổ đó không có giới hạn:**

```
   python scripts/refresh_gateway.py --every 120
```

Chạy vòng lặp hai phút một lần suốt buổi thì `fact_usage_daily` luôn mới còn
`fact_usage_hourly` cũ bằng đúng thời gian vòng lặp đã chạy.

### ③ Nhưng KHÔNG được thêm cả hai bước một cách ngây thơ

Đây là chỗ dễ sửa sai nhất, nên đo trước:

```
   db/build_usage_hourly.py    921 ms   doc fact_call + fact_monitoring
                                        KHONG phu thuoc file ngoai nao
   db/build_performance.py     394 ms   PHU THUOC MOT FILE THU CONG
```

`build_performance.py:100` **dừng hẳn** nếu thiếu
`data/raw_google_console/do_tre_phan_bo/latency-daily.csv` — file do
`pull_latency_distribution.py` + `merge_latency_daily.py` cào tay sinh ra. Đo hôm nay: file
ấy **cũ 4 ngày** (sửa lần cuối 30/08 01:05).

Thêm nó vào một script **chạy vòng lặp** là biến một chu kỳ nhẹ thành phụ thuộc vào một file
phải cào tay. Ngày file đó mất hoặc bị đổi chỗ, vòng lặp chết — và chết ở một nơi không ai
ngờ tới.

**May là không cần đến nó.** `build_performance.load_gateway_latency()` đọc **duy nhất**
`fact_call.duration_ms`; cả bốn chỗ nhắc `LATENCY_CSV` đều nằm ở nhánh `monitoring`. Phần
Gateway của bảng phân vị **tính được mà không cần CSV**.

Cản trở duy nhất là `main()` xoá **cả hai bảng** trước khi nạp lại:

```python
   cur.execute("DELETE FROM fact_perf_daily")
   cur.execute("DELETE FROM fact_latency_daily")
```

## What Changes

**① `refresh_gateway.py` làm mới đủ đường dẫn Gateway**

- Thêm `db/build_usage_hourly.py` vào `STEPS`. Nó không phụ thuộc file ngoài nào nên an toàn
  cho chế độ vòng lặp.
- Thêm bước làm mới **phần Gateway** của bảng phân vị — xem ②.
- Giữ nguyên kỷ luật đã có: **dừng ngay nếu một bước hỏng**, không tổng hợp trên dữ liệu
  thiếu.

**② `build_performance.py` nhận chế độ chỉ-Gateway**

- Cờ mới chạy `DELETE FROM fact_latency_daily WHERE source = 'gateway'` rồi
  `load_gateway_latency()`. **Không đọc CSV, không đụng `fact_perf_daily`, không đụng dòng
  `monitoring`.**
- Chế độ đầy đủ (mặc định) **giữ nguyên hành vi**: `rebuild_db.py` bước 9 không được đổi một
  chút nào.

**③ Phép kiểm canh chính khoảng trống này**

- `scripts/audit_db.py`: phép kiểm mới đối chiếu **mốc thời gian mới nhất** của `fact_call`
  nguồn gateway với mốc mới nhất trong `fact_usage_hourly` và `fact_latency_daily`. Lệch
  nghĩa là một bảng dẫn xuất đã cũ — bắt được **trước** khi tổng lệch.

**Không đụng:** `rebuild_db.py` (10 bước giữ nguyên), `update_dashboard.py` (đã gọi
`rebuild_db.py` nên không dính), sổ `LiteLLM_SpendLogs`, tầng frontend, migration nào.

## Capabilities

### New Capabilities

- `gateway-refresh-completeness`: đường làm mới nhanh phải phủ **mọi** bảng dẫn xuất mà nguồn
  đó nuôi, và phải phát hiện được khi một bảng bị bỏ lại.

### Modified Capabilities

*(không có — `hourly-time-series` và `latency-source-resolution` giữ nguyên mọi yêu cầu; change
này chỉ bảo đảm chúng được **làm mới**, không đổi định nghĩa của chúng.)*

## Impact

- `/api/usage-hourly` và `/api/performance` không còn phục vụ số cũ sau một lần refresh.
- Chu kỳ **~0,8 s → ~1,8 s** (thêm 921 ms cho bảng theo giờ, phần phân vị chỉ-Gateway chạy
  trên 41 dòng nên tính bằng mili giây). Vẫn rẻ với `--every 120`.
- Một khoảng mù được canh: bảng dẫn xuất cũ nay bị bắt bằng mốc thời gian, không phải đợi
  tổng lệch.

**Rủi ro ①: thêm bước là thêm chỗ hỏng cho một vòng lặp.** `build_usage_hourly.py` tự đối
chiếu tổng giờ với tổng ngày và **`SystemExit` nếu lệch** — đúng thứ ta muốn ở chế độ chạy
tay, nhưng ở chế độ `--every` nó sẽ làm vòng lặp báo lỗi mỗi chu kỳ cho tới khi người ta sửa.
Đó là hành vi **đúng** (im lặng thì tệ hơn), nhưng phải biết trước, và `refresh_gateway.py` đã
có sẵn nhánh bắt lỗi cho vòng lặp.

**Rủi ro ②: chế độ chỉ-Gateway dễ trôi khỏi chế độ đầy đủ.** Hai đường cùng ghi vào một bảng,
và bản sao thứ hai của một phép đo thì sẽ trôi — đúng bẫy đã dính 21/08. Phải dùng **cùng một
hàm** `load_gateway_latency()`, không chép lại phép tính.

**Rủi ro ③: `fact_latency_daily` bị xoá một phần.** `DELETE ... WHERE source = 'gateway'` viết
sai điều kiện là mất 339 dòng `monitoring` — mà chúng dựng lại được **chỉ khi** file CSV còn.
Nghiệm thu phải đếm dòng `monitoring` trước và sau, không chỉ đếm dòng gateway.
