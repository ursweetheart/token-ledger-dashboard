# Đổi được schema mà không phải xoá cả database

## Why

Hôm nay dự án **không có** migration. Nó có *"đập đi xây lại"*, và đó là **cách duy nhất**
để đổi schema.

`db/connect.py:132-154` — hàm `rebuild()`, được gọi từ bước 1 của `scripts/rebuild_db.py`:

```python
cur.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
run_sql_file(cn, placeholder, DB_DIR / "01_schema.sql")
run_sql_file(cn, placeholder, DB_DIR / "02_catalog.sql")
```

Thêm một cột nghĩa là xoá sạch rồi nạp lại 7 bước. **Và hôm nay điều đó hoàn toàn ổn**,
vì mọi dòng trong database đều dựng lại được từ `data/`. Database hiện là một **sản phẩm
phái sinh**, không phải bản gốc.

### Điều đó chấm dứt vào ngày Gateway ghi dòng đầu tiên

```
   HOM NAY
   data/  ──(pull_*, load_*)──▶  database        DROP SCHEMA = mat 0 phut cong
     ▲                                            (chay lai rebuild la co lai)
     └── ban goc that su o day

   SAU GATEWAY
   data/  ──────────────────▶  database
                                  ▲
   LiteLLM ─── ghi THANG ────────┘
                                  │
                          dong gateway KHONG co ban sao o data/
                          DROP SCHEMA = MAT VINH VIEN
```

Master Plan giai đoạn 4 (*"Ghi đủ trường cần cho dashboard ngay tại thời điểm gọi"*) và
quyết định A1-2 ngày 20/08 (*"**CÓ** ghi `fact_attempt`"*) đều dẫn tới cùng một chỗ:
database sẽ thành **bản gốc**. Từ lúc đó, cách duy nhất còn lại là migration tại chỗ.

### Và có một đồng hồ thứ hai đang chạy

Đo 24/08/2026:

| | |
|---|---|
| `data/` trên đĩa | **2,3 GB** |
| `data/` trong git | **1 file** — `raw_google_console/danh_muc/sku-gemini-api.json` |

