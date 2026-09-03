# Nhật ký 03/09/2026 — ba change đóng trong một ngày

Tên file giữ hậu tố `-sang` vì phiên sáng viết trước; phiên chiều nối vào từ mục 10.

**Sáng:** `fill-the-declared-fields-and-log-by-the-hour` (59/59) và
`answer-what-each-agent-did-on-a-day` (48/48).
**Chiều:** `extend-the-checks-to-gateway-data` (40/40).

Tiếp theo `soat-stt6-tich-hop-03-09.md`. Đọc nhanh: mục 1, mục 4, mục 7.

Buổi sáng triển khai change `fill-the-declared-fields-and-log-by-the-hour` từ **17/54** lên
**50/59** việc. Bốn việc nghiệm thu cuối (10.1–10.4) hoãn có chủ ý — chúng cần chạy
`rebuild_db.py`, mà lệnh đó xoá sạch quyền đọc của API, và change kế tiếp mới bịt lỗ hổng đó.

---

## 1. Tóm tắt

```
   LAM DUOC
     ① migration 008        2 cot fact_call + 2 cot `source` + bang theo gio
     ② load_gateway.py      doc `completion_tokens_details`
     ③ build_usage_hourly   3.327 dong, tu doi chieu voi bang ngay
     ④ build_performance    phan vi Gateway tu so THO -> p95 = 1,822 s
     ⑤ /api/usage-hourly    BAT BUOC khoang thoi gian
     ⑥ audit_db nhom F      12 phep moi, tat ca DAT
     ⑦ check_api theo_gio   6 phep moi

   BAT DUOC (khong di tim)
     ⑧ DO UPDATE khong du - phai `--full`      6/41 dong
     ⑨ thinking_enabled 0/41, va do la DUNG    2 dong co reasoning bi loai
     ⑩ design ⑧ ghi sai KIEU du lieu           TEXT chu khong phai BOOLEAN
     ⑪ check_api.py mang mot phep kiem LOI THOI tu 31/08
```

Điểm chung của bốn cái bắt được: **cả bốn đều hỏng theo kiểu trả về số đúng.** Không cái nào
crash. Cái nguy hiểm nhất (⑪) báo HỎNG cho một hệ thống đang đúng — nếu ai đó "sửa" bằng cách
nới ngưỡng thì đã xoá mất một phép kiểm thật.

---

## 2. Migration 008 — ba việc một lần

```
   fact_call            + output_modality TEXT
                        + thinking_enabled BOOLEAN
   fact_latency_daily   + source, VAO KHOA CHINH (day, agent_id, source)
   fact_perf_daily      + source, VAO KHOA CHINH (day, agent_id, method,
                                                  response_code, source)
   fact_usage_hourly    bang moi, 5 chieu khoa nhu bang ngay
```

`source` phải vào **khoá chính**, không phải cột phụ. Thiếu thì dòng Gateway đụng khoá với dòng
monitoring của cùng một ngày — hoặc `INSERT` hỏng, hoặc tệ hơn, `DO UPDATE` ghi đè và mất một
nguồn mà tổng vẫn "khớp".

339 dòng latency và 669 dòng perf cũ nhận `DEFAULT 'monitoring'`. **Đây là DEFAULT đúng nghĩa**,
khác hẳn `outcome` ở migration 006 nơi một DEFAULT sẽ là bịa: hai bảng đó thật sự dựng từ
monitoring, đó là toàn bộ nội dung của chúng cho tới hôm nay.

Nghiệm thu: **24/24 khoá mốc khớp, 0 lệch**, head = `008_theo_gio`.

---

## 3. Bảng theo giờ — 3.327 dòng, và một ước lượng sai hướng

```
   monitoring  2.624 dong        1.751 gio rieng biet tren 153 ngay
   app           698 dong
   gateway         5 dong
   billing         0 dong    <- va se KHONG BAO GIO co
```

Mốc 1.4 đếm **ba cách** ra hệ số 3,8–6,9 lần. Thật ra là **1,67 lần** (3.327/1.990). Vẫn nằm
trong khoảng tổng 3.000–7.700 nên không phải lỗi, nhưng nguyên nhân đáng ghi: ước lượng đếm
trên `fact_monitoring` **thô**, còn bảng thật gộp theo `account_id` neo — nên nó đếm nhiều
tổ hợp hơn thực tế.

