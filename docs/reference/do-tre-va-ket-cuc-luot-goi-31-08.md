# Ghi độ trễ và kết cục của từng lượt gọi — nhật ký 31/08/2026

Đóng mục Master Plan *"Ghi đủ trường cần cho dashboard ngay tại thời điểm gọi"* (mốc 21/09).
Bản ghi mỗi request đòi **12 trường**; `fact_call` có 10, thiếu **độ trễ** và **mã trả về** —
cả hai đều đã nằm sẵn trong sổ Gateway, chỉ thiếu đường nạp.

Change: `record-latency-and-outcome-per-gateway-call`. Nhật ký trước:
`nap-so-gateway-vao-database-31-08.md`.

---

## 1. Lỗi nguy hiểm nhất: `ON CONFLICT DO NOTHING` bỏ qua dữ liệu cũ

Bắt được **sau khi** migration đã chạy và bộ nạp đã sửa, lúc soi tại sao một câu truy vấn trả
về rỗng.

```
   38 dong gateway cu   outcome = NULL   duration_ms = NULL
    3 dong moi nap      outcome = failure
```

Bộ nạp dùng `ON CONFLICT (call_id) DO NOTHING` để chạy lại được nhiều lần. Nhưng `DO NOTHING`
**bỏ qua hoàn toàn** dòng đã có — nên ba cột vừa thêm rỗng trên toàn bộ dữ liệu cũ.

Hai hậu quả nếu bỏ lọt, cả hai đều **im lặng**:

| | Hậu quả |
|---|---|
| ① | Thêm bộ lọc `outcome = 'success'` ở tầng tổng hợp → token gateway về **0**. Dashboard hiện "chưa có lưu lượng" trong khi dữ liệu vẫn nằm đủ trong bảng |
| ② | `duration_ms` NULL trên cả 38 dòng thành công → **mục đích chính của change không đạt được dòng nào** |

**Sửa:** đổi sang `DO UPDATE` cho **đúng ba cột mới**, không phải cả hàng:

```sql
   ON CONFLICT (call_id) DO UPDATE SET
       duration_ms = EXCLUDED.duration_ms,
       outcome     = EXCLUDED.outcome,
       error_code  = EXCLUDED.error_code
```

An toàn vì ba cột này suy từ chính sổ gốc, mà dòng trong sổ là **bất biến sau khi ghi**. Chạy
lại bao nhiêu lần cũng ra cùng giá trị.

**Cố ý không `DO UPDATE` cả hàng:** nếu mai kia một khâu ánh xạ đổi (ví dụ `dim_model_alias`),
ta **không** muốn lịch sử bị viết lại im lặng.

> Bài học chung: **thêm cột vào bảng đã có dữ liệu thì phải có đường nạp bù.** Migration chỉ
> tạo cột rỗng; nếu bộ nạp bỏ qua dòng cũ thì cột đó rỗng mãi mãi.

---

## 2. Lỗ rò 14 token — chứng minh TRƯỚC khi vá

Thiết kế nói rằng nạp lượt hỏng mà quên lọc ở tầng tổng hợp thì token của chúng sẽ rò. Thay vì
tin lời thiết kế, chạy thử để **chứng minh lỗ rò có thật**:

```
   chay build_usage_daily KHI CHUA co bo loc
   -> fact_usage_daily gateway = 45.201 token
                       dung la = 45.187 token
                       ro dung =      14 token
```

14 token đó là của **một** lượt hỏng mang tên model dạng upstream. Hai lượt hỏng còn lại mang
tên **bí danh** nên `model_id` ra NULL và đã bị điều kiện `model_id IS NOT NULL` chặn sẵn.

Sau khi vá, bốn nguồn khớp mốc tuyệt đối, không đổi một token nào.

Con số nhỏ, nhưng cơ chế thì không: nó rò **im lặng**, và tỉ lệ sẽ tăng khi có lượt hỏng **sau
khi** Router đã chốt tuyến (timeout, 429, 500) — loại lỗi chưa gặp lần nào.

---

## 3. Lý lẽ sai nguy hiểm hơn con số sai

Bản đầu của thiết kế viết: *"cả 5 lượt hỏng chết ở khâu xác thực, chưa từng chạm nhà cung cấp,
nên không có độ trễ để đo"*. Soi từng dòng thì **sai**:

```
   lop loi                do tre   ma     token   di den dau
   AuthenticationError       0     401     14     DA GOI GOOGLE, Google tu choi khoa
   ProxyException            0     403      0     chan o Gateway
   ValueError                0     (rong)  14     chan o Gateway (cau hinh tag)
   RouterRateLimitError      0     (rong)   0     khong tim duoc tuyen
   RouterRateLimitError      0     (rong)   0     khong tim duoc tuyen
```

