# Thiết kế — trả lời "ngày A, agent này hoạt động thế nào"

Mọi con số đo trên database thật `token_ledger_v2` ngày **03/09/2026**, bằng session chỉ-đọc.

---

## ① Vì sao KHÔNG sửa `kind` của `usage_by_account`

Đường sửa hiển nhiên là nới điều kiện ở `001_baseline.sql:773`:

```sql
WHERE f.source IN (SELECT source FROM ref_source WHERE knows_user)
  AND a.kind = 'real';
```

Đo trước khi sửa — và đó là lý do không sửa:

```
   kind = 'real'                        337 dong · 2 agent · 53 account · 108.554.843
   kind IN ('real','service_account')   338 dong · 3 agent · 54 account · 108.600.030
```

Thêm đúng **một** agent (DMS), vì `knows_user` mới là điều kiện chặn:

```
   service_account · billing     knows_user = f   741.641.736 token   6 agent
   service_account · monitoring  knows_user = f   485.267.016 token   6 agent
```

Sáu agent dịch vụ có token ở billing và monitoring — hai nguồn **không** biết người dùng, dù
bản thân agent thì ta biết rõ là ai.

**Bỏ luôn `knows_user` là hỏng nặng hơn:**

```
   1.903 dong · 8 agent · 1.335.508.782 token
   tong chuan usage_resolved:        915.969.971
                                     -> 145,8%
```

`fact_usage_daily` để bốn nguồn **cạnh nhau**, không phải chồng lên nhau. Cộng thẳng là đếm
cùng một lưu lượng qua nhiều công tơ. `backend/store.py:455` đã ghi lại đúng bẫy này, kèm số
đo cũ: `1.248.600.872 / 867.657.110 = 143,9%`, và "phần còn lại" ra `-43,9%`.

Điều kiện `knows_user` hiện tại **an toàn một cách tình cờ** — nó lọc còn đúng một nguồn (`app`)
nên không có gì để đếm hai lần. Nới nó ra là mất luôn sự an toàn tình cờ đó.

**Kết luận: chiều account phải dựng trên `usage_resolved`, nơi nguồn ĐÃ được chọn.**

---

## ② JOIN hai lần — và vì sao nghiệm thu phải là HAI con số

`usage_resolved` khoá theo `(day, agent_id, model_id)` và **không mang `account_id`** — vì
COALESCE diễn ra ở mức đó. Nhưng nó **nói ra** nó đã chọn nguồn nào. Lấy đúng nguồn ấy quay lại
`fact_usage_daily` là có chiều account, không đếm hai lần:

```
   fact_usage_daily  --JOIN--  usage_resolved
                               ON (day, agent_id, model_id)
                              AND f.source = v.token_source
```

Đo: **1.442 dòng · 8/8 agent · 60 account · 915.969.971 token — lệch 0.**

Nghiệm thu token đạt tuyệt đối. **Và đó chính là chỗ suýt lọt một lỗi 77,9%:**

```
   calls chuan (usage_resolved):  122.504
   calls theo cach tren:           27.056
   MAT:                            95.448   =  77,9%
```

Nguyên nhân — `usage_resolved` chọn nguồn **theo TỪNG CHỈ TIÊU**, và **billing không có `calls`**:

```
   token_source | call_source | dong |    token    | calls
   -------------+-------------+------+-------------+--------
   billing      | monitoring  |  524 | 472.161.741 | 93.062   <- lech o day
   billing      |   (khong)   |  488 | 279.027.663 |      —
   app          | app         |  181 | 107.125.668 | 11.176
   monitoring   | monitoring  |   71 |  57.609.712 | 15.842
     (khong)    | monitoring  |   11 |           — |  2.386   <- chi co calls
   gateway      | gateway     |    1 |      45.187 |     38
```

524 dòng lấy token của hoá đơn nhưng lượt gọi của monitoring. Và 11 dòng **chỉ** có calls, không
có token — chúng biến mất hoàn toàn nếu chỉ JOIN theo `token_source`.

**Cách đúng: hai nhánh, mỗi nhánh một `*_source`, rồi FULL OUTER JOIN theo
`(day, agent_id, model_id, account_id)`.** Đo lại:

```
   1.453 dong · 8/8 AGENT · 60 account
   token   915.969.971  =  915.969.971   DAT
   calls       122.504  =      122.504   DAT
```

> **Luật cho việc 3.4:** nghiệm thu view này **phải** gồm cả hai con số. Chỉ kiểm token thì một
> lỗi 77,9% vẫn báo ĐẠT — đã xảy ra thật trong lúc thiết kế change này.