**Đối chiếu giờ ↔ ngày, CHO TỪNG NGUỒN** (bộ dựng tự `SystemExit` nếu lệch):

```
   gateway        45.187 =      45.187    calls      38 =      38   DAT
   monitoring 496.933.793 = 496.933.793   calls 111.290 = 111.290   DAT
   app         50.068.543  <- so voi PHAN fact_call cua nguon app   DAT
               (bang ngay 112.775.370 vi TLA Hop Dong o
                fact_app_daily, gop san theo ngay, KHONG co gio)
```

So **tổng chung** thì chắc chắn lệch, và không có gì sai — gộp lại thành một con số là biến một
sự thật đã biết thành báo động giả, rồi người ta sẽ tắt phép kiểm đi.

Một rủi ro số học đã đo và bịt trước: `int()` **cắt** ở mức giờ trong khi bảng ngày cắt ở mức
ngày, nên cộng 24 số đã cắt có thể khác cắt một lần. Đo: **0/62.785** dòng monitoring có phần
lẻ, nên hôm nay không lệch. Không dựa vào đó — phép đối chiếu ở trên mới là thứ giữ an toàn.

---

## 4. Phân vị Gateway — nghiệm thu khớp, nhưng lộ ra một câu chưa trả lời được

```
   2026-08-31  agent 6  source=gateway  38 mau
      p50 0,788 s · p95 1,822 s · p99 2,702 s
      p95_bucket_from/to = NULL          <- so tho khong co sai so noi suy
      enough_samples = true
```

**p95 = 1,822 s khớp đúng con số change 006 tính tay.** Phép tính đúng.

Nhưng so với nguồn thủ công cho **cùng agent 6**:

```
   thu cong (histogram Google)   p95 TB 58,206 s   p50 TB 19,66 s   681 mau
   gateway  (duration_ms tho)    p95     1,822 s   p50     0,788 s   38 mau
                                     ^ lech 31,9 lan      ^ lech 24,9 lan
```

Ba phép đo loại trừ các giải thích dễ dãi:

```
   (a) KHONG phai o histogram rong
       38 luot Gateway: min 609 ms · max 3.136 ms · TB 1.003 ms
       tren 10 giay: 0 luot        tren 33,55 giay: 0 luot

   (b) KHONG phai mau it
       thu cong TB 45,4 luot/ngay (11-145)     gateway 38 luot

   (c) p50 CUNG lech, ma p50 it chiu sai so o hon nhieu
```

Ô cuối **có** bão hoà thật, nhưng chỉ ở vài agent nên không giải thích được toàn bộ: agent 6
**86,7%** số ngày p95 rơi vào ô ≥ 33,55 s, agent 7 64,0%, nhưng agent 1 chỉ 3,2% và agent 2 là
0,0%.

**Và không ngày nào chồng lấn** — thủ công dừng 29/08, gateway bắt đầu 31/08. Nên chưa nguồn nào
kiểm chứng được nguồn kia.

**Chưa kết luận. Ghi lại để đừng ai kết luận vội.** Hai giả thuyết còn sống: (i) hai nguồn đo hai
điểm khác nhau trong đường gọi; (ii) 38 lượt ngày 31/08 là lưu lượng **thử** ngắn, không phải
lưu lượng DMS sản xuất. Phép đo phân biệt được hai cái này là **một buổi chạy DMS qua Gateway
trong ngày mà Cloud Monitoring đang ghi**.

---

## 5. `cached_tokens` — kết luận của việc 3, và nó vẫn là "chưa biết"

Đây là mục dễ bị hiểu nhầm nhất của change này, nên ghi đủ.

**Hiện trạng: `cached_tokens` = 0/41, cột giữ NULL, KHÔNG ghi 0.**

Ba khả năng đặt ra ban đầu, và tình trạng từng cái:

| | Khả năng | Trạng thái |
|---|---|---|
| a | Gemini không có context caching cho những lượt này | **Nghiêng về, chưa chứng minh** |
| b | Gemini có báo, LiteLLM không ánh xạ | **ĐÃ LOẠI TRỪ** |
| c | Có caching nhưng phải bật tường minh | chưa tách khỏi (a) |

**Loại được (b):** fork `litellm_tuan_test` **có** ánh xạ —
`vertex_and_google_ai_studio_gemini.py:1760` đọc `cachedContentTokenCount` → `cached_tokens`.
Google báo thì LiteLLM chuyển tiếp.

**Không loại được (a) khỏi (c), và lý do rất cụ thể:** `response` thô trong sổ cũng ghi
`cached_tokens: null`, nhưng đó là bản **đã chuẩn hoá** của LiteLLM, không phải phản hồi gốc
của Gemini. Nhìn vào đó không phân biệt được "Google không báo" với "LiteLLM không chép".

**Phép thử quyết định vẫn CHƯA về:** hoá đơn Google **có** SKU cache — 461 dòng / 7 SKU /
252.321.118 token. Riêng agent 6, **16/19 ngày có hoá đơn đều có cached** (1.596.241 token) khi
gọi **thẳng** Google. Nhưng hoá đơn dừng ở **29/08** còn lượt Gateway ở **31/08** — **không giao
nhau**. So hai giai đoạn không giao nhau rồi kết luận đúng là cái bẫy đã mắc hai lần rồi
(change 006 với độ trễ, và chính mục này). Không lặp lại.

Một dấu hiệu ủng hộ (a) nhưng chưa đủ: **7/42 lượt có prompt ≥ 1.024 token** — đủ ngưỡng cache
ngầm — mà vẫn không có cached. Hợp lý, vì cache ngầm cần **tiền tố lặp lại**, còn DMS phân loại
các phản hồi khác nhau.

**Kết luận: CHƯA BIẾT, và đó là câu trả lời đúng ở thời điểm này.** Ghi 0 vào cột là biến "không
đo được" thành "đo được và bằng không", làm mọi phép tính tỷ lệ cache sau này sai mà không ai
biết.

**Hệ quả cho Master Plan STT 7 mục tiêu 2:** yêu cầu *"phép kiểm riêng đối chiếu token cache của
Gateway với SKU cache trên hoá đơn Google"* **chưa thực hiện được** — không phải vì thiếu công,
mà vì vế Gateway luôn rỗng và hai nguồn chưa có ngày chung.

---

## 6. Bốn thứ bắt được mà không đi tìm

### 6a. `DO UPDATE` không đủ — phải `--full`

Chạy `load_gateway.py` trần sau khi thêm cột: nạp được **6/41** dòng. Mốc nạp (`watermark`) chỉ
lùi 1 giờ, nên 35 dòng cũ **giữ NULL vĩnh viễn** và cột mới chỉ đầy dần từ lượt gọi **mới**.

`load_gateway.py --full` mới đọc lại cả sổ và ghi đè đủ **41/41**.

Bẫy này chưa được ghi ở đâu trước hôm nay, và nó sẽ cắn lại **mỗi lần thêm cột vào `fact_call`**.

### 6b. `thinking_enabled` ra 0/41 — và đó là ĐÚNG

Hai dòng duy nhất có `reasoning_tokens` (=342, `gemini-3.6-flash`) mang `request_tags` chỉ gồm
`User-Agent: Python-urllib` — **không tag định danh agent nào**. `resolve_agent()` trả `None`,
mà `fact_call.agent_id` là `NOT NULL`, nên cả hai bị loại ở khâu nạp. Một trong hai còn là lượt
trúng cache.

Cột **đọc đúng**, **chưa có dữ liệu**. Đúng luận điểm ① của chính đề xuất này: *"có cột không có
nghĩa là có dữ liệu"*. Câu **"Data Out 21/26 → 23/26"** phải đọc là *trường đã có đường nạp*,
KHÔNG phải *trường đã có số*.

### 6c. Design ⑧ ghi sai kiểu dữ liệu