Dòng đầu **đã ra tới Google** và bị Google từ chối — mà độ trễ **vẫn bằng 0**.

Lý do thật: **LiteLLM không ghi độ trễ cho lượt hỏng**, bất kể lượt đó đi được tới đâu.

Quyết định không đổi (0 → NULL), nhưng lý lẽ thì phải đúng. Nếu tin theo lý lẽ cũ, người đọc
sau sẽ tưởng lượt hỏng ở xa hơn sẽ có độ trễ thật — và sẽ ngạc nhiên khi nó vẫn bằng 0.

**Và năm dòng hỏng đó không cùng loại:** hai dòng `RouterRateLimitError` là **tàn dư phép kiểm
mồi của chính tôi** hôm 31/08, không phải sự cố thật của hệ thống.

---

## 4. Tách bộ đếm — một con số đáng báo động đừng chìm trong tiếng ồn

Sau khi nạp lượt hỏng, bộ đếm `khong_noi_duoc_model` trộn hai chuyện trái ngược:

```
   tuyen moi chua khai trong GATEWAY_MODELS   <- VIEC PHAI LAM
   luot hong TRUOC khi Router chot tuyen      <- binh thuong
```

Đã tách đôi. Chạy thật:

```
   model chua khai              0
   hong truoc khi chot tuyen    2
```

Cùng loại sai lầm với `whole_agent` mang hai nghĩa, đã ghi trong bản chốt 20/08.

---

## 5. Độ trễ: số thô hơn histogram bao nhiêu

```
   Gateway     p50 0,788 s  ·  p95 1,822 s  ·  p99 2,702 s
               tinh CHINH XAC tu 38 gia tri tho

   Monitoring  p95 63,6 s
               noi suy trong THUNG 33,55 - 67,11 giay
```

**Cái thùng rộng 33,6 giây.** Mọi p95 rút từ nó mang sai số hàng chục giây — đúng cái mà
`build_performance.py` đã cảnh báo về việc gộp histogram.

**Nhưng hai con số này CHƯA so được với nhau**, và đây là chỗ dễ vội:

- Monitoring dừng ở 28/08; Gateway chỉ có 31/08 — **khác giai đoạn, khác lưu lượng**
- Trước khi có Gateway, DMS gọi thẳng Google với file lớn; sau khi có Gateway thì mới đo
- Chưa xác định monitoring đang đo **phép đo nào**

Chênh 35 lần thì không thể quy cho sai số thùng. **Không kết luận bên nào đúng** — ghi lại
thành việc phải làm, không phải thành phát hiện.

---

## 6. Đã đụng vào những gì

| File | Việc |
|---|---|
| `db/migrations/**/006_*` | **Mới** — ba cột `duration_ms`, `outcome`, `error_code` |
| `db/load_gateway.py` | Đọc cả hai trạng thái · `NULLIF` cho độ trễ và mã lỗi · `DO UPDATE` · tách bộ đếm · in phân bố mã lỗi |
| `db/build_usage_daily.py` | `load_gateway()` lọc `outcome = 'success'` |
| `scripts/audit_db.py` | Hai phép kiểm mới |

**Change này đảo một quyết định** của `load-the-gateway-ledger-into-the-database`, mục ②:
*"Dòng `failure` không nạp vào `fact_call`"*. Lý do đảo: Master Plan đòi *"bản ghi mỗi
request"*, và ta đang vứt hết lý do hỏng trong khi câu trả lời nằm sẵn trong sổ.

---

## 7. Nghiệm thu

```
   migration      9/9 moc khop, 17 -> 20 cot, khong mat mot token nao
   bo nap         doi chieu: nguon 45 dong/45.257 token
                            = dich 41/45.201 + bo qua 4/56
   chay hai lan   41 -> 41 -> 41
   bon nguon cu   KHONG DOI mot token nao
   audit          38 phep kiem | 34 dat | 4 luu y | 0 hong
   doi soat moc   lech DUNG 1 khoa: fact_call +3 dong hong co y them
                  usage_resolved KHONG DOI -> bo loc outcome hoat dong
```

---

## 8. Còn chưa chắc

| | Mức |
|---|---|
| Ba cột nạp đúng, không hồi quy | **Chứng minh được** — mốc trước/sau, đối soát 24 khoá |
| Lỗ rò 14 token có thật | **Chứng minh được** — chạy thử trước khi vá |
| LiteLLM không bao giờ ghi độ trễ cho lượt hỏng | **Chỉ suy luận** — mới 5 mẫu, cả 5 bằng 0 |
| Monitoring p95 đo cái gì | **Chưa biết** — việc phải làm, không phải kết luận |
| Hành vi khi có lượt hỏng sau khi chốt tuyến | **Chưa quan sát được lần nào** |
