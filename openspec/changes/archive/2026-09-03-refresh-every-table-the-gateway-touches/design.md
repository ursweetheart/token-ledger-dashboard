# Thiết kế — làm mới mọi bảng mà Gateway chạm tới

Mọi con số đo trên database thật `token_ledger_v2` ngày **03/09/2026**.

## Context

Ba bộ điều phối, ba phạm vi khác nhau — và chỉ một cái bị bỏ lại:

```
   rebuild_db.py         10 buoc   dung lai CA database tu file (~78 giay)
   update_dashboard.py   goi rebuild_db.py o buoc 8/9   ->  KHONG dinh
   refresh_gateway.py     2 buoc   lam moi duong Gateway (~0,8 giay)
```

`refresh_gateway.py` ra đời **31/08/2026** (commit `44997a8`), khi đường dẫn Gateway đúng là
hai bước: `load_gateway` → `build_usage_daily`. Nó **không sai lúc viết**.

Sáng **03/09** migration 008 thêm hai bảng dẫn xuất nữa mà nguồn gateway nuôi:

```
   fact_usage_hourly    <-  CHI db/build_usage_hourly.py
   fact_latency_daily   <-  CHI db/build_performance.py
```

`refresh_gateway.py` không được cập nhật theo. Đây là một khoản nợ **có ngày sinh cụ thể**,
không phải một thiếu sót từ đầu.

## Goals / Non-Goals

**Goals:**

- Sau một lần `refresh_gateway.py`, **mọi** bảng dẫn xuất mà nguồn gateway nuôi đều mới.
- Giữ script đủ nhẹ và đủ **độc lập** để chạy vòng lặp — không kéo thêm phụ thuộc vào file
  phải cào tay.
- Có phép kiểm bắt được **bảng dẫn xuất bị bỏ lại**, và bắt **trước** khi tổng lệch.

**Non-Goals:**

- **Không** đổi `rebuild_db.py`. Mười bước của nó giữ nguyên từng chữ.
- **Không** đổi hành vi mặc định của `build_performance.py` — chế độ đầy đủ phải y hệt.
- **Không** đụng `update_dashboard.py`: nó gọi `rebuild_db.py` nên vốn đã đủ.
- **Không** viết migration. Đây là change về **đường làm mới**, không về schema.

## Decisions

### ① Thêm `build_usage_hourly`, nhưng KHÔNG thêm `build_performance` nguyên bản

Đo hai bước trước khi quyết:

```
   db/build_usage_hourly.py   921 ms   doc fact_call + fact_monitoring
                                       KHONG phu thuoc file ngoai nao
   db/build_performance.py    394 ms   PHU THUOC latency-daily.csv
```

`build_performance.py:100` **dừng hẳn** nếu thiếu
`data/raw_google_console/do_tre_phan_bo/latency-daily.csv` — file cào tay, đo hôm nay **cũ 4
ngày** (30/08 01:05).

**Quyết định: `build_usage_hourly` vào thẳng `STEPS`; `build_performance` thì KHÔNG.**

Lý do không phải thời gian chạy — 394 ms rẻ hơn 921 ms. Lý do là **hạng phụ thuộc**:

```
   build_usage_hourly    doc DATABASE       -> tu chua duoc, chay vong lap an toan
   build_performance     doc MOT FILE TAY   -> vong lap chet ngay file do mat cho
```

Một script chạy `--every 120` suốt buổi mà phụ thuộc vào file phải cào tay là một quả bom hẹn
giờ đặt ở nơi không ai nhìn.

### ② Chế độ chỉ-Gateway: dùng CÙNG hàm, không chép phép tính

Đếm bốn chỗ nhắc `LATENCY_CSV` trong `build_performance.py`:

```
   dong  44   hang so o muc module
   dong 100   load_latency():  if not LATENCY_CSV.exists()
   dong 102   load_latency():  thong bao loi
   dong 108   load_latency():  mo file

   load_gateway_latency():  0 lan nhac
```

**Phần Gateway của bảng phân vị tính được mà không cần CSV** — nó đọc duy nhất
`fact_call.duration_ms`. Cản trở duy nhất là `main()` xoá cả hai bảng trước khi nạp:

```python
   cur.execute("DELETE FROM fact_perf_daily")
   cur.execute("DELETE FROM fact_latency_daily")
```

**Quyết định: một cờ chạy đúng hai việc —**

```
   DELETE FROM fact_latency_daily WHERE source = 'gateway'
   load_gateway_latency(cn, dc)        <- DUNG HAM CU, khong chep lai
```

**Bắt buộc gọi lại chính `load_gateway_latency()`.** Chép phép tính percentile sang một chỗ
thứ hai là tạo bản sao của một phép đo, và bản sao **sẽ trôi** — đúng bẫy đã dính ngày 21/08
khi `tools/dien_tap_gateway.py` chép câu SQL của `store.py` rồi đo bằng logic đã bị bỏ.

**Chế độ mặc định giữ nguyên từng chữ.** `rebuild_db.py` bước 9 gọi nó không tham số, và bước
đó không được đổi hành vi — nó là chỗ duy nhất dựng lại phần `monitoring`.

### ③ `DELETE` có điều kiện là chỗ nguy hiểm nhất của change này

