## Context

Dự án chạy trên SQLite (`var/token_ledger.sqlite`) làm database mặc định. PostgreSQL đã có
sẵn trong `docker-compose.yml` từ đợt trước và hiện đang chạy, nhưng chỉ dùng làm bản đối
chiếu — nó được tạo bằng `scripts/copy_to_postgres.py`, chép 1:1 từ file SQLite.

Hiện trạng đã đo (không suy đoán):

```
  data/ (thô)  ──rebuild_db.py──▶  var/*.sqlite  ──copy_to_postgres──▶  Postgres
                  ĐÃ CHẠY NHIỀU LẦN                  ĐÃ CHẠY            đang chạy

  data/ (thô)  ──rebuild_db.py --db <postgres dsn>──▶  Postgres
                  ✗ CHƯA BAO GIỜ CHẠY
```

`01_schema.sql` được viết để chạy trên cả hai hệ (không dùng `SERIAL`, mọi khoá gán tường
minh), nên về lý thuyết đường thứ hai chạy được. Chưa ai thử.

Ràng buộc:

- Database chứa 937 nhân viên kèm email. Nó không được ra mạng. `docker-compose.yml` đã
  gắn cả hai cổng vào `127.0.0.1`, không phải `0.0.0.0` — giữ nguyên.
- `backend/store.py` mở kết nối **chỉ-đọc** ở mức máy chủ (`set_session(readonly=True)`),
  không phải lời hứa trong tài liệu. Giữ nguyên.
- `data/` là thứ duy nhất mất là mất vĩnh viễn: cửa sổ lưu giữ của Cloud Monitoring trượt
  91 ngày chỉ trong 7 ngày. Mọi thứ khác dựng lại được từ nó.

## Goals / Non-Goals

**Goals:**

- PostgreSQL là database mặc định, không cần đặt biến môi trường nào sau
  `docker compose up -d`.
- Đúng **một** nguồn sự thật về DSN mặc định trong toàn bộ mã nguồn.
- Chứng minh đường ống dựng thẳng vào PostgreSQL từ `data/` chạy được, và cho ra đúng số
  liệu đã đối chiếu.
- Mật khẩu không lọt ra terminal hay log.
- Xoá `var/token_ledger.sqlite` **sau khi** đã chứng minh, không phải trước.

**Non-Goals:**

- Không chia schema hay `GRANT` theo service. Thay đổi này chỉ *dỡ chặn đường* cho việc đó;
  bản thân việc chia là chuyện của giai đoạn API Gateway.
- Không sửa một dòng SQL nào. Nếu phải sửa SQL thì tức là `01_schema.sql` chưa thật sự
  chạy được hai hệ, và đó là phát hiện cần báo chứ không phải việc cần vá trong change này.
- Không bỏ khả năng mở SQLite. Nó vẫn là đường đối chiếu độc lập rẻ nhất.
- Không đụng vào frontend. Đó là change `serve-dashboard-from-database-only`.
- Không đổi cách `backend/store.py` chọn nguồn hay tính số.

## Decisions

### 1. `DEFAULT_DSN` dựng từ biến môi trường, không phải chuỗi gán cứng

```python
PG_HOST     = os.environ.get("PGHOST",     "127.0.0.1")
PG_PORT     = os.environ.get("PGPORT",     "5432")
PG_USER     = os.environ.get("PGUSER",     "token")
PG_PASSWORD = os.environ.get("PGPASSWORD", "token_local")
PG_DATABASE = os.environ.get("PGDATABASE", "token_ledger")

DEFAULT_DSN = os.environ.get("TOKEN_LEDGER_DSN") or (
    f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DATABASE}")
```

**Vì sao dùng đúng tên biến của `docker-compose.yml`:** compose đã đọc
`PGDATABASE`/`PGUSER`/`PGPASSWORD`/`PGPORT` từ `.env` để cấu hình container. Dùng lại đúng
tên đó nghĩa là **một** chỗ đặt cấu hình cho cả container lẫn script. Đặt tên khác sẽ tạo
ra hai bộ cấu hình phải giữ khớp bằng tay — đúng loại lỗi im lặng mà change này đang đi
dọn.