Design viết *"`fact_monitoring` đã có sẵn cột `thinking_enabled` kiểu **BOOLEAN**"*. Đo thật: nó
là **TEXT** mang chuỗi `'true'` / `'false'`. Ba con số 11.440 / 3.589 / 636.624 thì **khớp**.

`fact_call.thinking_enabled` vẫn dùng **BOOLEAN** — đúng tiền lệ `cache_hit` ở migration 007
(nguồn TEXT `'None'`, đích BOOLEAN, dịch bằng `CASE`). Sự khác kiểu đã ghi vào
`COMMENT ON COLUMN` để không ai so hai bảng mà quên dịch kiểu.

### 6d. `check_api.py` mang một phép kiểm lỗi thời từ 31/08

Phép `Tien API == database` báo **HỎNG**:

```
   api $307,382155  !=  db $307,360850     chenh $0,021305
```

Truy ra: `against_database()` so tiền của API với **riêng** `fact_billing_daily`, trong khi
migration **005** (`gateway_cost_vao_view`, 31/08) đã **cố ý** đổ tiền Gateway vào
`usage_resolved.cost_usd`.

```
   fact_billing_daily                $307,360850
   usage_resolved                    $307,382155
   gateway trong fact_usage_daily      $0,021305   <- DUNG BANG chenh lech
```

`scripts/audit_db.py` đã được sửa theo từ 31/08 (*"Cost: invoice + gateway =="*), file kia thì
không — nên nó báo HỎNG trong khi **cả hai vế đều đúng**.

**Không nới ngưỡng.** Sửa **công thức** cho khớp định nghĩa mới của view, dùng đúng phép của
`audit_db.py` (chỉ cộng tiền Gateway của khoá **không** có dòng hoá đơn tương ứng — nếu không là
đếm hai lần). Đây là trường hợp duy nhất được phép sửa một phép kiểm: chứng minh được **bản thân
phép kiểm sai**, không phải dữ liệu không vừa ý nó.

Việc này đóng luôn một mục Master Plan STT 7 đang treo: *"Còn: backend/check_api.py"*.

---

## 7. Trạng thái nghiệm thu cuối buổi

```
   scripts/audit_db.py    54 kiem · 50 dat · 4 luu y · 0 hong   (moc cu 42/38/4/0)
   backend/check_api.py   25 kiem · 25 dat · 0 hong
   moc 24 khoa            24/24 KHOP, 0 lech
   git diff --stat web/   RONG
```

Bốn lưu ý của `audit_db.py` **giữ nguyên** — đúng bốn khoảng trống dữ liệu đã biết, không phát
sinh cái mới.

**Đo trên 41 dòng gateway:**

```
   unit_id           41/41   DAT
   output_modality   38/41   DUNG (3 dong rong la 3 LUOT HONG - luot hong
                             khong co phan hoi nen khong co modality de dan nhan)
   thinking_enabled   0/41   DUNG nhu vay - xem 6b
   cached_tokens      0/41   DUNG nhu vay - xem muc 5
```

Việc 10.5 của change viết kỳ vọng `output_modality` **41/41**. Kỳ vọng đó được viết **trước** khi
biết 3 lượt hỏng cũng nằm trong `fact_call`. **Sửa kỳ vọng, không sửa dữ liệu.**

---

## 8. Một phép đo ngoài lề, nhưng trả lời được một câu đang treo

Change kế tiếp (`answer-what-each-agent-did-on-a-day`) ghi một suy luận **chưa chứng minh**:
*"`docker compose up -d` cấp lại quyền cho `api_readonly`"* — đọc từ cấu hình compose
(`depends_on: api-db-init: service_completed_successfully`).

Sáng nay chạy thật, và **đo được cả hai đầu**:

```
   truoc `docker compose up -d api`   USAGE = false   doc duoc  0/24 bang+view
   sau                                USAGE = true    doc duoc 24/24
```

**Suy luận đó nay là sự thật đo được, không còn là suy luận.** Và nó bao gồm cả bảng mới
`fact_usage_hourly` — `read-only-api.sql` cấp theo `ALL TABLES IN SCHEMA` nên bảng mới tự có
quyền, không phải khai thêm.