`fact_latency_daily` hôm nay có **340 dòng: monitoring 339, gateway 1**.

Viết sai điều kiện — quên `WHERE`, hoặc gõ nhầm tên nguồn — là mất **339 dòng monitoring**. Và
chúng chỉ dựng lại được **khi file CSV còn**, tức phục hồi phụ thuộc vào đúng cái file mà
quyết định ① vừa tránh phụ thuộc.

**Quyết định: nghiệm thu phải đếm CẢ HAI nguồn, trước và sau.**

```
   truoc:  monitoring 339 · gateway 1
   sau  :  monitoring 339 · gateway 1      <- monitoring PHAI khong doi
```

Đếm mỗi dòng gateway thì một lệnh `DELETE` mất `WHERE` vẫn cho kết quả "đúng" — gateway vẫn
ra 1 dòng sau khi nạp lại. Đây đúng loại lỗi mà cả dự án này đi chống: **kết quả trông đúng
trong khi thứ khác đã mất**.

### ④ Phép kiểm bắt bảng cũ — bằng MỐC THỜI GIAN, không đợi tổng lệch

`audit_db.py` đã có `Hourly totals match daily totals (gateway)`. Nó **bắt được** khoảng trống
này, nhưng bắt **muộn**: chỉ khi tổng đã lệch, tức đã có dữ liệu mới bị bỏ lại.

Có một dấu hiệu sớm hơn: **mốc thời gian mới nhất**.

```
   fact_call source='gateway'   MAX(ts_local)::date
   fact_usage_hourly gateway    MAX(hour)::date
   fact_latency_daily gateway   MAX(day)
```

Ba con số này phải bằng nhau. Lệch nghĩa là một bảng dẫn xuất **đã cũ** — và nó lệch ngay ở
lượt gọi đầu tiên của một ngày mới, trước khi tổng kịp lệch đủ để ai chú ý.

**Quyết định: thêm phép kiểm mốc thời gian, mức HỎNG.** Đây là chỗ sửa được bằng cách chạy
lại — đúng ranh giới HỎNG/CẢNH BÁO mà `audit_db.py` đã chốt.

Áp cơ chế mẫu số của change trước: **0 dòng gateway → CHƯA KIỂM ĐƯỢC**, không phải ĐẠT.

### ⑤ Vòng lặp: một bước hỏng thì kêu mỗi chu kỳ, và đó là ĐÚNG

`build_usage_hourly.py` tự đối chiếu tổng giờ với tổng ngày và **`SystemExit` nếu lệch**. Ở
chế độ chạy tay đó là hành vi mong muốn. Ở chế độ `--every 120` nó sẽ báo lỗi **mỗi hai
phút** cho tới khi có người sửa.

**Quyết định: giữ nguyên, không nới.** Im lặng thì tệ hơn nhiều — đó chính là khoảng trống mà
change này đang bịt. `refresh_gateway.py` đã có sẵn nhánh bắt lỗi cho vòng lặp
(`try/except Exception` quanh `mot_luot`), nên một bước hỏng không giết vòng lặp; nó chỉ kêu.

Docstring của `refresh_gateway.py` phải nói trước điều này, để người bật `--every` không tưởng
mình vừa làm hỏng cái gì.

### ⑥ Thứ tự bước là bắt buộc, không phải tuỳ

```
   1  load_gateway         fact_call
   2  build_usage_daily    fact_usage_daily   (doc fact_call)
   3  build_usage_hourly   fact_usage_hourly  (doc fact_call, TU DOI CHIEU voi buoc 2)
   4  build_performance --<co>   fact_latency_daily gateway  (doc fact_call)
```

Bước 3 **phải sau** bước 2: nó đối chiếu tổng của mình với `fact_usage_daily` và dừng hẳn nếu
lệch. Đảo thứ tự là nó so với bảng ngày **cũ** rồi báo lệch giả.

## Risks / Trade-offs

**Chu kỳ dài gấp đôi.** ~0,8 s → ~1,8 s (thêm 921 ms cho bảng theo giờ; phần phân vị chỉ-Gateway
chạy percentile trên 41 dòng nên tính bằng mili giây). Với `--every 120` thì 1,8 s trên 120 s
là 1,5% — không đáng bàn. Nhưng con số phải **đo lại** sau khi sửa, không suy từ phép cộng.

**Hai đường cùng ghi vào `fact_latency_daily`.** Chế độ đầy đủ và chế độ chỉ-Gateway. Rủi ro
là chúng trôi khỏi nhau. Giảm bằng cách bắt buộc dùng **cùng một hàm** — quyết định ② — và
bằng phép kiểm mốc thời gian ở ④ soi kết quả chứ không soi đường đi.

**Phép kiểm mốc thời gian có thể báo giả trong một trường hợp.** Nếu lượt gọi Gateway mới nhất
rơi vào một ngày mà `build_usage_hourly` lọc bỏ (`outcome != 'success'`, hoặc `model_id` NULL),
thì `fact_call` có ngày mới hơn hai bảng kia một cách **hợp lệ**. Phải so trên đúng tập dòng mà
tầng tổng hợp nhận, không so `MAX` thô — nếu không ta vừa thêm một báo động giả, và báo động
giả thì sẽ bị tắt.