**Vì sao FULL OUTER chứ không LEFT:** 11 dòng chỉ-có-calls (agent 1, từ 29/04 đến 28/08, 2.386
lượt) không có nhánh token. LEFT JOIN từ phía token sẽ vứt chúng đi mà tổng token vẫn khớp —
đúng loại lỗi im lặng mà mục này đang phòng.

Phân bố kết quả theo `kind`:

```
   service_account  1.046 dong · 6 agent ·  6 account · 793.613.395 · 86,6%
   real               324 dong · 2 agent · 52 account · 102.905.141 · 11,2%
   whole_agent         38 dong · 1 agent ·  1 account ·  15.230.908 ·  1,7%
   unattributed        34 dong · 1 agent ·  1 account ·   4.220.527 ·  0,5%
```

**Chéo kiểm với `/api/health`** (`backend/store.py:483-500`), là đường tính hoàn toàn khác —
nó đi từ `usage_resolved` chứ không qua account:

```
   people_tokens   107.125.668  =  real 102.905.141 + unattributed 4.220.527   KHOP
   service_tokens  793.613.395  =  service_account 793.613.395                 KHOP
   opaque_tokens    15.230.908  =  whole_agent 15.230.908                      KHOP
   tong            915.969.971                                                 KHOP
```

Hai đường độc lập ra cùng một bộ số. Đây là bằng chứng mạnh nhất có được mà không cần nguồn thứ
ba.

Từng agent:

```
   Chatbot Contact Center        1 account · 216 ngay · 345.342.823
   Sale Agent                    1 account · 240 ngay · 310.369.050
   Multi modal AI Invoice        1 account · 105 ngay · 113.924.662
   Tro Ly Ao Hop Dong           25 account ·  63 ngay ·  72.288.033
   Tro ly ao Ralli              31 account · 148 ngay ·  50.068.543
   Phan Loai Du Lieu CRM         1 account ·  53 ngay ·  12.616.263
   Phan Loai Phan Hoi Tiep Thi   1 account ·  25 ngay ·  11.280.682
   Tools Quizzer                 1 account ·   8 ngay ·      79.915
```

Đúng quy ước account: agent dịch vụ = **một** account; app/gateway = chi tiết từng người.

---

## ③ `whole_agent` và `unattributed`: GIỮ và HIỆN, không giấu

`db/load_org.py:566` tạo cho **mỗi** agent hai chỗ ngồi, nên có đúng 16 tài khoản kỹ thuật.
Nhưng chỉ **hai** chỗ có lưu lượng thật:

```
   whole_agent   __whole_agent_5__  TLA Hop Dong   38 dong · 15.230.908 · 1,7%
                    phan billing + monitoring cua TLA HD.
                    Google CHI bao muc project -> khong biet ai trong 43 nguoi
                 __whole_agent_8__  Ralli           0 dong
                    Ralli chua noi GCP, khong co billing/monitoring nao

   unattributed  __unattributed_8__ Ralli          34 dong ·  4.220.527 · 0,5%
                    luot trong nhat ky Ralli KHONG kem username
                    ('system', 'guest' - khau nap lui ve day CO CHU Y)
                 7 account con lai                  0 dong
```

**Vì sao phải tồn tại dù rỗng:** `fact_usage_daily.account_id` là khoá ngoại NOT NULL.
`001_baseline.sql:186` ghi rõ — thiếu hai loại này thì khoá phải nhận NULL, mà SQLite coi
`NULL != NULL` nên sẽ **âm thầm nhận hai dòng giống hệt nhau**.

**Quyết định: view mới GIỮ cả hai và hiện chúng thành dòng nhìn thấy được.**

Chúng là 2,2% mà ta thật sự **không** quy được về một account. Lọc đi là nói dối rằng độ phủ
bằng 100%. Đây là cùng một lý lẽ đã dùng cho `unit_conflict` (`001_baseline.sql`): giữ lại dấu
vết chỗ ta đã chọn hộ, thay vì để việc chọn diễn ra âm thầm.

**Ba chỗ mã đang đọc hai loại này — không được làm gãy:**

```
   db/build_usage_daily.py:74   kind IN ('service_account','whole_agent')
                                = "cho ngoi muc agent", tra bang (kind, unit_agent_id)
   scripts/audit_db.py:273      mau so cho ty le ap dung
   scripts/audit_db.py:515      phep kiem: dong tu ky nguyen GATEWAY khong duoc
                                roi vao unattributed/whole_agent (quy uoc A3)
```

