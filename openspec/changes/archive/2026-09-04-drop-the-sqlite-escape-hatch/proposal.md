# Thôi giả vờ đỡ hai hệ quản trị

## Why

Dự án khai là chạy được cả PostgreSQL lẫn SQLite. `db/connect.py` mở đầu bằng đúng lời hứa
đó: *"HAI HỆ QUẢN TRỊ, MỘT BẢN SCHEMA — `01_schema.sql` chạy được cả PostgreSQL lẫn SQLite
vì không dùng SERIAL: mọi khoá đều gán tường minh."*

**Đo 24/08/2026: lời hứa đó đã sai từ 21/08, và không ai biết.**

### Bằng chứng — dựng một bản SQLite thì nó nổ

Gọi thẳng `sqlite3.executescript(01_schema.sql)`, đúng code `connect.run_sql_file()` đang
có, **không qua công cụ mới nào**:

```
   sqlite3.OperationalError: syntax error
   near "'nen van phai doi hoa don xac nhan - xem ghi chu cost_usd o usage_resolved.'"
```

Chỗ gây lỗi ở `01_schema.sql:348-349`, trong `INSERT INTO ref_source`:

```sql
'LiteLLM. Biết người dùng, có ngay trong ngày. Tiền của nó là SUY TỪ BẢNG GIÁ '
'nên vẫn phải đợi hoá đơn xác nhận - xem ghi chú cost_usd ở usage_resolved.'
```

Hai chuỗi **liền kề**. PostgreSQL nối lại theo chuẩn SQL; SQLite báo lỗi cú pháp.

### Vì sao nó nằm im được ba ngày

```
   17/08   xoa var/token_ledger.sqlite      change switch-default-dsn-to-postgres
           └── tu day KHONG CON database SQLite nao

   21/08   them bang ref_source             change admit-gateway-as-a-fourth-source
           └── bang gay loi ra doi SAU ngay do

   24/08   dung lai mot ban SQLite  ->  lo ra
```

Không phép kiểm nào chạy trên SQLite. `audit_db.py` và `check_api.py` đều cần một database
sống, và database sống duy nhất là PostgreSQL. Nhánh SQLite **chưa từng được chạy** kể từ
ngày nó thành không-có-dữ-liệu.

### Ba điều kiện của một đường quay về, không điều nào còn đúng

| Điều kiện | Trạng thái |
|---|---|
| Có dữ liệu để quay về | ❌ `var/` **rỗng** từ 17/08 |
| Dựng lại được | ❌ **hỏng cú pháp** từ 21/08 |
| Có phép kiểm canh | ❌ **không có phép nào** chạy trên SQLite |

Một đường quay về không dựng được, không có dữ liệu, và không ai kiểm — **không phải đường
quay về**. Nó là mã chết mang hình dạng của một bảo hiểm, và nó tệ hơn không có gì: nó
khiến người đọc `connect.py` tin rằng có đường lui.

### Và nó đang bắt mọi thứ mới phải trả phí

Change `change-the-schema-without-dropping-it` đang dở dang phải gánh theo:
`001_baseline_baseline.py` có một nhánh `executescript`, `db/migrations/env.py` có
`_sqlalchemy_url()` để thêm tiền tố `sqlite:///`, và task 3.5 đòi migration **giữ trung lập
hai hệ** — tức mọi migration về sau đều bị cấm dùng cú pháp riêng của PostgreSQL, để phục
vụ một đường không chạy được.

## What Changes

**Bề mặt đo được 24/08 — 8 file, không phải một dòng nào trong 19 câu truy vấn:**

| File | Gỡ gì |
|---|---|
| `db/connect.py` | `SQLITE_DSN` · `is_sqlite()` · nhánh trong `open_db()` · nhánh trong `run_sql_file()` · nhánh trong `rebuild()` · lời hứa "hai hệ" ở đầu file |
| `backend/store.py` | nhánh `sqlite3.connect(...mode=ro)` ở dòng 44-50 |
| `scripts/audit_db.py` | nhánh mở SQLite chỉ-đọc ở dòng 43-46 |
| `scripts/merge_billing.py` | nhánh ở dòng 203-209 |
| `scripts/copy_to_postgres.py` | **xoá cả file** — nó đòi một nguồn SQLite vốn không còn |
| `db/migrations/env.py` | `_sqlalchemy_url()` không còn việc gì |
| `db/migrations/versions/001_baseline_baseline.py` | nhánh `executescript` |
| `scripts/rebuild_db.py` · `db/load_billing.py` | dòng trợ giúp `--db` nói về `.sqlite` |

