# Thiết kế — ghi độ trễ và kết cục của từng lượt gọi

Mọi con số đo trên **45 dòng thật** trong `LiteLLM_SpendLogs` ngày 31/08/2026.

---

## ① Ba cột mới trên `fact_call`

| Cột | Kiểu | Vì sao |
|---|---|---|
| `duration_ms` | `INTEGER`, cho phép NULL | độ trễ thô của lượt gọi |
| `outcome` | `TEXT`, cho phép NULL | `success` / `failure`. NULL cho nguồn `app` — nhật ký Ralli không ghi kết cục |
| `error_code` | `TEXT`, cho phép NULL | mã lỗi khi hỏng. TEXT chứ không INTEGER — xem ④ |

Cả ba đều `ADD COLUMN` nullable không `DEFAULT`, nên PostgreSQL ghi vào siêu dữ liệu chứ không
viết lại bảng. Cùng đường đã dùng ở migration 004 và đã diễn tập ở 002/003.

**Không đụng `fact_perf_daily` và `fact_latency_daily`.** Hai bảng đó là bảng **dẫn xuất** của
nguồn monitoring, mỗi bảng một độ mịn riêng, và chúng chưa có cột `source`. Đưa Gateway vào
chúng là một change khác — thuộc mục "Ghi log dạng time-series" mốc 30/09.

## ② Độ trễ của lượt HỎNG phải là NULL, không phải 0

Đo được:

```
   status=success   609 – 3.136 ms   (trung binh 1.002, p95 1.805)
   status=failure   0 tren ca 5/5 dong
```

Số 0 đó **không phải một phép đo**. Nhưng lý do thì KHÔNG phải cái tôi tưởng lúc đầu — soi
từng dòng mới ra:

```
   lop loi                do tre   ma     token   di den dau
   AuthenticationError       0     401     14     DA GOI GOOGLE, Google tu choi
   ProxyException            0     403      0     chan o Gateway
   ValueError                0     (rong)  14     chan o Gateway (cau hinh tag)
   RouterRateLimitError      0     (rong)   0     khong tim duoc tuyen
   RouterRateLimitError      0     (rong)   0     khong tim duoc tuyen
```

Bản đầu của mục này viết *"cả 5 chết ở khâu xác thực, chưa từng chạm nhà cung cấp"*. **Sai.**
Dòng `AuthenticationError` **đã gọi Google** và bị Google từ chối khoá — vậy mà độ trễ **vẫn
là 0**.

Nên lý do thật là: **LiteLLM không ghi độ trễ cho lượt hỏng**, bất kể lượt đó đi được tới đâu.
Không phải "chưa chạm provider nên không có gì để đo".

Khác biệt này quan trọng. Nếu tin theo lý lẽ sai, người đọc sau sẽ tưởng lượt hỏng ở xa hơn
(timeout, 429, 500) sẽ có độ trễ thật — và sẽ ngạc nhiên khi nó vẫn bằng 0.

Quyết định **không đổi**: nạp 0 vào là kéo tụt mọi phân vị — p95 trên `[0,0,0,0,0, 609…3136]`
khác hẳn p95 trên `[609…3136]`. Đúng quy tắc 5: trường không đo được ghi NULL, không ghi 0.

Quy tắc viết là **NULL khi bằng 0** chứ không phải "NULL khi hỏng", để phòng trường hợp một
phiên bản LiteLLM sau này có ghi độ trễ cho lượt hỏng. **Chưa quan sát được trường hợp đó** —
đừng đọc thành đã biết.

## ③ Nạp cả lượt hỏng — đảo một quyết định của change trước

Change `load-the-gateway-ledger-into-the-database` chốt **không nạp** lượt hỏng, với lý do
chúng không phải lưu lượng thật. Change này **đảo lại**, vì Master Plan đòi *"bản ghi mỗi
request"* và một sổ lặng lẽ bỏ qua lượt hỏng thì không phải sổ đầy đủ.

Đo 31/08:

```
   5 luot hong  ->  3 quy duoc ve agent (co tag)   -> NAP
                    2 khong co tag                 -> van BO, van DEM
```

Hai dòng không có tag vẫn bị bỏ, vì `fact_call.agent_id` là `NOT NULL` — schema cưỡng chế,
không phải chính sách.

**Hệ quả bắt buộc phải xử:** `build_usage_daily.load_gateway()` hiện lọc
`source='gateway' AND model_id IS NOT NULL`. Thiếu `AND outcome = 'success'` là token của lượt
hỏng rò vào số liệu sử dụng. Đây là cùng một hình dạng lỗi đã gặp ngày 31/08 khi `fact_call`
đón nguồn thứ hai mà `load_app()` chưa lọc `source`.

