# Nhật ký sáng 21/08/2026

Tiếp theo `nhat-ky-20-08-chieu.md`. Đọc nhanh: mục 1 và mục 6.

**Chưa commit.** Mọi phép kiểm xanh.

---

## 1. Tóm tắt

> Sáng nay biến câu *"hệ thống đã sẵn sàng đón Gateway chưa"* từ một **ý kiến** thành một
> **con số** — rồi sửa cho con số đó về 7/7.

Ba việc, theo thứ tự:

```
   ① Đo JWT của hai app        -> A3 đóng, và phát hiện một cái bẫy
   ② Soạn 2 proposal            -> đón nguồn thứ tư · khoá cho API
   ③ Làm trọn proposal ①        -> 40/40 task
```

Nhóm A trong `viec-can-lam-truoc-api-gateway.md` **hết việc đỏ**. Nhóm B cũng vậy.

---

## 2. Đo JWT: hai app **không** dùng cùng claim

Câu chốt A3 hôm 20/08 là *"agent tự giải mã JWT rồi gửi username lên Gateway"*. Câu đó còn
một chữ chưa xác định: **trích claim nào**. Đăng nhập cả hai app rồi giải mã payload:

```
   Trợ lý ảo Ralli                 Trợ Lý Ảo Hợp Đồng
   ┌────────────────────┐          ┌──────────────────────────┐
   │ sub  = "admin"     │          │ sub      = "user-admin"  │ ← KHÔNG phải username
   │ role = "ADMIN"     │          │ username = "admin"       │ ← username ở ĐÂY
   │ exp                │          │ role, company_id         │
   └────────────────────┘          │ unit_id  = ""   (rỗng)   │
   3 claim · HS256 · ~2h           └──────────────────────────┘
                                   6 claim · HS256 · ~8h
```

**Quy ước không được rút gọn thành "lấy `sub`".** Viết vậy — cách viết tự nhiên nhất — thì
agent Hợp Đồng gửi lên `user-admin`: chuỗi hợp lệ, không có trong bảng `account`, JOIN ra
rỗng, **không lỗi nào báo**.

| Agent | Claim |
|---|---|
| Trợ lý ảo Ralli | `sub` |
| Trợ Lý Ảo Hợp Đồng | **`username`** (không phải `sub`) |
| 6 agent một-người-dùng | hằng số `svc.<code>` |

**Bẫy thứ hai: claim `unit_id` của Hợp Đồng tồn tại nhưng RỖNG.** Nó trông như một lối tắt
cho phòng ban. Quyết định 20/08 *"tra `account.unit_id`, agent không cần gửi phòng ban"* vì
thế không chỉ tránh nguồn-sự-thật-thứ-hai — nó tránh đúng một cái bẫy đang nằm sẵn.

**Nỗi lo "Ralli trả ObjectId" nhắm sai chỗ.** Cảnh báo ở `01_schema.sql:139` nói về *bản ghi
sử dụng*, không phải JWT. Đo hai đầu độc lập, ra cùng một hình dạng:

| | Ralli `/users/list` | `account` (kind='real') |
|---|---:|---:|
| dạng có dấu chấm (`c4led.lamln`) | 814/891 | **814/937** |
| là ObjectId 24 hex | **0**/891 | **0**/937 |

Trùng khít. Nghĩa là dòng Gateway nối thẳng vào `account_id` đang có — **không phải mở rộng
bảng `account`**.

**Điều chưa chứng minh được:** tài khoản trong `.env` là **ADMIN** ở cả hai app, không nằm
trong danh bạ 891 dòng. Anh quyết **không đợi** token nhân viên thường. Thay bằng một phép
kiểm (mục 4 ③).

---

## 3. Đo trước khi sửa — và dashboard đứng im trước 4 triệu token

`tools/dien_tap_gateway.py`: chèn dòng `source='gateway'` mang username **THẬT**, chạy toàn
bộ phép kiểm, so số trước/sau, rồi `ROLLBACK`.

Chạy **trước** khi sửa gì:

| | trước | sau | |
|---|---:|---:|---|
| `usage_by_account` dòng | 320 | 320 | **+0** |
| tỷ lệ áp dụng agent 8 | 24 | 24 | **+0** |
| quy về người thật | 104.990.903 | 104.990.903 | **+0** |
| `usage_resolved` dòng | 1.189 | 1.192 | +3 |
| `usage_resolved` token | 867.657.110 | 867.657.110 | **+0** |
| `usage_resolved` dòng **KHÔNG có token** | 10 | **13** | **+3** |

**TRƯỢT 8/8.** Và triệu chứng rõ hơn dự đoán: `usage_resolved` *có* thêm khoá, nhưng
`COALESCE(b, m, a)` không biết `gateway` nên trả `NULL`. Dữ liệu nằm trong database và
**vô hình**.