**Vì sao `TOKEN_LEDGER_DSN` được ưu tiên cao nhất:** biến này đã tồn tại và đã được ghi
trong `backend/main.py:8-9`, nhưng hiện chỉ `backend/store.py` đọc nó. Các script nạp dùng
`--db default=connect.DEFAULT_DSN` nên bỏ qua nó. Cho `DEFAULT_DSN` tôn trọng biến này làm
nó có hiệu lực toàn hệ thống — một biến đổi được database cho mọi thành phần, và đó cũng là
đường quay về SQLite.

*Đã cân nhắc:* để `DEFAULT_DSN` là hằng số Postgres thuần và bắt mỗi script tự đọc
`TOKEN_LEDGER_DSN`. Bị loại vì đó chính là hình dạng lỗi đang có: nhiều chỗ tự quyết định,
và một chỗ quên là không ai biết.

*Đã cân nhắc:* đọc DSN từ `.env` bằng một thư viện như `python-dotenv`. Bị loại vì thêm phụ
thuộc để giải quyết việc mà biến môi trường đã giải quyết, và vì compose đã đọc `.env` rồi.

### 2. `mask_dsn()` đặt trong `db/connect.py`, không nhân bản

Hàm che mật khẩu hiện là `che()` trong `scripts/rebuild_db.py` — chỉ script đó dùng được.
`db/load_billing.py:67` in `args.db` thô.

Chuyển hàm vào `db/connect.py` cạnh `DEFAULT_DSN`: nơi nào biết DSN thì nơi đó biết cách in
DSN an toàn. Tên tiếng Anh (`mask_dsn`) theo quy ước của `db/` — `connect.py` hiện dùng
`is_sqlite`, `open_db`, `run_sql_file`, `rebuild`. `scripts/rebuild_db.py` bỏ hàm `che()`
cục bộ và gọi `connect.mask_dsn()`.

*Đã cân nhắc:* để `che()` ở `rebuild_db.py` và `load_billing.py` tự cắt chuỗi. Bị loại —
hai bản cài đặt của cùng một quy tắc bảo mật là một bản sẽ sai.

### 3. `rebuild_db.py` dùng `connect.DEFAULT_DSN`

Đổi `default=str(ROOT / "var" / "token_ledger.sqlite")` thành
`default=connect.DEFAULT_DSN`, và import `connect` theo đúng khuôn của
`scripts/audit_db.py`:

```python
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "db"))
import connect  # noqa: E402
```

Đây là chỗ quan trọng nhất về mặt hậu quả: `scripts/update_dashboard.py:145` gọi
`rebuild_db.py` **không truyền `--db`**. Không sửa chỗ này thì đổi `connect.py` xong đường
ống vẫn dựng lại SQLite, và mọi thứ trông như đang chạy đúng.

### 4. Xoá SQLite là bước CUỐI, sau khi đã chứng minh

Thứ tự bắt buộc:

```
  1. sửa mã (3 file)
  2. rebuild_db.py --db <postgres> trên database rỗng   ← đường chưa test
  3. audit_db.py trên Postgres                          ← 30 phép kiểm
  4. đối chiếu 8 con số mốc                             ← nghiệm thu bằng SỐ
  5. chạy backend + mở dashboard                        ← nghiệm thu bằng MẮT
  6. XOÁ var/token_ledger.sqlite                        ← không hoàn nguyên
```

Bước 6 không hoàn nguyên theo nghĩa thao tác, dù dữ liệu dựng lại được từ `data/`. Trước
bước 2 thì file SQLite là database duy nhất đã được chứng minh đúng; nó chính là thứ dùng
để kiểm bước 4. Xoá sớm là bỏ mốc đối chiếu trong lúc còn cần nó.

Bước 2 chạy trên **database rỗng** để chứng minh đúng thứ cần chứng minh. Chạy trên
database đang có dữ liệu thì `load_billing --rebuild` sẽ xoá sạch rồi nạp lại — cùng kết
quả, nhưng không phân biệt được "dựng được từ đầu" với "ghi đè lên cái đã đúng".

### 5. Hai chênh lệch kiểu dữ liệu: ghi lại, không sửa

Đã đo trên cả hai hệ:

| Cột | Postgres | SQLite | JSON frontend nhận | Xử lý |
|---|---|---|---|---|
| `total/input/output/cached_tokens` | `Decimal` | `int` | **số, giống nhau** | không sửa |
| `units.is_technical` | `True` | `1` | `true` vs `1` | không sửa, ghi lại |

