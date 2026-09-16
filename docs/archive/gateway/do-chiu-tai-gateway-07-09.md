# Đo sức chịu tải API Gateway — nhật ký 07/09/2026

Đo trên máy dev, không phải máy chủ. Mục tiêu ban đầu là "bench 10k request xem chịu tải
tới đâu", nhưng thứ tìm được quan trọng hơn con số chịu tải: **hạn mức thật của Google
thấp hơn cấu hình 4 lần**, và **tồn tại một kiểu hỏng mà mọi cơ chế giám sát hiện tại đều
bỏ sót**.

---

## 1. Vì sao phải dựng sân riêng, không bench thẳng vào tuyến thật

Bench thẳng vào tuyến thật hỏng theo ba đường khác nhau cùng lúc:

| Đường bẩn | Hậu quả |
|---|---|
| Gọi Google thật | tốn tiền, ăn hạn mức của agent đang chạy |
| Ghi vào `LiteLLM_SpendLogs` thật | rác chảy vào `fact_call` → `fact_usage_daily` |
| Dùng chung Redis | bộ đếm `rpm/tpm` của agent thật bị bench tiêu mất |

Con số làm rõ mức nghiêm trọng: `fact_call` có **8.672 dòng** tích luỹ từ tháng 3. Một bài
10.000 lượt sẽ tạo ra khối rác **lớn hơn toàn bộ dữ liệu thật**, đúng 7 ngày trước cửa sổ
đối chiếu 14/09.

### Bốn lớp cách ly, mỗi lớp chặn một đường

```
   1. mock_response trong CẤU HÌNH TUYẾN  →  không lượt nào ra Google
   2. database `litellm_bench` riêng      →  sổ thật không nhận dòng nào
   3. KHÔNG khai Redis                    →  không đụng bộ đếm rpm/tpm
   4. cổng 4003, không qua gateway-lb     →  không nhiễu chính phép đo
```

Thêm một cái bẫy có chủ ý: **khoá Google của instance bench đặt giá trị cố ý sai**. Nếu vì
lý do nào đó mock không ăn và request đi ra thật, nó hỏng ngay và ồn ào (401) chứ không âm
thầm tiêu tiền. Chế độ hỏng phải là "không chạy", không phải "chạy mà không ai biết" — cùng
kỷ luật với `entrypoint.sh` và `DASHBOARD_KEY`.

**Cách ly đã được chứng minh, không phải tuyên bố:**

```
                     đầu buổi     cuối buổi
   SpendLogs THẬT        50    →      50      qua 51.223 lượt bench
   fact_call          8.672    →   8.672
   fact_usage_daily   1.990    →   1.990
   SpendLogs BENCH        0    →  51.223      ($2,7148 tiền giả)
```

$2,71 đó chính là số tiền không có thật đã **không** chảy vào sổ nhờ lớp thứ 2. Lớp 1 một
mình không đủ: `mock_response` **vẫn ghi sổ và vẫn tính giá**.

---

## 2. Đường bão hoà — trần ~150-170 req/s, bất kể đồng thời

Instance bench, trần bộ nhớ 1,5 GB, mock (không gọi Google):

| Người dùng | Thông lượng | p50 | p95 | p99 | Chậm nhất | Hỏng |
|---:|---:|---:|---:|---:|---:|---:|
| 5 | 134,5/s | 30 ms | 55 ms | 210 ms | 0,65 s | 0 |
| 50 | 157,8/s | 300 ms | 390 ms | 780 ms | 1,5 s | 0 |
| 200 | 149,8/s | 1,2 s | 2,1 s | 5,2 s | 9,5 s | 0 |
| 500 | 164,3/s | 1,7 s | — | — | 41,6 s | 0 |
| 1.000 | 162,4/s | 1,6 s | 8,8 s | 29 s | 37,6 s | 0 |
| 1.500 | 149,5/s | 1,7 s | — | — | 43,6 s | 0 |
| 3.000 | 97,5/s | 1,4 s | — | — | 44,7 s | 0 |
| 5.000 | 107,6/s | 1,4 s | — | — | 41,8 s | 450 (9,2%) |
| 8.000 | 154,6/s | 1,8 s | 9,9 s | 37 s | 50,5 s | 6 (0,08%) |
| 10.000 | 172,2/s | 2,1 s | 7,6 s | 38 s | 59,7 s | 0 |