---

## ④ Bịt lỗ hổng quyền: BÁO ĐỘNG, không tự chữa

Hai hướng đã cân nhắc:

| | Hướng | Ưu | Nhược |
|---|---|---|---|
| a | `rebuild()` tự gọi lại phần cấp quyền | không ai phải nhớ gì | tự chữa **âm thầm**; lỗ hổng biến mất khỏi tầm nhìn và quay lại lần sau ở dạng khác |
| b | `rebuild_db.py` thêm bước cuối kiểm quyền, thiếu thì **dừng và báo** | con người nhìn thấy; ép sửa đúng chỗ | phải chạy thêm một lệnh |

**Chọn (b).**

Lý do không phải là (a) sai kỹ thuật — nó chạy được. Lý do là chuyện này đã **im lặng suốt
38 phút ngày 02/09** trong khi cả hai bộ kiểm báo lành. Vấn đề không phải quyền bị xoá; vấn đề
là **không ai được báo**. Hướng (a) sửa cái thứ nhất và giữ nguyên cái thứ hai.

Bước kiểm phải hỏi đúng câu mà `read-only-api.sql` cấp:

```
   has_schema_privilege(<vai doc>, 'public', 'USAGE')
   SELECT tren MOI bang va MOI view trong schema public
```

Không hỏi bằng cách "thử một bảng" — `DROP SCHEMA` xoá tất, nhưng một migration hỏng nửa chừng
thì có thể để lại quyền không đều.

**Chưa chắc chắn:** `docker compose up -d` tự chữa được vì `api` khai
`depends_on: api-db-init: service_completed_successfully`. Đây là **suy luận từ cấu hình
compose**, chưa chạy để chứng minh — việc 1.4 phải chứng minh hoặc bác bỏ nó.

---

## ⑤ `read_only()` phải phân biệt HAI trạng thái, không phải một

Phép kiểm hiện tại (`backend/check_api.py:274`):

```python
   cur.execute("CREATE TEMP TABLE _write_probe (x INT)")   # cho bi tu choi
```

Nó cho **cùng một kết luận** cho hai trạng thái ngược nhau:

```
   ky luat chi-doc CON NGUYEN   ->  lenh ghi bi tu choi  ->  DAT
   MAT SACH QUYEN DOC           ->  lenh ghi bi tu choi  ->  DAT  <- sai
```

Phải thành **hai** khẳng định độc lập:

```
   (1) lenh GHI  bi tu choi   ->  ky luat chi-doc con nguyen
   (2) cau SELECT THANH CONG  ->  vai con doc duoc
```

Cả hai đạt mới là ĐẠT. Câu SELECT phải chạm bảng thật của schema, không phải `SELECT 1` —
`SELECT 1` không cần `USAGE` trên schema nên nó qua cả khi quyền đã mất sạch.

---

## ⑥ Thứ tự ưu tiên nguồn độ trễ: `monitoring` TRƯỚC — và vì sao đó là lựa chọn tạm

Hai nguồn cho **cùng** agent 6 lệch 31,9 lần:

```
   thu cong (histogram Google)   p95 TB 58,206 s   p50 TB 19,66 s   681 mau
   gateway  (duration_ms tho)    p95    1,822 s    p50    0,788 s    38 mau
```

Ba phép đo đã loại trừ các giải thích dễ dãi — chi tiết ở proposal ④. Còn lại hai giả thuyết,
**cả hai đều còn sống**:

| | Giả thuyết | Nếu đúng thì ưu tiên nào? |
|---|---|---|
| a | Hai nguồn đo hai điểm khác nhau trong đường gọi | phải biết hệ số trước khi gộp |
| b | 38 lượt ngày 31/08 là lưu lượng **thử** ngắn, không phải lưu lượng DMS sản xuất | gateway đúng, nhưng chưa đại diện |

**Quyết định: `monitoring` đứng trước `gateway`, tạm thời.**

Lý lẽ là về **rủi ro bất đối xứng**, không phải về nguồn nào chính xác hơn:

```
   monitoring truoc  ->  dashboard KHONG doi mot con so nao hom nay.
                         Gateway chi dien vao NGAY ma monitoring khong co.
                         Sai lam nay khong ai nhin thay.

   gateway truoc     ->  p95 cua DMS roi tu ~58 s xuong ~1,8 s.
                         Nguoi xem thay he thong nhanh len 31,9 LAN sau mot dem.
                         Sai lam nay AI CUNG nhin thay, va no trong y nhu that.
```

