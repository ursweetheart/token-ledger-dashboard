# Soát ba mục STT 6 — Tích hợp với FE / BE / DB đã có (03/09/2026)

Đo trên database thật `token_ledger_v2`, đọc bằng session read-only (mọi lệnh ghi
bị máy chủ từ chối `SQLSTATE 25006`). Không mục nào trong ba mục đã xong.

| Dòng | Mục tiêu | Mốc | Trạng thái đo được |
|---|---|---|---|
| 16 | Đưa dữ liệu Gateway vào database hiện tại | 30/09 | 1/2 sản phẩm — vế còn lại **chưa làm được** |
| 17 | Mở rộng backend đọc, giữ nguyên kỷ luật chỉ-đọc | 07/10 | 1/2 sản phẩm — và vế "chỉ-đọc" đang hỏng theo hướng ngược |
| 18 | Cập nhật dashboard cho chiều người dùng đầy đủ | 21/10 | 0/1 — biểu đồ đủ, dữ liệu không đủ |

---

## 1. Bốn nguồn KHÔNG giao nhau ngày nào

Sản phẩm dòng 16 đòi *"kiểm tra và báo cáo đối chiếu chênh lệch giữa bốn nguồn"*.
Không có script, không có tài liệu, không có phép kiểm nào trong 42 phép của
`scripts/audit_db.py`. Nhưng lý do sâu hơn là **chưa đối chiếu được**:

```
   app          371 dong · 154 ngay   2026-03-14 -> 2026-08-30   112.775.370 token
   billing    1.012 dong · 240 ngay   2026-01-01 -> 2026-08-29   751.189.404 token
   monitoring   606 dong · 135 ngay   2026-04-17 -> 2026-08-29   496.933.793 token
   gateway        1 dong ·   1 ngay   2026-08-31 -> 2026-08-31        45.187 token

   so ngay co DU CA BON nguon:  0
   nhieu nhat cung mot ngay:    3 nguon (132 ngay) · 2 nguon (24) · 1 nguon (86)
```

Và ngày duy nhất có Gateway thì Gateway **là nguồn duy nhất có số**:

```
   2026-08-31  ->  gateway
                   khong billing · khong monitoring · khong app
```

Ba nguồn cũ đều dừng trước đó 1–2 ngày. Nên không chỉ chưa đối chiếu được bốn
nguồn — chưa đối chiếu được với **dù chỉ một** nguồn nào khác.

Đây đúng cái bẫy đã mắc hai lần (change 006 với độ trễ, mục 3 của change đang dở
với `cached_tokens`): so hai giai đoạn không giao nhau rồi kết luận. Việc này bị
chặn bởi kỳ chạy song song ở **STT 7 dòng 19**, không phải bởi thiếu công sức.

**Vế đã xong của dòng 16:** `ref_source` có dòng `gateway`; `usage_resolved` cho
gateway đứng đầu COALESCE token và calls; `load_gateway` là bước 6/8 của
`scripts/rebuild_db.py`, đọc thẳng `LiteLLM_SpendLogs` qua vai `gateway_readonly`
nên mỗi lần dựng lại database là tự có số mới.

---

## 2. Backend chưa đọc một cột nào của Gateway

```
   grep -rn "gateway"   backend/  ->  3 ket qua, CA BA deu la ghi chu
   grep -rn "fact_call" backend/  ->  0 ket qua
```

9 endpoint hiện có đều không biết nguồn. Số Gateway *đi nhờ* qua `usage_resolved`,
nhưng đó là thừa hưởng chứ không phải mở rộng. Mọi cột riêng của Gateway nằm lại
trong `fact_call`:

```
   fact_call gateway  n=41   duration_ms 38/41 · unit_id 41/41 · virtual_key 41/41 · cached 0/41
   fact_call app      n=8631 duration_ms  0/8631 · unit_id 8631/8631 · virtual_key 0/8631

   fact_latency_daily  9 cot · KHONG co cot `source`
   fact_perf_daily     5 cot · KHONG co cot `source`
```

Độ trễ thô 38/41 lượt không có đường nào lên API: hai bảng phân vị không có cột
`source` nên chưa đổ số Gateway vào được mà không trộn với monitoring. Cột
`source` cho hai bảng này là việc 5.3 của change
`fill-the-declared-fields-and-log-by-the-hour`.

Cột Kết quả dòng 17 đang **để trống**, và trống là đúng hiện trạng.

---

## 3. Vai `api_readonly` mất sạch quyền đọc sau mỗi lần dựng lại database

Đây là phát hiện ngoài dự tính, tìm được vì bộ đo cố tình nối bằng đúng vai mà
container `api` dùng.

```
   M6a  api_readonly thu GHI  ->  ReadOnlySqlTransaction SQLSTATE=25006   DAT
   M6b  api_readonly thu DOC  ->  0/20 bang · 0/3 view
                                  has_schema_privilege('api_readonly','public','USAGE') = False
```