Tăng đồng thời **gấp 2.000 lần** chỉ đổi được **28% thông lượng**. Toàn bộ phần tải thêm
biến thành thời gian xếp hàng.

**Hệ không gãy — nó hoá thành hàng đợi.** Không kết nối nào bị từ chối, không sập dây
chuyền. Vài lỗi xuất hiện ở mức 5.000-8.000 đều là `HTTP 0`, tức **client không mở nổi kết
nối**, không phải server từ chối.

Hành vi này lành, nhưng nó cũng có nghĩa: **quá tải không báo bằng lỗi, mà báo bằng người
dùng ngồi đợi 38 giây** — thứ không sinh ra dòng cảnh báo nào.

### Nút thắt là CPU của LiteLLM, không phải database

Đo trực tiếp lúc đang tải:

```
   token-ledger-litellm-bench   105%   ← ghim chặt MỘT lõi
   token-ledger-postgres        0,4%   ← rảnh rỗi
```

Container thấy **16 CPU**, LiteLLM ghim đúng **một lõi**, và `num_workers` **không được khai
ở đâu cả** — tức đang chạy mặc định một worker.

> **Việc rẻ nhất chưa ai làm:** đặt `num_workers`. Đang dùng 1/16 lõi.
> *Chưa đo* — "tăng worker sẽ tăng thông lượng gần tuyến tính" là suy luận.

---

## 3. Không thể làm nó OOM bằng số kết nối

120 mẫu liên tục trong lúc tải nặng:

```
   Bộ nhớ    : 1,00 → 1,12 GiB   (trần 1,465 GiB — chưa bao giờ chạm)
   CPU       : đỉnh 137%
   Trạng thái: "running" ở 120/120 mẫu, OOMKilled=false
```

Hàng đợi nằm ở **tầng socket**, không nằm trong bộ nhớ ứng dụng. Nên không có đường nào dẫn
tới OOM bằng cách tăng đồng thời, kể cả ở 8.000 kết nối.

Thêm một con số bị lật: **1,1 GB không phải nhu cầu thật**. Siết trần xuống 700 MB thì nó
chạy bằng **264 MB** và vẫn khoẻ — phần lớn 1,1 GB kia là bộ đệm thu hồi được mà Docker vẫn
tính vào.

---

## 4. PHÁT HIỆN QUAN TRỌNG NHẤT: hỏng mà không chết

Ép thiếu bộ nhớ (trần 700 MB, dưới mức nó muốn dùng), rồi đặt tải 3.000 người dùng:

| | Trần 1,5 GB | Trần 700 MB |
|---|---:|---:|
| Thông lượng | 97 req/s | **46 req/s** |
| p90 | ~3 s | **17 s** |
| p95 | ~10 s | **24 s** |
| Bộ nhớ | 1,10/1,46 GiB | **700/700 MiB — kịch trần** |
| CPU | ổn định ~100% | **giật cục 100% → 33% → 102% → 28%** |

Thông lượng **giảm còn một nửa**, p95 từ vài giây thành **24 giây**. CPU giật cục là dấu
hiệu kernel đang vật lộn thu hồi bộ nhớ thay vì làm việc.

**Và mọi cơ chế báo sức khoẻ đều nói "khoẻ":**

```
   OOMKilled       = false
   status          = running
   Docker health   = healthy
   /health/liveliness → HTTP 200  (7,3 giây)
                     → HTTP 200  (4,6 giây)
                     → HTTP 200  (0,006 giây)
```

### Vì sao không cơ chế nào bắt được

```
   nginx bản mở nguồn : chỉ đếm LỖI THẬT. Instance này không trả lỗi —
                        nó trả 200 sau 24 giây. nginx thấy mọi thứ bình thường.

   Docker healthcheck : interval 10s · timeout 5s · retries 18
                        → phải hỏng LIÊN TỤC 18 lần = 180 giây mới bị đánh dấu
                        → và chỉ cần MỘT lần trả lời nhanh là đếm lại từ đầu
```

Lượt đo thứ ba trả lời trong 0,006 giây — đúng cái làm bộ đếm reset. Trong thực tế, một
instance ốm kiểu này **có thể không bao giờ bị đánh dấu là ốm**, trong khi người dùng chờ
24 giây mỗi lượt.

**`retries: 18` là con số nên xem lại.**

---

## 5. Định tuyến trên cặp thật khi một instance chết