Chọn hướng mà sai lầm rẻ hơn, cho tới khi có số.

**Chỗ này đi ngược `usage_resolved`, và đó là có chủ ý.** View kia cho `gateway` đứng trước
billing về token, vì Gateway là bộ đếm của chính ta và có mặt ngay trong ngày. Lý lẽ đó đúng
cho **token** — hai nguồn đếm cùng một thứ. Với **độ trễ** thì chưa chứng minh được là chúng
đo cùng một thứ. Cùng một tên "nguồn" không bảo đảm cùng một phép đo.

**Cô lập điều chưa biết vào MỘT chỗ.** Thứ tự ưu tiên nằm trong **một** `CASE` của
`latency_resolved`. Mọi thứ khác trong change này — `store.py` đọc theo nguồn, `api.js` hết ghi
đè, bốn chỗ hiển thị — **không** phụ thuộc câu trả lời. Phần tầng dữ liệu (cột `source`, phép
tính p50/p95/p99 từ số thô) nằm ở change kia và cũng không phụ thuộc: nó giữ **mỗi nguồn một
dòng**, chưa chọn gì cả. Phép đo về thì đổi đúng một dòng, ở đúng một file.

Đây đúng cách dự án đã làm với `ref_source`: *"thêm nguồn thứ tư là thêm MỘT DÒNG DỮ LIỆU,
không phải sửa 10 câu SQL nằm rải ở 3 file."*

*(Ghi chú: `ref_source` hiện có 5 cột — `source`, `knows_user`, `has_invoice_cost`, `era`,
`note` — **không** có cột thứ tự ưu tiên. Độ trễ chỉ có hai nguồn nên một `CASE` là đủ; change
này **không** đụng `ref_source`.)*

---

## ⑦ `latency_resolved` đọc gì, và nó KHÔNG dựng lại cái đã có

Change này dựng **một view**, không dựng bảng và không tính lại phân vị. Nó đọc
`fact_latency_daily` **sau khi** change `fill-the-declared-fields-and-log-by-the-hour` đã thêm
cột `source` (việc 5.3) và đổ phân vị Gateway vào (việc 7.1–7.5).

Hình dạng view, một dòng cho mỗi `(day, agent_id)`:

```
   latency_resolved
       day, agent_id
       samples, p50_seconds, p95_seconds, p99_seconds, enough_samples
       p95_bucket_from, p95_bucket_to     <- NULL khi nguon la gateway
       latency_source                     <- nguon DA CHON, de audit doc duoc
```

**`latency_source` là cột bắt buộc, không phải trang trí** — cùng lý lẽ đã dùng cho
`token_source` / `call_source` ở `usage_resolved`: một con số 1,8 giây tính từ số thô trông y hệt
một con số 1,8 giây nội suy từ histogram. Không có cột này thì `scripts/audit_db.py` không kiểm
được view đã chọn đúng nguồn chưa.

Cột đó **không** lên tới màn hình — dashboard hiện một con số trần, theo đúng yêu cầu. Nó phục
vụ phép kiểm, không phục vụ người xem.

**Vì sao `p95_bucket_*` vẫn đi qua view dù màn hình không dùng:** chúng là bề rộng ô chứa phân
vị, tức sai số của phép nội suy. Đo hiện tại cho thấy sai số đó không hề nhỏ:

```
   agent 6   p95 TB 58,206 s   be rong o TB 31,318 s   = 54% chinh gia tri
   agent 7   p95 TB 46,531 s   be rong o TB 27,179 s   = 58%
   agent 5   p95 TB 45,802 s   be rong o TB 30,559 s   = 67%
```

Giữ chúng chảy qua view là giữ đường cho phép kiểm `audit_db.py:376`
(*"p50<=p95<=p99 và p95 nằm trong chính ô của nó"*) tiếp tục chạy được. Cắt chúng ở view là làm
gãy một phép kiểm đang đạt.

---

## ⑧ Bốn chỗ hiển thị p95, và `A.lat` không phải số lấy thẳng

```
   app.js:2384   bang chi tiet theo agent        fmtDecimal(g.lat,1)+"s"
   app.js:2900   m-pv-latency  (tab Provider)    top.lat
   app.js:3518   m-pf-p95      (tab Hieu nang)   A.lat
   app.js:3531   bang tab Hieu nang              g.lat
```