Nhưng nó **không** làm lỗ hổng biến mất: `rebuild_db.py` vẫn xoá sạch quyền, và cả hai bộ kiểm
vẫn báo lành trong lúc API mù. `docker compose up -d` chỉ là cách chữa **thủ công sau khi đã
hỏng** — nó đòi có người biết mà chạy.

---

## 9. Còn lại

```
   10.1-10.4  nghiem thu rebuild_db.py 9/9 buoc   HOAN CO CHU Y
              -> lenh do XOA SACH quyen api_readonly, va change ke tiep
                 moi them buoc kiem quyen. Chay sau, khi no da tu dung duoc.
   11.3       Master Plan STT 4 muc tieu 1 va 2
```

**`scripts/refresh_gateway.py` CHƯA gọi hai bước mới** (`build_usage_hourly`,
`build_performance`). Sau mỗi lần refresh, bảng theo giờ và phân vị Gateway **cũ đi một nhịp**.
Nằm ngoài phạm vi change này — ghi lại để không ai tưởng nó đã đủ.

---

# PHIÊN CHIỀU — mở rộng bộ kiểm tra sang dữ liệu Gateway

Đóng **STT 7 mục tiêu 2**. Change `extend-the-checks-to-gateway-data`, **40/40 việc**.

## 10. Ba thứ đo được trước khi viết một dòng mã nào

```
   ① khoa ngoai      audit khai 23 · database co 36  ->  13 KHONG AI CANH
   ② ngay tuong lai  nguong ghim '2026-12-31', chi soi 1/5 bang
   ③ phep kiem gateway DAT ca khi khong co dong gateway nao
```

**① Danh sách khoá ngoại đã trôi, và đang trôi nhanh hơn.** Mười ba quan hệ không được kiểm, trong đó **sáu** do chính migration 008 tạo ra **sáng cùng ngày**. Đây không phải nợ đứng yên — cứ thêm một bảng là danh sách tụt thêm, trong im lặng, vì nhãn vẫn báo `Foreign keys (23 relations)` ĐẠT. Con số 23 nằm ngay trong nhãn, và nó là số quan hệ **được khai** chứ không phải số **có thật**.

**② Ngưỡng ngày ghim `2026`** (`audit_db.py:629`). Sang 2027 thì mọi dòng dữ liệu **thật** đều bị coi là tương lai. Và nó chỉ soi `usage_resolved` — `fact_call`, nơi Gateway ghi từng lượt, không được soi.

**③ Hình dạng lỗi trung tâm.** Mọi phép kiểm theo nguồn là *"đếm dòng xấu, đòi bằng 0"*. Trên **0 dòng** nó trả 0 và báo ĐẠT — **không phân biệt** *"Gateway ghi đúng"* với *"Gateway không ghi gì cả"*. Cùng hình dạng đã để API mù 38 phút ngày 02/09.

## 11. Sửa hình dạng, không chỉ thêm phép kiểm

`Audit.check_tren()` và `Check.expect_tren()` — mỗi phép kiểm theo nguồn nay khai **cả mẫu số**:

```
   quan sat 0 dong             ->  CANH BAO "chua kiem duoc"
   quan sat n > 0, khong loi   ->  DAT, nhan kem "(n rows checked)"
   quan sat n > 0, co loi      ->  HONG
```

CẢNH BÁO chứ không HỎNG: kỳ chưa có lưu lượng của một nguồn là trạng thái **hợp lệ**. Nhưng nó phải **hiện ra** — hôm nay nó vô hình.

**Nghiệm thu bằng tập rỗng THẬT, không dựng database giả.** Đo ra **8 cặp (bảng, nguồn) rỗng tự nhiên**; dùng `fact_perf_daily` × `gateway` (bảng đó chỉ có monitoring, 669 dòng). Kết quả:

```
   [ note ] Gateway rows in fact_perf_daily carry method and response_code
            CHUA KIEM DUOC - 0 dong de quan sat. Day KHONG phai ket qua dat.
```

Cơ chế hoạt động, và **không xoá một dòng dữ liệu nào** để chứng minh.

## 12. Đối chiếu token cache — viết xong một phép kiểm CHƯA CHẠY ĐƯỢC