**GIỮ NGUYÊN `open_db()` trả về `(cn, placeholder)`.** Đây là quyết định quan trọng nhất
của change:

```
   15 cho goi open_db()/rebuild()      -> khong doi mot chu
   19 cho noi chuoi f"... = {ph}"      -> khong doi mot chu
```

Chỉ có **nhánh rẽ** biến mất; `placeholder` thành hằng `"%s"`. Gỡ luôn cả abstraction đó là
sửa 34 chỗ để đổi `{ph}` thành `%s` — một diff lớn, rủi ro thật, và **không mua thêm gì**.
Để lại kèm ghi chú tại chỗ nói vì sao nó còn sống thì rẻ hơn nhiều, và có thể dọn sau bằng
một change riêng nếu thấy vướng.

**KHÔNG làm trong change này**

- Không sửa lỗi nối chuỗi ở `ref_source`. Sau change này không còn ai chạy nó trên SQLite,
  nên nó thôi là lỗi — PostgreSQL vẫn nối đúng, và đã nối đúng suốt từ 21/08
- Không đụng 19 câu truy vấn dùng `{ph}`
- Không gỡ `psycopg2` khỏi bất kỳ đâu — nó là driver duy nhất còn lại, càng quan trọng hơn

## Impact

| | |
|---|---|
| **Specs** | `single-database-engine` (mới) |
| **Code** | `db/connect.py` · `backend/store.py` · `scripts/audit_db.py` · `scripts/merge_billing.py` · `db/migrations/env.py` · `001_baseline_baseline.py` · `scripts/rebuild_db.py` · `db/load_billing.py` |
| **Xoá** | `scripts/copy_to_postgres.py` |
| **Rebuild** | **Không.** Change này không đụng schema, không đụng dữ liệu |
| **Đồng nghiệp** | Ghi vào `dong-bo-may-dong-nghiep-*.md`: `--db <file>.sqlite` không còn nhận |
| **Không đụng** | `web/` · 19 câu truy vấn dùng `{ph}` · 15 chỗ gọi `open_db()` |
| **Rủi ro** | **Thấp.** Gỡ nhánh chưa từng chạy được từ 21/08. Mọi phép kiểm hiện có đều chạy trên PostgreSQL nên chúng canh được đúng thứ còn lại |
| **Quay lui** | Một commit. Và `git revert` lấy lại được nhánh SQLite — **nhưng lấy lại một nhánh hỏng**, nên đường lui thật là sửa lỗi nối chuỗi, không phải khôi phục code |

### Thứ tự: làm TRƯỚC khi xong `change-the-schema-without-dropping-it`

Change kia đang ở **13/44** và còn 5 nhóm chưa chạy. Làm cái này trước thì:

- Task **3.5** (*"migration phải giữ trung lập hai hệ"*) **biến mất** thay vì phải sửa
- `001_baseline_baseline.py` bớt một nhánh
- `env.py` bớt một hàm
- Nhóm 5–8 không phải nghĩ tới SQLite lần nào nữa

Làm sau thì đúng những chỗ đó phải viết ra rồi xoá đi.

### Cái bẫy đã biết

**`store.py` là đường đọc của backend đang chạy.** Nó mở kết nối chỉ-đọc, và `check_api.py`
có một phép kiểm khẳng định điều đó (*"Kết nối của backend là chỉ đọc
(ReadOnlySqlTransaction)"*). Gỡ nhánh SQLite ở đây phải giữ nguyên tính chất chỉ-đọc của
nhánh PostgreSQL — phép kiểm đó là lưới, và nó phải còn xanh sau change.