`Decimal` là chỗ đáng lo nhất và đã kiểm tận nơi: `jsonable_encoder` của FastAPI đổi
`Decimal` có phần thập phân bằng 0 thành `int`. Nếu nó ra chuỗi thì `ti + to + cached` ở
`web/js/app.js` thành nối chuỗi — số sai mà không lỗi nào ném ra. Không phải rủi ro ở đây,
nhưng là lý do phép kiểm về kiểu JSON nằm trong spec.

`is_technical` không thành phần nào trong `web/` đọc, nên vô hại hôm nay. Không thêm phép
chuẩn hoá kiểu: thêm một lớp chuyển đổi cho một cột không ai đọc là thêm chỗ để sai.

## Risks / Trade-offs

**`docker compose down -v` xoá sạch volume `pgdata`.** Trước change này còn file SQLite làm
lớp đệm; sau thì không → Dựng lại được từ `data/` bằng `rebuild_db.py` (~15 phút), và chính
change này chứng minh đường đó chạy được. Ghi cảnh báo vào `README.md`. `docker-compose.yml`
đã có ghi chú `down -v` = "dung va XOA sach du lieu".

**`01_schema.sql` có thể không thật sự chạy được trên Postgres.** Chưa ai thử dựng từ đầu →
Bước 2 của kế hoạch chính là phép thử đó. Nếu hỏng, `rebuild_db.py` dừng ngay ở bước hỏng
và in `--from-step N` để chạy tiếp sau khi sửa. File SQLite vẫn còn nguyên lúc này, nên
dashboard vẫn dùng được trong khi sửa.

**`psycopg2-binary` từ tuỳ chọn thành bắt buộc.** Ai clone repo mà chưa cài sẽ không chạy
được gì → Đã có trong `backend/requirements.txt`; sửa ghi chú đang nói *"chi can khi doc
PostgreSQL. Chay tren SQLite thi bo qua duoc"*. `connect.py:37-44` đã có thông báo lỗi tử
tế kèm hướng dẫn cài và gợi ý dùng SQLite.

**Cần Docker chạy mới làm được gì.** Trước đây `git clone` + `python` là chạy được đường ống
trên SQLite → Đánh đổi có chủ đích: `data/` không lên git nên một bản clone thuần vốn đã
không có số liệu để nạp. Đường ghi đè về SQLite vẫn còn cho ai cần.

**Mật khẩu mặc định `token_local` nằm trong mã nguồn.** → Đã nằm trong
`docker-compose.yml` với lý do ghi rõ: chấp nhận được vì chỉ mở trên `127.0.0.1`, không ra
mạng. Đổi được bằng `.env` mà không sửa mã. Không đưa mật khẩu thật vào đây.

## Migration Plan

**Triển khai:** theo đúng 6 bước ở Decision 4. Bước 1-5 hoàn nguyên được (`git checkout`);
bước 6 thì không.

**Quay lui:** `git checkout` ba file đã sửa. Nếu đã xoá SQLite và cần nó lại:
`python scripts/rebuild_db.py --db var/token_ledger.sqlite` dựng lại từ `data/`.

**Nghiệm thu:** 8 con số mốc trong `specs/postgres-rebuild-equivalence/spec.md`, đọc qua
view `usage_resolved` — KHÔNG `SUM` thẳng trên `fact_usage_daily` (khoá chính gồm cả
`source`, cộng thẳng ra 897.452.165 thay vì 539.827.701).

## Open Questions

- `scripts/copy_to_postgres.py` còn giữ hay xoá? Sau change này nó không còn nằm trên đường
  chính. Nó vẫn hữu ích để chép nhanh giữa hai database mà không nạp lại từ `data/`.
  Nghiêng về **giữ** và ghi rõ trong docstring rằng đây là công cụ phụ. Docstring của nó
  cũng đang ghi sai tên file (`tai_tao_postgres.py`) — sửa luôn.
- `VAR_DIR` trong `connect.py` sau change này chỉ còn được tài liệu tham chiếu. Giữ làm hằng
  số mô tả layout, hay xoá? Nghiêng về **giữ**, vì `var/` vẫn là nơi duy nhất được phép
  chứa SQLite đối chiếu.