```
   ve GATEWAY   fact_call source='gateway'         41 dong · cached_tokens 0/41
   ve HOA DON   fact_billing_daily kind='cached'  461 dong · 252.321.118 token
                                                  214 ngay · 6 agent
   so ngay CA HAI nguon cung co du lieu:  0
```

Vế hoá đơn giàu, vế Gateway rỗng, hai khoảng ngày **rời nhau hoàn toàn**.

Vẫn viết phép kiểm **đầy đủ** ngay bây giờ: ngày hai nguồn giao nhau, nó phải **đã sẵn ở đó**. Viết sau nghĩa là ngày đó không ai nhớ, và cửa sổ so sánh trôi qua — đúng như cửa sổ lưu giữ của Cloud Monitoring đã trôi mất ba tháng dữ liệu.

Ngưỡng **1%** chốt **trước** khi có số đầu tiên, theo đúng kỷ luật STT 7 dòng 19. Ghi rõ tại chỗ: nó **chưa có cơ sở đo đạc**.

Chạy hôm nay:

```
   [ note ] Gateway cache tokens match the invoice cache SKU
            CHUA KIEM DUOC - khong ngay nao ca hai nguon cung co du lieu.
            gateway 2026-08-31 -> 2026-08-31 (1 ngay) ·
            hoa don 2026-01-05 -> 2026-08-29 (214 ngay).
            Day KHONG phai ket qua dat.
```

**Cám dỗ lớn nhất của cả change này** là cho phép kiểm chạy trên tập rỗng, nó báo ĐẠT, và mục Master Plan được tick xanh. Thiết kế làm điều đó **không thể xảy ra** — hai nhánh rỗng đều đi thẳng vào `note(WARN, ...)`, không đi qua `check()`.

## 13. Bốn phép kiểm đổi màu, và vì sao đó là dấu hiệu tốt

```
   luu y  4 -> 7      hong  0 -> 0

   + Foreign keys are read from the database, not from a hand-written list
                                              (do troi 13/36 quan he)
   + Gateway cache tokens match the invoice cache SKU        (chua kiem duoc)
   + Gateway rows in fact_perf_daily carry method and ...    (0 dong quan sat)

   bon luu y CU giu nguyen, khong cai nao bien mat
```

Số lưu ý tăng là **đúng**: ba cái mới đều là chỗ trước nay báo đạt mà **chưa quan sát gì**. Hạ tiêu chuẩn để giữ màu cũ chính là thứ change này đi bịt.

## 14. Nghiệm thu cuối phiên chiều

```
   scripts/audit_db.py    72 kiem · 65 dat · 7 luu y · 0 hong   (moc 68/64/4/0)
   backend/check_api.py   31 kiem · 31 dat · 0 luu y · 0 hong   (moc 27/27)
   khoa ngoai             36/36 duoc kiem · 0 quan he treo
   ngay tuong lai         0 dong tren ca 5 bang
   chay hai lan lien tiep (72,65,7,0) = (72,65,7,0)             KHOP
   usage_resolved         khop 4/4 khoa, lech 0
```

Con số cuối là quan trọng nhất: change này **không đụng một dòng dữ liệu nào**, và số liệu chứng minh điều đó.

## 15. Một lỗi bắt được ngoài phạm vi

Soát bind IP trước khi push thì phát hiện `docker-compose.yml` đang bind `web` vào `127.0.0.1` thay vì `192.168.20.111`. Hai dòng bị **hoán đổi** để chạy trên máy dev và không trả lại — và hoán đổi làm **chú thích trỏ nhầm dòng**, nên đọc lướt thì tưởng đúng.

Commit `9ef9626` của phiên này đưa `docker-compose.yml` vào mà không soát bind IP; nó chỉ nên mang phần `logging`. Đã sửa ở commit `622b52b`.

Nếu đẩy lên với `127.0.0.1` thì dashboard chỉ mở được **trên chính máy chủ** — và hỏng im lặng: container vẫn `healthy`, `docker ps` vẫn đẹp, chỉ là không ai trong mạng nội bộ gọi tới được.