Nạp tải vào `/health/liveliness` qua `gateway-lb`. Đường này đi qua upstream (chính
`nginx.conf` ghi vậy), nên đo đúng quyết định định tuyến mà không tốn một xu.

| | Cả hai khoẻ | `litellm-2` chết | Sau khôi phục |
|---|---:|---:|---:|
| Thông lượng | 1.257/s | **37,8/s** | 1.319/s |
| p50 | 18 ms | 25 ms | 14 ms |
| p95 | 68 ms | **10.015 ms** | 52 ms |
| litellm-1 | 202 | **403** | 221 |
| litellm-2 | 204 | **0** | 185 |

**nginx CÓ loại được instance chết** — `litellm-2` nhận đúng 0 lượt.

**Nhưng cái giá thì tàn khốc:** thông lượng sụt **33 lần** trong khi instance còn lại hoàn
toàn khoẻ và thừa sức gánh. p95 nhảy lên đúng ~10 giây — đó là **timeout được trả bằng
request của người dùng thật**. Cơ chế `max_fails=2 fail_timeout=30s` nghĩa là: loại ra 30
giây, rồi **tự động cho vào lại**, và mỗi vòng lại phải có 2 request nữa chết mới loại tiếp.

Nên câu *"nginx loại được instance chết"* đúng nhưng dễ gây hiểu nhầm. Đầy đủ hơn: **nó
loại ra, rồi lại thử lại mãi, và mỗi lần thử lại đều tính tiền bằng trải nghiệm người dùng.**

### Ca "sống mà hỏng" — CHƯA đo được trên cặp thật

Siết 400 MiB → crash-loop (restarts 2→8). Nới 600 MiB → vẫn crash-loop (restarts=10).
Dừng ở lần thứ ba, không dò tiếp.

```
   Bench (cấu hình đơn giản)  : CÓ dải giữa — 700 MiB thì ốm mà vẫn sống
   Cặp thật (3 tuyến + Redis) : KHÔNG có dải giữa — hoặc khoẻ, hoặc chết hẳn
```

LiteLLM với cấu hình thật ăn ~855 MiB và hành xử **nhị phân**. Muốn ép ca kia phải dùng
đường khác — làm chậm đĩa, chèn độ trễ nhân tạo — không phải bằng bộ nhớ.

**Ca nguy hiểm nhất vẫn chỉ chứng minh được ở sân bench.**

---

## 6. Hạn mức thật của Google: 15 rpm, không phải 60

Gọi thật 100 lượt qua tuyến thật, model `gemini-flash-lite`:

```
   100 lượt · 191 giây · 0,52 lượt/giây
       200 :  53
       429 :  27
        -1 :  20   (hết giờ chờ 60 giây)
```

Log cho nguyên văn nguồn gốc:

```
   quotaId    : GenerateRequestsPerMinutePerProjectPerModel-FreeTier
   quotaMetric: generativelanguage.googleapis.com/generate_content_free_tier_requests
   limit      : 15        ← mỗi phút, mỗi project, mỗi model
   model      : gemini-3.5-flash-lite
```

**`rpm: 60` trong `config.gateway.yaml` cao gấp 4 lần trần thật của Google.** Nó không bao
giờ kích hoạt — LiteLLM thả 60 lượt/phút đi qua, Google từ chối mọi thứ sau lượt thứ 15.
Nâng con số đó lên là vô ích.

### `num_retries: 3` biến hạn mức thành độ trễ và timeout

```
   Khách gửi      : 100 lượt
   Google từ chối : 140 lần  (80 ở litellm-1 + 60 ở litellm-2)
```

Số lần bị từ chối **nhiều hơn số lượt gửi** — mỗi lượt hỏng được thử lại 3 lần, mỗi lần đều
chắc chắn 429. Hai mươi lượt chết ở mốc 60 giây trong lúc vẫn đang thử lại. Log có cả câu
Google dặn: `Please retry in 55.7s`.

Hạn mức không hiện ra dưới dạng "bị từ chối" mà dưới dạng **người dùng ngồi đợi rồi hỏng**.

### Chỗ nó chạm vào mốc 14/09

Lưu lượng thật cao nhất đã ghi được, từ `fact_call`:

| Phút | Lượt |
|---|---:|
| 2026-05-28 15:52 | **46** |
| 2026-06-21 02:13 | 38 |
| 2026-06-21 02:17 | 38 |
| 2026-05-28 15:54 | 37 |