### Nguyên nhân, truy được đến từng dòng

```
   scripts/rebuild_db.py  buoc 1 = load_billing --rebuild
        -> db/connect.py:251   DROP SCHEMA public CASCADE; CREATE SCHEMA public;
        -> xoa MOI GRANT tren schema, tren 20 bang, tren 3 view,
           va ca cac dong ALTER DEFAULT PRIVILEGES gan voi schema do

   docker/read-only-api.sql   la cho cap lai
        -> chi chay qua container `api-db-init` (restart: "no")
```

### Timeline, khớp mốc container với mtime file bằng chứng

```
   02/09 16:08:31 VN   api-db-init xong        -> quyen duoc cap
   02/09 16:14:06 VN   rebuild_db.py xong      -> quyen bi xoa   (var/rebuild-cuoi.txt)
   02/09 16:52:14 VN   container `api` tat     -> 38 phut chay tren DB no khong doc noi
```

### Vì sao không bộ kiểm nào bắt được

```
   scripts/audit_db.py         chay bang vai `token` (chu schema)  -> 42/38/4/0 DAT
   backend/check_api.py
     read_only()               thu CREATE TEMP TABLE, cho bi tu choi
                               mat quyen doc thi lenh ghi VAN bi tu choi
                               -> van DAT dung luc API mu hoan toan
```

Phép kiểm khẳng định *"kỷ luật chỉ-đọc còn nguyên"* trong khi vai đó không đọc
nổi một bảng. Nó không phân biệt **chặn ghi** với **mất quyền đọc**.

### Mức nghiêm trọng

Lần 02/09 vô hại vì stack đã tắt ngay sau đó. Hình dạng nguy hiểm là:
**chạy `rebuild_db.py` trong lúc stack đang bật** — API mù ngay lập tức, không ai
được báo, và cả hai bộ kiểm đều báo lành.

`docker compose up -d` tự chữa, vì `api` khai
`depends_on: api-db-init: service_completed_successfully`. Đây là **suy luận từ
cấu hình compose**, chưa chạy để chứng minh.

**Chưa biết:** lần 02/09 có phải lần đầu không. Không có nhật ký các lần trước,
nên không rõ chuyện này đã lặp bao nhiêu lần và có lần nào rơi vào lúc ai đó đang
xem dashboard không.

---

## 4. Ba biểu đồ chiều người dùng: đủ biểu đồ, thiếu dữ liệu

Cả ba canvas (`c-dep-adopt`, `c-us-dau`, `c-dep-cost`) có từ commit `c028bc6`,
trước khi bắt đầu Gateway. Cái thiếu là **dữ liệu cho 8 agent**, và mỗi biểu đồ
thiếu một kiểu khác nhau.

| Biểu đồ | Phủ được | Vấn đề |
|---|---|---|
| Tỷ lệ áp dụng | 8/8 agent | khoá theo **AGENT**, không theo phòng ban |
| Người dùng hoạt động theo ngày | **2/8** agent | trần thiết kế, không phải thiếu công |
| Chi phí theo phòng ban | **8 lát / 130 đơn vị** | thực chất là chi phí theo agent |

### 4.1 Nguồn biết người dùng chỉ phủ 3/8 agent

```
   nguon BIET NGUOI DUNG (ref_source.knows_user):  app · gateway

   Chatbot Contact Center     billing,monitoring            -
   Multi modal AI Invoice     billing,monitoring            -
   Phan Loai Du Lieu CRM      billing,monitoring            -
   Phan Loai Phan Hoi Tiep T  billing,gateway,monitoring    gateway
   Sale Agent                 billing,monitoring            -
   Tools Quizzer              billing,monitoring            -
   Tro Ly Ao Hop Dong         app,billing,monitoring        app
   Tro ly ao Ralli            app                           app
```

### 4.2 Biểu đồ 1 — có đủ 8 cột, nhưng 6 cột là 1/1

```
   Chatbot Contact Center     service   1/1  = 100,0%
   Multi modal AI Invoice     service   1/1  = 100,0%
   Phan Loai Du Lieu CRM      service   1/1  = 100,0%
   Phan Loai Phan Hoi Tiep T  service   1/1  = 100,0%
   Sale Agent                 service   1/1  = 100,0%
   Tools Quizzer              service   1/1  = 100,0%
   Tro Ly Ao Hop Dong         people   21/43 =  48,8%
   Tro ly ao Ralli            people   27/892 =  3,0%
```

Sáu agent chạy bằng tài khoản dịch vụ nên mẫu số là 1. `web/js/app.js:2274` ghi rõ
đây là quyết định có cân nhắc từ 14/08: ép vào cây phòng ban thì sáu agent kia
vĩnh viễn không có mẫu số, và trước 14/08 biểu đồ này trắng vì đúng lý do đó.