`A.lat` là **trung bình có trọng số theo số request** (`app.js:1155`, `1172`):

```js
   if(num(row.lat)>0 && num(row.r)>0){ a.latW += num(row.lat)*num(row.r); a.latR += num(row.r); }
   a.lat = a.latAvailable ? a.latW/a.latR : 0;
```

Trong phạm vi **một** agent thì đúng — `api.js` lặp cùng một p95 trên mọi dòng model của agent
đó, nên trung bình có trọng số trả về đúng con số ban đầu. Gộp **nhiều** agent thì nó là một
xấp xỉ, và change này **không** đổi điều đó — đổi phép gộp là một việc khác, không nằm trong
phạm vi.

Cái change này **phải** đổi là `api.js:187`:

```js
   var d = slot(x.day + "|" + x.agent_id);
   d.lat = x.p95_seconds || 0;     // GAN DE — khoa khong co `source`
```

Sau khi `/api/performance` biết nguồn, hai dòng cho cùng (ngày, agent) sẽ tồn tại. Khoá không
có `source` nghĩa là dòng đến sau thắng, mà `backend/store.py:performance()` sắp xếp
`ORDER BY day, agent_id` — **không có tie-break trên nguồn**. Con số hiển thị sẽ không xác định.

**Dashboard vẫn hiện MỘT con số, không nhãn nguồn** — theo đúng yêu cầu. Việc chọn nguồn xảy ra
ở tầng dữ liệu (`latency_resolved`), không ở tầng hiển thị.

---

## ⑨ Ranh giới với `fill-the-declared-fields-and-log-by-the-hour`

Hai change đụng nhau ở đúng một chỗ, và ranh giới phải vạch rõ **trước** khi triển khai, nếu
không sẽ có hai migration cùng đánh số 008 và hai bản `build_performance.py` khác nhau.

Head migration hôm nay là `007_cot_bo_qua`. Change kia đã đặt tên `008_theo_gio` (việc 5.1).

```
   fill-the-declared-fields-and-log-by-the-hour   SO HUU TANG DU LIEU
       5.3   cot `source` cho fact_latency_daily + fact_perf_daily
             dong cu DEFAULT 'monitoring'
       7.1   build_performance.py tinh p50/p95/p99 tu duration_ms tho
       7.2   p95_bucket_from/to = NULL cho gateway
       7.3   giu MIN_SAMPLES = 10
       7.4   moi nguon MOT DONG, khong gop trung binh
       7.5   nghiem thu p95 Gateway 31/08 = 1,822 s

   answer-what-each-agent-did-on-a-day            SO HUU TANG DOC
       latency_resolved     chon MOT nguon cho moi (ngay, agent)
       backend/store.py     doc theo nguon da chon
       web/js/api.js        het ghi de
       4 cho hien so        van MOT con so, khong nhan
```

**Vì sao chia thế này chứ không gộp hết vào một change:**

Change kia đã làm xong việc 1–4 và đang dở việc 5–7. Rút 5.3 và 7.x ra khỏi nó giữa chừng là
làm hỏng mạch lý lẽ của chính nó — design ⑤ và ⑥ của nó tồn tại **để** biện minh cho hai nhóm
việc đó.

Và ranh giới này khớp đúng chỗ change kia tự dừng lại. Design ⑥ của nó viết: *"để cạnh nhau,
`usage_resolved` chọn một khi cần một con số duy nhất"* — nhưng `usage_resolved` **không có độ
trễ**. Câu đó mô tả một view chưa tồn tại. `latency_resolved` chính là view đó.

**Hệ quả cho thứ tự triển khai:** phần ③ của change này **chặn** cho tới khi việc 5.3 và 7.1–7.5
xong. Phần ① (quyền đọc) và ② (chiều account) **không** phụ thuộc gì — làm được ngay, và không
đụng file nào của change kia.

## ⑩ Những gì change này KHÔNG làm

- **Không** chạy buổi đo DMS trong project Google One. Đó là một buổi chạy, không phải việc gõ
  phím, và nó là thứ trả lời cho ⑥. Nó **không chặn** bất cứ việc nào ở đây.
- **Không** viết migration nào. Cột `source` thuộc change kia.
- **Không** sửa `db/build_performance.py`.
- **Không** đụng `db/load_gateway.py`, `ref_source`, sổ `LiteLLM_SpendLogs`.
- **Không** đổi phép gộp `A.lat` từ trung bình có trọng số sang thứ khác.
- **Không** đổi `MIN_SAMPLES`.