`.gitignore` dòng 7 là `data/*`, có chủ đích (*"schema và danh mục là MÃ, số liệu là DỮ
LIỆU"*). Nhưng hệ quả là **2,3 GB dữ liệu gốc không có bản sao ở đâu khác**, và một phần
không kéo lại được:

| Nhánh | Dung lượng | Kéo lại từ nguồn? |
|---|---:|---|
| `raw_google_console/` | 1.023 MB | ⚠️ **Không** — cửa sổ lưu giữ Google trượt **196 → 112 ngày** trong một tuần |
| `da_xu_ly/` | 829 MB | Gộp từ trên → cùng số phận |
| `raw_web/` | 440 MB | Được (app của mình) |
| còn lại | ~6 MB | Được |

`fact_monitoring` **583.917 dòng** đến từ đó.

> **Đây là lần cuối cùng việc chuyển sang migration còn rẻ.** Làm bây giờ thì được dựng lại
> từ đầu và **chứng minh** đường migration đúng. Làm sau Gateway thì phải migrate tại chỗ
> trên dữ liệu không dựng lại được.

### Bộ số nghiệm thu đã có sẵn, và nó chính xác

Đây là thứ khiến change này khác một cuộc dọn dẹp: nó **chứng minh được**. Đo trên
PostgreSQL đang chạy, 24/08/2026:

| | |
|---|---|
| `usage_resolved` | **1.189 dòng · 867.657.110 token · $291,985601** · 2026-01-01 → 2026-08-17 |
| `usage_by_account` | **320 dòng · 107.926.810 token** |
| `account` | **953** = `real` 937 · `service_account` 6 · `whole_agent` 2 · `unattributed` 8 |
| `fact_usage_daily` | 1.845 — `billing` 965 · `monitoring` 539 · `app` 341 |
| `fact_monitoring` | 583.917 |
| `fact_billing_daily` | 2.441 |
| `fact_call` | 8.330 |
| `fact_app_daily` | 77 |
| `ref_source` | 4 |

Nạp lại xong mà **khớp từng con số** thì đường migration đúng. Lệch một con số thì dừng —
và database cũ vẫn còn nguyên.

## What Changes

- **Alembic sở hữu schema.** `alembic upgrade head` thay cho `DROP SCHEMA` + `01_schema.sql`
- **Migration `001` là bản ĐÓNG BĂNG** của `db/01_schema.sql` hôm nay, kèm nguyên vẹn mọi
  ghi chú tiếng Việt. SQL nằm ở file `.sql` cạnh migration, không nhét vào chuỗi Python
- **Tách hai thao tác đang bị gộp làm một.** `DROP SCHEMA` **không** biến mất — nó ở lại
  đường *"xoá sạch rồi nạp lại từ `data/`"*, vì `rebuild_db.py` bước 1 gọi
  `load_billing.py --rebuild` và đường đó thật sự cần một schema trắng. Thứ biến mất là
  `01_schema.sql` **với tư cách nguồn schema**:

  ```
     connect.rebuild()        "xoa sach roi dung lai tu data/"     (da co)
     ├── DROP SCHEMA                       GIU
     ├── run_sql_file(01_schema.sql)  ➡️  alembic upgrade head
     └── run_sql_file(02_catalog.sql)      GIU nguyen mot chu

     alembic upgrade head     "doi schema TAI CHO, khong xoa gi"   ← NANG LUC MOI
  ```

  Hai đường dùng chung một chuỗi migration, khác nhau ở chỗ có xoá trước hay không. Danh
  mục `02_catalog.sql` giữ nguyên vì nó là dữ liệu gieo, không phải schema, và còn được
  sinh tự động bởi `db/gen_catalog.py`
- **Dựng `token_ledger_v2` song song**, nạp lại, so bộ số ở trên. Chỉ khi khớp mới đổi
  `DEFAULT_DSN`
- **Giữ song song hai database** theo quyết định 27/08/2026: `token_ledger` là bản legacy
  để đối chiếu/rollback; `token_ledger_v2` là runtime ledger hiện tại và là đích duy nhất
  cho ingestion Gateway về sau. Không `DROP` database cũ, không rename v2. Database vận
  hành riêng của LiteLLM vẫn là `litellm`, không phải một trong hai ledger
- **Xoá `db/01_schema.sql`** — nội dung đã nằm trong `001`. Còn hai file là còn trôi khỏi
  nhau; xoá đi thì bài toán đó **không tồn tại**, không cần phép kiểm chống trôi nào
- **Xoá `scripts/copy_to_postgres.py`** — đã chết sẵn. Docstring của chính nó ghi *"CONG CU
  PHU… GIO DA HET DUNG"*, và nó đòi một file SQLite làm nguồn, mà `var/token_ledger.sqlite`
  đã bị xoá từ 17/08 (`var/` hiện rỗng)
- **Forward-only, không viết migration lùi.** `downgrade()` ném `NotImplementedError` kèm
  lý do. Migration lùi thường được viết mà không bao giờ chạy, nên đến lúc cần thì nó sai;
  với đội 3 người thì *bản lưu trước khi chạy* rẻ hơn và thật hơn. Gỡ một thay đổi = viết
  một migration **tiến** khác

**KHÔNG làm trong change này**

- **Không dựng `fact_request` / `fact_attempt`.** Chúng là migration `002`, và phải viết
  **sau** khi chạy thử LiteLLM thật — hôm nay chưa ai nhìn thấy `LiteLLM_SpendLogs` có
  những cột gì. Thiết kế bảng trước khi nhìn là đúng cái bẫy *"tưởng / đo ra"* đã cắn 4 lần
  ở change `admit-gateway-as-a-fourth-source` và 5 lần ở `require-a-key-to-read-the-api`
- **Không gỡ bỏ đường SQLite.** `var/token_ledger.sqlite` đã xoá nhưng code vẫn đỡ được
  (`connect.is_sqlite()`, `open_db()`, `store.py:44`). Migration `001` vì thế **giữ trung
  lập** như `01_schema.sql` hôm nay — không `SERIAL`, khoá gán tường minh. Bỏ hẳn SQLite là
  một change riêng
- **Không đụng `02_catalog.sql`, `gen_catalog.py`, `load_*.py`, `build_*.py`.** Toàn bộ
  đường nạp dữ liệu giữ nguyên
- **Không đụng `web/`.** Frontend đọc qua API, không biết schema dựng bằng gì

## Impact

| | |
|---|---|
| **Specs** | `schema-migrations` (mới) |
| **Code** | `db/connect.py` · `db/migrations/` (mới) · `alembic.ini` (mới) · `backend/requirements.txt` |
| **Xoá** | `db/01_schema.sql` · `scripts/copy_to_postgres.py` |
| **Rebuild** | **Có — và đó chính là phép nghiệm thu.** Nạp lại toàn bộ vào `token_ledger_v2` |
| **Đồng nghiệp** | Phải bổ sung `dong-bo-may-dong-nghiep-*.md`: lệnh dựng đổi từ `rebuild_db.py` thuần sang có bước `alembic upgrade head` |
| **Không đụng** | `web/` · `backend/store.py` · `backend/main.py` · toàn bộ `db/load_*.py` |
| **Rủi ro** | **Trung bình — và thấp hơn bản đầu đánh giá.** Đo 24/08 cho thấy đường nạp **chỉ đọc** `data/`, nên dữ liệu gốc không nằm trong tầm với của change. Lưới: (1) dựng v2 **song song**, database cũ không bị đụng một chữ, (2) so 9 con số trước khi đổi DSN, (3) giữ database cũ lâu dài để đối chiếu/rollback |
| **Quay lui** | Quay lui runtime = đổi `DEFAULT_DSN` về `token_ledger`. Database cũ được giữ nguyên; không có bước phá huỷ hoặc rename trong kế hoạch hiện hành |

### Bốn cái bẫy đã biết trước

1. **`data/` là điểm hỏng duy nhất — nhưng change này không đụng vào nó.** Đo 24/08: cả 8
   script trên đường nạp (`load_*`, `build_*`, `rebuild_db`) đều **chỉ đọc** đối với ổ đĩa;
   chúng chỉ ghi vào database. Thứ ghi vào `data/` là `pull_*` và `merge_*`, và change này
   không gọi cái nào. Nên chép `data/` ra ổ ngoài vẫn đáng làm (1 file trong git trên tổng
   2,3 GB; 1 GB không kéo lại được), nhưng đó là rủi ro **thường trực** của dự án, không
   phải rủi ro do change này tạo ra — task **1.1** vì thế là ⚪ chứ không phải 🔴.
2. **Migration đã chạy thì KHÔNG BAO GIỜ được sửa.** `001` phải là bản **chép đóng băng**
   của `01_schema.sql`, không phải con trỏ tới file đang sống. Nếu `001` đọc file `.sql`
   ngoài, file đó phải nằm trong `db/migrations/` và không ai được sửa nữa.
3. **Alembic mặc định tự đọc biến môi trường riêng của nó.** `connect.py` tự nhận là *"chỗ
   DUY NHẤT quyết định database mặc định"*, và nó ghi lại một sự cố đúng hình dạng đó:
   `rebuild_db.py` từng khai DSN riêng, đổi `connect.py` xong mà đường ống vẫn dựng
   database cũ, **không lỗi nào báo ra**. `env.py` của Alembic phải lấy DSN **từ
   `connect.DEFAULT_DSN`**, không tự đọc.
4. **Hai ledger không được cùng nhận một dòng Gateway.** `token_ledger` là legacy đóng băng;
   ingestion mới chỉ ghi vào `token_ledger_v2`. Ghi vào cả hai rồi cộng/đối chiếu không có
   provenance rõ ràng sẽ tạo hai bản gốc và mở đường double-count.