Số rò **không phải 28** — soi từng dòng mới ra con số đúng:

```
   model                          token  ma loi  co tag   sau khi nap
   gemini-flash-lite                  0  ''      co       model_id NULL -> bi loc san
   gemini-flash-lite                  0  ''      co       model_id NULL -> bi loc san
   gemini/gemini-3.5-flash-lite      14  401     co       model_id 12   -> RO 14 TOKEN
   gemini-flash                       0  403     KHONG    khong nap
   gemini/gemini-3.5-flash-lite      14  ''      KHONG    khong nap
```

Chỉ **14 token** rò, không phải 28. Hai dòng hỏng mang tên **bí danh** thì `model_id` ra NULL
nên `model_id IS NOT NULL` đã chặn sẵn; dòng thứ ba mang tên upstream nên lọt qua được.

Con số nhỏ, nhưng cơ chế thì không: nó rò **một cách im lặng**, và tỉ lệ dòng hỏng mang tên
upstream sẽ tăng khi có lượt hỏng SAU khi Router đã chốt tuyến (timeout, 429, 500) — loại lỗi
mà hiện chưa gặp lần nào.

## ③b Bộ đếm "không nối được model" sẽ mang hai nghĩa

Sau change này, dòng hỏng dạng bí danh (`gemini-flash-lite`) vào bảng với `model_id` NULL, nên
bộ đếm `khong_noi_duoc_model` sẽ trộn hai chuyện khác hẳn nhau:

```
   tuyen moi chua khai trong GATEWAY_MODELS   <- viec phai lam
   luot hong TRUOC khi Router chot tuyen       <- binh thuong, khong phai loi
```

Phải **tách hai bộ đếm**, nếu không thì một con số đáng báo động sẽ chìm trong tiếng ồn
thường ngày. Cùng loại sai lầm với `whole_agent` mang hai nghĩa, đã ghi trong bản chốt 20/08.

## ④ `error_code` là TEXT, không phải INTEGER

Đo 5 dòng hỏng: **ba chuỗi rỗng**, một `401`, một `403`.

```
   (rong)  3 dong     <- RouterRateLimitError x2, ValueError x1
   401     1 dong
   403     1 dong
```

Chuỗi rỗng là **đa số**, không phải ngoại lệ — nên việc quy nó về NULL không phải chuyện nhỏ.

Chuỗi rỗng không ép sang số được. Và LiteLLM đặt trường này từ nhiều nguồn khác nhau
(`ProxyException`, lỗi của nhà cung cấp, lỗi mạng) nên không có gì bảo đảm nó luôn là số.

Chuỗi rỗng nạp thành **NULL** — cùng lý do với `end_user` ở change trước: rỗng nghĩa là không
biết, và `NULLIF` là chỗ duy nhất diễn đạt được điều đó.

## ⑤ `outcome` cho nguồn `app` để NULL, không đặt `'success'`

8.631 dòng cũ của Ralli **không có** thông tin kết cục — nhật ký của app không ghi. Đặt chúng
thành `'success'` là **bịa**: ta không biết chúng thành công hay không.

Khác với `source` ở migration 004, nơi `DEFAULT 'app'` là **đúng nghĩa** vì mọi dòng cũ thật
sự là của app.

## ⑥ Không tự tính phân vị trong change này

Change này chỉ **lưu số thô**. Việc tính p50/p95/p99 theo ngày thuộc mục Master Plan
"Ghi log dạng time-series" (mốc 30/09), và nó cần quyết định thêm hai chuyện chưa chốt:

- Ngưỡng số mẫu tối thiểu — `fact_latency_daily` hiện dùng `enough_samples` với ngưỡng 10 lượt
- Có gộp chung với phân vị từ monitoring hay để cạnh nhau như bốn nguồn token

Lưu thô trước là đúng thứ tự: phân vị tính lại được từ số thô, còn số thô thì không dựng lại
được từ phân vị.

---

## Những gì change này CỐ Ý không làm

- **Không đụng `fact_perf_daily` / `fact_latency_daily`** — bảng dẫn xuất của nguồn khác.
- **Không tính phân vị** — xem ⑥.
- **Không đụng tầng view và frontend** — chưa có ô nào cần hiển thị hai cột này.
- **Không nạp `error_message` và `traceback`** — chúng dài, có thể chứa nội dung request, và
  `error_code` đã đủ để phân loại. Muốn đọc chi tiết thì tra thẳng sổ gốc bằng `request_id`.
