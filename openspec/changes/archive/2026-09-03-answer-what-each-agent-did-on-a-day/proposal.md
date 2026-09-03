# Trả lời được "ngày A, agent này hoạt động thế nào" — cho cả 8 agent

Đóng **hai** mục STT 6 của Master Plan, **gỡ chặn** mục thứ ba, và sửa lại câu chữ của hai
trong ba mục cho khớp với câu hỏi mà dashboard thật sự phải trả lời.

Change này **không** đóng dòng 16. Nó bỏ ràng buộc đang chặn dòng đó (kỳ chạy song song 2 tuần
trên agent production) và định nghĩa lại sản phẩm của nó cho đúng bản chất — nhưng phép kiểm
đối chiếu nguồn thì chưa viết ở đây.

```
   STT 6 dong 16   "Dua du lieu Gateway vao database hien tai"      moc 30/09
   STT 6 dong 17   "Mo rong backend doc, giu ky luat chi-doc"       moc 07/10
   STT 6 dong 18   "Cap nhat dashboard cho chieu nguoi dung day du" moc 21/10
```

Mọi con số dưới đây đo trên database thật `token_ledger_v2` ngày **03/09/2026**, bằng session
chỉ-đọc.

## Why

### ① Câu hỏi mà dashboard phải trả lời không phải "bốn nguồn lệch nhau bao nhiêu"

Dòng 16 đòi *"kiểm tra và báo cáo đối chiếu chênh lệch giữa bốn nguồn"*. Nhưng người dùng
dashboard không bao giờ nhìn thấy bốn con số cạnh nhau — `usage_resolved` đã **chọn sẵn** một
nguồn cho từng chỉ tiêu và nói rõ nó chọn gì qua `token_source` / `call_source`.

Câu hỏi thật là: **"ngày A, agent này hoạt động thế nào"**. Đối chiếu nguồn là **phép kiểm nội
bộ trong lúc phát triển** để bắt lỗi logic — không phải sản phẩm giao cho ai.

Điều đó gỡ được một ràng buộc đang chặn cả STT 6: kỳ chạy song song 2 tuần trên agent
production. Ràng buộc đó không thoả được (máy không đủ, chưa được phép động vào agent thật), và
nó **không cần thiết** cho câu hỏi trên.

### ② Chiều người dùng: 2/8 agent, và nguyên nhân KHÔNG phải chỗ ai cũng tưởng

Dòng 18 đòi *"ba biểu đồ có dữ liệu cho cả 8 agent"*. Đo `usage_by_account` hôm nay:

```
   337 dong · 2 AGENT · 53 account · 108.554.843 token · 14/03 -> 29/08
```

Quy ước account của dự án (chốt 20/08, ghi ở `001_baseline.sql:176-186`) nói rõ **ta biết được
người dùng của cả 8 agent**:

```
   'real'             nguoi that (app, gateway)
   'service_account'  6 agent chay bang MOT tai khoan dich vu.
                      "Ta BIET chinh xac ai dung - chi la 'ai' do khong phai
                       mot con nguoi. QUY DUOC ve danh tinh."
   'whole_agent'      Google chi bao muc project -> KHONG quy duoc
   'unattributed'     co luot goi nhung ban ghi khong kem nguoi dung
```

Đo phân bố account:

```
   real             938 account · 2 agent
   service_account    6 account · 6 agent    svc.contact-center, svc.sale-agent,
                                             svc.invoice, svc.tools-quizzer,
                                             svc.dms-feedback, svc.crm-feedback
   whole_agent        2 account · 2 agent    TLA Hop Dong, Ralli
   unattributed       8 account · 8 agent
```

**Nhưng nới điều kiện `kind` KHÔNG giải quyết được gì.** Đo thật:

```
   kind = 'real'                          337 dong · 2 agent · 53 account
   kind IN ('real','service_account')     338 dong · 3 agent · 54 account
                                                     ^^^^^^^ chi them 1
```

Vì điều kiện thứ hai của view mới là thứ chặn — `source IN (... knows_user)`:

```
   service_account · billing     knows_user = f   6 agent   741.641.736 token  BI CHAN
   service_account · monitoring  knows_user = f   6 agent   485.267.016 token  BI CHAN
   real            · app         knows_user = t   2 agent   108.554.843
   service_account · gateway     knows_user = t   1 agent        45.187  <- chi DMS lot
```

**Và bỏ luôn `knows_user` thì phồng số**, vì `fact_usage_daily` để bốn nguồn cạnh nhau:

```
   bo ca hai dieu kien  ->  1.903 dong · 8 agent · 1.335.508.782 token
   tong chuan (usage_resolved):           915.969.971
                                          -> phong 145,8%
```

Đúng cái bẫy đã ghi ở `backend/store.py:455`: một agent dịch vụ có token ở **cả** billing lẫn
monitoring, cộng thẳng là đếm hai lần.

Nên chiều người dùng cho 8 agent **không phải một dòng `WHERE`**. Nó cần một view dựng trên
`usage_resolved` — nơi nguồn đã được chọn.

### ③ Vai `api_readonly` mất sạch quyền đọc sau mỗi lần dựng lại database

Phát hiện ngoài dự tính, truy được đến từng dòng:

```
   scripts/rebuild_db.py  buoc 1 = load_billing --rebuild
        -> db/connect.py:251   DROP SCHEMA public CASCADE; CREATE SCHEMA public;
              -> xoa MOI GRANT: schema + 20 bang + 3 view
              -> xoa ca ALTER DEFAULT PRIVILEGES ... IN SCHEMA public

   docker/read-only-api.sql   la cho cap lai
        -> CHI chay qua container `api-db-init`,  restart: "no"
```

Đo ngày 02/09 bằng chính vai mà container `api` dùng:

```
   api_readonly thu GHI  ->  ReadOnlySqlTransaction  SQLSTATE 25006     DAT
   api_readonly thu DOC  ->  0/20 bang · 0/3 view
                             has_schema_privilege(...,'public','USAGE') = False
```

Timeline khớp mốc container với mtime file bằng chứng:

```
   02/09 16:08:31 VN   api-db-init xong      -> quyen duoc cap
   02/09 16:14:06 VN   rebuild_db.py xong    -> quyen bi xoa
   02/09 16:52:14 VN   container `api` tat   -> 38 phut chay tren DB no khong doc noi
```

**Và không bộ kiểm nào bắt được:**

```
   scripts/audit_db.py     chay bang vai `token` (chu schema)  -> 42 phep, DAT het
   backend/check_api.py    read_only() thu CREATE TEMP TABLE, cho bi tu choi
                           MAT QUYEN DOC thi lenh ghi VAN bi tu choi
                           -> bao DAT dung luc API mu hoan toan
```

Phép kiểm không phân biệt **"chặn ghi"** với **"mất quyền đọc"**. Lần 02/09 vô hại vì stack tắt
ngay sau đó; hình dạng nguy hiểm là chạy `rebuild_db.py` trong lúc stack đang bật.

### ④ Độ trễ: hai nguồn lệch 31,9 lần, và chưa ngày nào giao nhau để biết vì sao

Dòng 17 đòi *"truy vấn và endpoint mới cho các chỉ tiêu từ Gateway"*. Chỉ tiêu đáng giá nhất là
độ trễ: Gateway giữ `duration_ms` **từng lượt**, nên phân vị tính chính xác thay vì nội suy.

Nghiệm thu phép tính trước — p95 Gateway ngày 31/08 từ số thô:

```
   38 mau  ->  p50 0,788 s · p95 1,822 s · p99 2,702 s
   khop dung con so change 006 da tinh tay
```

Nhưng so với nguồn thủ công (histogram Cloud Monitoring, gộp bởi
`scripts/merge_latency_daily.py`) cho **cùng agent 6**:

```
   thu cong (histogram)   p95  28,941 - 64,748 s   TB 58,206 s   681 mau / 15 ngay
   gateway  (so tho)      p95              1,822 s               38 mau  / 1 ngay
                                    ^ chenh 31,9 lan
```

Ba phép đo loại trừ các giải thích dễ dãi:

```
   (a) KHONG phai o histogram rong:
       38 luot Gateway  min 609 ms · max 3.136 ms · TB 1.003 ms
       tren 10 giay: 0 luot        tren 33,55 giay: 0 luot

   (b) KHONG phai mau it:
       thu cong TB 45,4 luot/ngay (11-145)      gateway 38 luot

   (c) p50 cung lech, ma p50 it chiu sai so o hon nhieu:
       thu cong TB 19,66 s   vs   gateway 0,788 s   -> lech 24,9 lan
```

Ô cuối **có** bão hoà thật, nhưng chỉ ở vài agent nên không giải thích được toàn bộ:

```
   agent 6  86,7% so ngay p95 roi vao o >= 33,55s    p50 TB 19,66 s
   agent 7  64,0%                                    p50 TB 25,56 s
   agent 5  42,9%                                    p50 TB  9,76 s
   agent 1   3,2%                                    p50 TB  3,14 s
   agent 2   0,0%                                    p50 TB  3,47 s
```

Và **không ngày nào chồng lấn** giữa hai nguồn:

```
   fact_latency_daily   dung 29/08   (7/8 agent, thieu Ralli - chua noi GCP)
   fact_call gateway    bat dau 31/08 (1 agent)
   so ngay co CA HAI:   0
```

Nên chưa nguồn nào kiểm chứng được nguồn kia. **Điều đó không chặn việc xây** — nó chỉ chặn
**một** quyết định: nguồn nào đứng trước khi cả hai cùng có số.

### ⑤ Tầng đọc chưa sẵn sàng nhận nguồn thứ hai cho độ trễ

Phần **dữ liệu** của việc này đã có chủ: change `fill-the-declared-fields-and-log-by-the-hour`
sở hữu việc 5.3 (cột `source` cho hai bảng phân vị) và 7.1–7.5 (tính p50/p95/p99 từ
`duration_ms` thô). Change này **không** làm lại — xem design ⑨.

Nhưng change đó dừng đúng ở tầng dữ liệu. Design ⑥ của nó viết: *"để cạnh nhau… `usage_resolved`
chọn một khi cần một con số duy nhất"* — mà `usage_resolved` **không** có độ trễ. Không view nào
chọn hộ, và **tầng đọc thì chưa chịu nổi hai dòng**:

```
   fact_latency_daily   339 dong · khoa (day, agent_id)
   fact_perf_daily      669 dong · khoa (day, agent_id, method, response_code)
```

Ngày cả hai nguồn cùng có số, `api.js:187` **ghi đè âm thầm**:

```js
   (perf.latency || []).forEach(function (x) {
     var d = slot(x.day + "|" + x.agent_id);
     d.lat = x.p95_seconds || 0;     // GAN DE, khoa khong co `source`
   });
```

`backend/store.py:performance()` sắp xếp `ORDER BY day, agent_id` — **không có tie-break trên
nguồn**. Hai dòng cho cùng (ngày, agent) thì dòng đến sau thắng, và không ai biết là dòng nào.
Không crash, không nhân đôi — chỉ là một con số không xác định.

## What Changes

**① Kỷ luật chỉ-đọc sống sót qua `rebuild_db.py`** *(dòng 17, vế 2)*

- `scripts/rebuild_db.py` thêm một bước cuối **kiểm quyền của vai đọc**, thiếu thì **dừng và
  báo** — chọn báo động thay vì tự chữa, để con người nhìn thấy.
- `backend/check_api.py:read_only()` phải thử **cả một câu SELECT**, không chỉ một câu ghi.
  Phép kiểm hiện tại cho cùng kết luận với hai trạng thái ngược nhau.

**② Chiều người dùng cho cả 8 agent** *(dòng 18)*

- View mới dựng trên `usage_resolved`, JOIN **hai lần** — một theo `token_source`, một theo
  `call_source` — vì billing không có `calls`.
- `whole_agent` và `unattributed` **giữ và hiện ra**, không giấu. Chúng là 2,2% mà ta thật sự
  không quy được về account nào.
- `/api/usage-by-account` trả về view mới.

**③ Một con số độ trễ trên dashboard, chọn ở tầng dữ liệu** *(dòng 17, vế 1)*