**Đỉnh thật 46 lượt/phút. Trần free tier 15.** Gấp hơn ba lần — và đó mới là *một* agent.

Kế hoạch định 14/09 chuyển nốt 7 agent còn lại qua Gateway. Với **một khoá duy nhất** như
hôm nay, cả 8 agent chia nhau đúng 15 lượt/phút cho mỗi model.

Nhưng hạn mức là **15 rpm mỗi project mỗi model**, nên **8 project = 8 lần 15 rpm**. Việc
"8 tuyến / 8 project" mà `config.gateway.yaml` đã ghi chú **không phải cho gọn gàng — nó
chính là thứ làm cho trần 15 rpm sống được.** Chưa có nó thì 14/09 không chuyển được 8 agent.

### Vertex là đường thoát, và nó có sẵn

Gọi thử trên `token-ledger-test`, cả bốn model đều **HTTP 200**, `trafficType: ON_DEMAND`:

| Model | Vertex |
|---|---|
| `gemini-2.5-flash-lite` | 200 |
| `gemini-3.5-flash-lite` | 200 |
| `gemini-3.6-flash` | 200 |
| `gemini-3-flash-preview` | 200 |

Vertex và AI Studio là **hai đường riêng**: hạn mức riêng, hoá đơn riêng, project riêng.
Và mã nguồn DMS **đã hỗ trợ Vertex sẵn** (`gemini_client.py:34`, và `vertex` còn là backend
mặc định ở `settings.py:36`), không có danh sách trắng model nào chặn.

Lưu ý: project của DMS — `feedback-dms-tiep-thi` — **chưa bật Vertex API**.

---

## 7. Ba việc rút ra, theo thứ tự rẻ trước

1. **Hạ `rpm: 60` xuống ≤ 15.** Để LiteLLM tự tiết chế tại chỗ thay vì đốt 3 lần thử lại
   vào những lượt chắc chắn bị từ chối. Sửa một dòng.
2. **Xem lại `retries: 18`** trong healthcheck — nó khiến kiểu hỏng ở §4 gần như không thể
   bị phát hiện.
3. **Cấp đủ khoá theo project trước 14/09**, hoặc chuyển sang Vertex, hoặc lùi mốc chuyển
   8 agent. Ba lựa chọn, phải chọn một.

---

## 8. Sai lầm đã mắc trong lúc đo, ghi lại để không lặp

**`mock_response` đặt trong THÂN request bị tuyến thật bỏ qua.** Chỉ có `mock_response`
khai trong `litellm_params` của cấu hình tuyến mới ăn.

Hậu quả: ba dòng tôi từng ghi là "mock ghi vào sổ kèm tiền tính sẵn" **thực ra là ba lượt
gọi Google thật**. Phát hiện khi thấy latency 1.500 ms và đọc thân trả về — một câu trả lời
thật, không phải chuỗi mock.

Nguyên nhân gốc: **nhìn mã 200 rồi kết luận, không đọc thân.** Đúng cái bẫy đã được cài
phép kiểm để tránh trong `locustfile.py` (mỗi lượt đều đòi đúng chuỗi mock, sai thì đếm là
hỏng dù HTTP 200), nhưng lại tự mắc khi dùng `curl` tay.

Cái giá: hôm nay sổ thật nhận **241 dòng gọi Google thật, $0,0068, 5.393 token**, và ăn vào
hạn mức free tier.

---

## 9. Công cụ để lại

| File | Dùng để |
|---|---|
| `docker/gateway/config.bench.yaml` | tuyến `bench-mock`, không hạn mức, khoá Google cố ý sai |
| `docker-compose.bench.yml` | service `litellm-bench`, profile `bench`, cổng 4003, DB riêng, trần bộ nhớ đặt qua `BENCH_MEM_LIMIT` |
| `tools/bench/locustfile.py` | nạp tải; **đòi đúng chuỗi mock**, không lấy HTTP 200 làm bằng chứng |
| `tools/bench/goi_thu_tuyen_that.py` | gọi thật, **chốt cứng 100 lượt bằng hằng số** chứ không bằng thời lượng |
| `tools/bench/do_dinh_tuyen_khi_om.py` | đo phân bố định tuyến qua `gateway-lb`, không tốn tiền |

Dựng sân bench:

```
docker compose -f docker-compose.yml -f docker-compose.bench.yml \
  --profile bench up -d litellm-bench
```

Dọn: `down litellm-bench` rồi `DROP DATABASE litellm_bench`.