> Vì sao chạy trước mới có giá trị: danh sách chỗ trượt **là bản đặc tả**. Trước đó phạm vi
> của việc này chỉ là một kết quả `grep`.

Và bịa `account_id` thì phép thử chỉ chứng minh *"SQL chạy được"*. Dùng username thật mới
chứng minh *"Gateway nối được vào dữ liệu đang có"* — cùng công sức, khác hẳn giá trị.

---

## 4. Đã sửa gì

### ① Nguồn tự khai năng lực, thay cho một chuỗi mang nghĩa ngầm

```sql
ref_source(source, knows_user, has_invoice_cost, era, note)

   app          TRUE   FALSE   scrape
   billing      FALSE  TRUE    scrape
   monitoring   FALSE  FALSE   scrape
   gateway      TRUE   FALSE   gateway
```

`source = 'app'` ở **đầu đọc** không có nghĩa "nguồn tên app" — nó có nghĩa **"nguồn duy
nhất biết ai là người dùng"**. Hai nghĩa đó trùng nhau cho tới ngày Gateway xuất hiện. Giờ
8 chỗ đầu đọc hỏi `knows_user`, và thêm nguồn thứ năm sẽ là **thêm một dòng dữ liệu**.

Cột `source` cũng thành khoá ngoại: nguồn lạ bị chặn **ngay lúc ghi**.

### ② `usage_resolved` ưu tiên Gateway trước hoá đơn

`COALESCE(g, b, m, a)`. Gateway là bộ đếm của chính ta và có mặt ngay trong ngày, còn hoá
đơn Google về trễ ~1 ngày. Trong kỳ chạy song song 2 tuần (giai đoạn 7) cả bốn nguồn cùng
có dữ liệu cho cùng một ngày — không chốt thứ tự thì con số đổi tuỳ nguồn nào nạp sau.

**Nhưng KHÔNG ưu tiên về tiền.** `cost_usd` vẫn chỉ lấy của `billing`. Lý do ở mục 5 ②.

### ③ Tên của 6 tài khoản dịch vụ

```
   __whole_agent_1__  ->  svc.contact-center
   __whole_agent_2__  ->  svc.sale-agent
   ... 6 dòng, suy từ dim_agent.code, không gõ tay
```

Đây không phải đổi tên cho đẹp: ngày Gateway chạy, 6 agent một-người-dùng gửi lên **đúng
chuỗi này** làm username.

Ghi chú tại chỗ ở `load_org.py:568` đã cảnh báo trước: *"đừng đổi tên ở đây,
`build_usage_daily.py` tra tài khoản này BẰNG TÊN ĐĂNG NHẬP"*. Sửa **không phải** bằng cách
đổi chuỗi ở hai nơi, mà bỏ hẳn phụ thuộc: nó tra bằng `(kind, unit_agent_id)` — hỏi đúng
câu nó cần hỏi.

### ④ Ba phép kiểm mới, và cả ba đều đã chứng minh là **kêu được**

| | |
|---|---|
| Tài khoản dịch vụ đặt tên `svc.<code>` | lệch một ký tự là Gateway gửi lên tên không tra ra ai |
| Dòng ký nguyên `gateway` rơi vào chỗ "không biết ai" | **lưới an toàn thay cho việc chờ token nhân viên** |
| Nguồn không có tiền hoá đơn mà mang `cost_usd` | số tiền đó sẽ biến mất khỏi dashboard |

---

## 5. Bốn lần "đo lại thì khác với lúc soạn proposal"

Phần đáng đọc nhất, vì cả bốn đều là **lập luận nghe hợp lý** viết trong proposal buổi sáng
rồi bị chính việc thực thi bác bỏ.

### ① "10 chỗ đầu đọc" — thực ra là **8**

Hai chỗ tôi xếp vào đầu đọc thực ra là **định nghĩa**, và Gateway lọt vào đó mới là sai:

| Chỗ | Câu nó hỏi |
|---|---|
| `01_schema.sql` CTE `a` | *"gom các dòng CỦA nguồn app"* |
| `audit_db.py:163` | *"khâu nạp app ghi đúng bằng hai bảng app không"* |

### ② `has_cost` cho gateway — phải là **FALSE**

Suýt đặt `TRUE` vì LiteLLM rõ ràng có trả về một con số tiền. Nhưng nó **tự nhân từ bảng
giá**, y hệt `ref_price`. Đặt TRUE rồi đổ vào `cost_usd` là biến tiền **suy ra** thành tiền
**đã xác nhận** — đúng thứ cả ngày 20/08 đi bịt.

Đã đổi tên cột thành `has_invoice_cost` để không ai đọc nhầm lần nữa. Và để `cost_usd` NULL
hoá ra **đúng hơn**: dòng Gateway tự động được tính lại từ `ref_price` **và** được gắn dấu
`≈`, đúng bản chất của nó cho tới ngày hoá đơn về.

### ③ Phép kiểm "nguồn lạ lọt vào dữ liệu" — **không kêu được**