- View `latency_resolved`: mỗi (ngày, agent) **chọn một** nguồn, **không** trung bình — phân vị
  không cộng được.
- `backend/store.py` + `web/js/api.js` đọc theo nguồn đã chọn, **hết ghi đè**.
- Dashboard hiện **một con số, không nhãn nguồn** — theo đúng yêu cầu. Việc chọn nguồn xảy ra ở
  tầng dữ liệu, không ở tầng hiển thị.
- **Thứ tự ưu tiên tạm: `monitoring` trước `gateway`.** Xem design ⑥.

**④ Phụ thuộc, không làm lại** *(dòng 17)*

Cột `source` cho hai bảng phân vị và phép tính p50/p95/p99 từ `duration_ms` thô thuộc change
`fill-the-declared-fields-and-log-by-the-hour` (việc 5.3, 7.1–7.5). Change này **phụ thuộc**
vào chúng và không viết lại — xem design ⑨.

**⑤ Sửa câu chữ Master Plan** *(dòng 16, dòng 18)*

- Dòng 16: *"báo cáo đối chiếu chênh lệch giữa bốn nguồn"* → *"phép kiểm đối chiếu nguồn, chạy
  trong quá trình phát triển"*. Bỏ ràng buộc chạy song song 2 tuần khỏi đường găng.
- Dòng 18: *"tỷ lệ áp dụng theo **phòng ban**"* → *"theo **agent**"*. Mã đã làm đúng theo agent
  từ 14/08 và có lý do ghi lại; câu chữ mới là chỗ sai.

**Không đụng:** sổ `LiteLLM_SpendLogs` (chỉ đọc), ba bộ số cũ, `db/load_gateway.py`,
`ref_source`, `db/build_performance.py`, và mọi việc của change
`fill-the-declared-fields-and-log-by-the-hour`.

## Impact

- **Dòng 18 từ 0/1 lên 1/1**: chiều người dùng phủ **8/8 agent** thay vì 2/8, và về đích trước
  mốc 21/10.
- **Dòng 17 từ 1/2 lên 2/2**: backend đọc được cột riêng của Gateway, và vế "chỉ-đọc" hết hỏng.
- **Dòng 16 vế 2 hết bị chặn**: không còn phụ thuộc kỳ chạy song song trên agent production.
- Độ trễ hiện phân vị **chính xác** cho ngày Gateway phủ, thay vì nội suy trong ô rộng trung
  bình 31,3 giây (agent 6) — nơi sai số bằng 54% chính giá trị p95.

**Phụ thuộc:** phần ③ cần việc 5.3 và 7.1–7.5 của change
`fill-the-declared-fields-and-log-by-the-hour` xong trước. Phần ① và ② **không** phụ thuộc gì —
làm được ngay.

**Rủi ro ①: con số p95 trên màn hình đổi.** Bốn chỗ hiển thị (`app.js` dòng 2384, 2900, 3518,
3531), và `A.lat` là trung bình có trọng số theo số request (`app.js:1155,1172`) chứ không phải
số lấy thẳng. Chọn `monitoring` đứng trước làm rủi ro này bằng **không** trong lúc chưa đo được
— xem design ⑥.

*(Đã kiểm: ngưỡng cảnh báo SLO độ trễ `latencyWarning` / `latencyCritical` ở `app.js:46-47` đều
`null`, tức cảnh báo đang tắt. Nên không cảnh báo nào tự đổi trạng thái theo con số này.)*

**Rủi ro ②: nghiệm thu view mới bằng một con số là chưa đủ.** Đã đo: cách JOIN chỉ theo
`token_source` cho token khớp **tuyệt đối** (lệch 0) trong khi calls hụt **77,9%**
(27.056/122.504). Nghiệm thu phải là **hai** con số — xem design ②.

**Rủi ro ③: thứ tự ưu tiên nguồn độ trễ chưa có cơ sở.** Đây là điều duy nhất trong change này
chưa trả lời được. Nó được cô lập vào **một** `CASE` trong một view, nên đổi sau là sửa một
dòng. Phép đo trả lời nó nằm ngoài change này (buổi chạy DMS trong project Google One).