**Nhưng Master Plan dòng 18 viết *"tỷ lệ áp dụng theo phòng ban"*.** Một trong hai
đang sai chữ — cần chốt, không phải cần sửa mã.

### 4.3 Biểu đồ 2 — trần cứng 2/8 agent

```
   usage_by_account ca ky 2026-01-01 -> 2026-08-31
     337 dong · 2 agent · 53 tai khoan · 24 don vi
     agent: Tro Ly Ao Hop Dong, Tro ly ao Ralli
     kind=real  53 tai khoan  108.554.843 token   (khong co kind nao khac)
```

Định nghĩa của view (`db/migrations/sql/001_baseline.sql`):

```sql
WHERE f.source IN (SELECT source FROM ref_source WHERE knows_user)
  AND a.kind = 'real';
```

DMS đi qua Gateway **có** `knows_user`, nhưng quy về tài khoản dịch vụ 949 nên
`kind='real'` loại nó ra — và loại **đúng**, view này là bảng người dùng.

**Hệ quả cho kế hoạch:** thêm agent vào Gateway sẽ **không** tự làm biểu đồ này
đầy lên, chừng nào agent còn gọi bằng tài khoản dịch vụ. Muốn đầy thì phải có
agent nhiều-người-dùng đi qua Gateway với `end_user` là người thật.

### 4.4 Biểu đồ 3 — không phải chi phí theo phòng ban

```
   backend/store.py  usage_by_account()   SELECT ... KHONG co cost_usd
   web/js/api.js:330 var u = unit[x.agent_id]    <- primaryUnit() = DON VI GOC cua agent
   web/js/app.js:2255 groupRowsByUnit(rows) -> donut c-dep-cost
```

Đo ra:

```
   dim_unit co 130 don vi, primaryUnit chi tra ve 8

     __technical_1__  Don vi su dung Chatbot Contact Center
     __technical_2__  Don vi su dung Sale Agent
     __technical_3__  Don vi su dung Multi modal AI Invoice
     __technical_4__  Don vi su dung Tools Quizzer
     __technical_6__  Don vi su dung Phan Loai Phan Hoi Tiep Thi
     __technical_7__  Don vi su dung Phan Loai Du Lieu CRM
     ef5f9f4c-...     Cong ty CPBD PN Rang Dong    (goc cay TLA HD)
     69ee5b13...      Toan cong ty                 (goc cay Ralli)
```

Sáu lát đầu chính là tên agent đổi nhãn. Hai lát cuối là **gốc cây**, tức toàn bộ
công ty gộp làm một. Không lát nào là một phòng ban.

Tiền không tồn tại ở mức tài khoản (`usage_by_account` không có `cost_usd`), nên
donut không trả lời được *"phòng Kinh doanh tiêu bao nhiêu"* — nó trả lời *"agent
nào tiêu bao nhiêu"*, dán nhãn bằng tên đơn vị gốc.

Bảng xếp hạng phòng ban (`deptRankByAccounts`) thì đúng ở mức tài khoản, nhưng
cộng **số request**, không cộng tiền.

```
   usage_resolved ca ky: 1.276 dong · 8 agent
   dong CO cost_usd: 1.013/1.276 · agent co tien: 7/8   (Ralli chua noi billing)
```

### 4.5 Trần chung của chiều người dùng

Từ `scripts/audit_db.py`, phép kiểm "Coverage of the 'who used it' dimension":

```
   (a) nguoi that          107.125.668 = 11,7%
   (b) tai khoan dich vu   793.613.395 = 86,6%
   (c) khong quy duoc       15.230.908 =  1,7%
```

---

## 5. Những gì còn chưa chắc chắn

**Chứng minh được:** toàn bộ số ở trên, gồm cả timeline mất quyền.

**Mới là suy luận:**

- `docker compose up -d` cấp lại quyền — đọc từ cấu hình compose, chưa chạy để kiểm.
- Lần mất quyền 02/09 là lần đầu tiên — không có nhật ký các lần trước.

---

## 6. Việc rút ra, chưa làm

1. **Bịt lỗ hổng `DROP SCHEMA` xoá GRANT.** Cần sửa mã, không phải chạy một lệnh.
   Hai hướng: `rebuild()` tự gọi lại phần cấp quyền, hoặc `rebuild_db.py` thêm một
   bước cuối kiểm quyền và dừng nếu thiếu.
2. **Phép kiểm `read_only()` phải phân biệt "chặn ghi" với "mất quyền đọc".** Hiện
   một câu SELECT thất bại cũng cho cùng kết luận như một câu INSERT bị chặn.
3. **Chốt câu chữ dòng 18**: "theo phòng ban" hay "theo agent". Là quyết định sản
   phẩm, không phải lỗi mã.
4. **Cập nhật cột Kết quả dòng 16 / 17 / 18** theo số đo thật ở tài liệu này.