Khoá ngoại đã chặn ngay lúc ghi, nên phép kiểm này vĩnh viễn im lặng. Một phép kiểm không
thể kêu **còn tệ hơn không có** — nó tạo cảm giác đã được kiểm. Bỏ, thay bằng một dòng
trong bảng `FOREIGN_KEYS` (chỗ đó *kêu được* với bản SQLite và với database dựng từ schema
cũ).

Đúng bài học `data_to` ngày 20/08, lặp lại sau một ngày.

### ④ Phép kiểm "mọi dòng từ nguồn biết người đều quy được" — kêu ngay **21 dòng**

Và nó **đúng**. Nguồn `app` *biết được* người dùng nhưng **không phải lúc nào cũng biết**:
nhật ký Ralli có lượt không kèm user, khâu nạp lùi về `__unattributed__` một cách có chủ ý.

> *"Nguồn này có thể mang danh tính"* khác *"mọi dòng đều có danh tính"*.

Chỉ `era='gateway'` mới đòi được vế sau, vì A3 bảo đảm mọi request mang danh tính.

### ⑤ Và một lỗi trong chính công cụ đo

Lần chạy sau khi sửa ra **5/7**, hai kỳ vọng trượt. Không phải code sai — **kịch bản của
tôi tự chép lại câu SQL của `store.py`**, và bản chép vẫn còn `token_source = 'app'`. Nó
đang đo bằng đúng cái logic mà change này vừa bỏ đi.

Một phép kiểm đo **bản sao** của thứ nó phải kiểm thì nó đang kiểm chính nó. Đã sửa bằng
cách gọi thẳng `store.health()` và `store.adoption()`.

Cùng cái bẫy mà cả change này đi bịt, chỉ khác chỗ: **một khái niệm cài đặt hai lần thì một
bản sẽ trôi.**

---

## 6. Đang ở đâu

### Nghiệm thu

```
   rebuild        7/7 bước, 63 giây
   audit_db       36 phép | 31 đạt | 5 lưu ý | 0 hỏng
   check_api      16/16
   test JS        6 + 7
   diễn tập       DAT 7/7   (trước khi sửa: TRƯỢT 8/8)
```

**Bất biến giữ nguyên tuyệt đối** — change này đổi *cách hỏi*, không đổi *câu trả lời*:

```
   usage_resolved     1.189 dòng · 867.657.110 token · $291,985601
   usage_by_account     320 dòng · 107.926.810 token
   độ phủ             104.990.903 / 749.483.267 / 13.182.940
```

Không lệch một token.

### Hai change OpenSpec

| | |
|---|---|
| `admit-gateway-as-a-fourth-source` | **40/40 xong** |
| `require-a-key-to-read-the-api` | 0/25 — chưa bắt đầu |

### File đã đổi (chưa commit)

```
 M backend/store.py            M db/01_schema.sql
 M db/build_usage_daily.py     M db/load_org.py
 M scripts/audit_db.py         ?? tools/dien_tap_gateway.py
 M 3 tài liệu tham chiếu       ?? 2 thư mục openspec/changes
```

### Còn treo

**🔴 C1 — backend vẫn không có xác thực nào.** Proposal đã soạn xong
(`require-a-key-to-read-the-api`, 25 task). Anh đã chọn hướng **khoá dùng chung** thay cho
JWT theo người, vì 8/8 endpoint là `GET` và **0 hành động đặc quyền** — không có gì để phân
vai. Câu "kho người dùng ở đâu" vì thế biến mất chứ không phải hoãn.

Task quan trọng nhất của change đó không phải task viết code:

> `5.2` Bỏ `DASHBOARD_KEY` rồi khởi động — máy chủ phải **không chạy**.

Chế độ hỏng phải là *"không chạy"*, tuyệt đối không phải *"chạy mở"*.

**🔴 Một việc chỉ anh trả lời được:** `Multi modal AI Invoice` chạy lại thật, hay còn tiến
trình sót? Phép kiểm vẫn kêu mỗi lần chạy `audit_db.py`.

**🟡 Còn lại:**

| | |
|---|---|
| A4 · A5 · A6 | Đều nằm trong `.xlsx` / `.docx` — không ai `git diff` được, nên chúng nằm im |
| D2 | Vẫn **0 file test Python** |
| D3 | Docker thiếu LiteLLM · Redis · Nginx |
| CSV | Chưa ai mở bằng Excel tiếng Việt |
| Git | 10 commit trên `Tuan-develop` chưa merge vào `main` |

### Phép nghiệm thu giờ đã có câu trả lời

Câu hỏi mở từ 20/08 — *"chèn dòng giả rồi xem có bao nhiêu chỗ vỡ"* — không còn là một đoạn
văn. Nó là `tools/dien_tap_gateway.py`, chạy được bất cứ lúc nào, không để lại dấu vết, và
hôm nay trả về **DAT 7/7**.
