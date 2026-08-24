# Tasks

## 0. Hai quy ước áp cho mọi nhóm bên dưới

**Đặt tên: định danh TIẾNG ANH, ghi chú tiếng Việt.** Quy ước chốt 14/08 của dự án. Áp cho
tên file, tên hàm, tên biến, tham số dòng lệnh, **và khoá trong JSON sinh ra**.

Bản đầu của task 1.2 vi phạm toàn diện — `tools/moc_nen.py`, hàm `chup()` `so_sanh()`
`in_ban_chup()`, hằng `PHEP_DO` `DEM_BANG`, cờ `--ghi` `--so-voi`, và khoá JSON `dong`
`dem_bang` `account_theo_kind`. Đã sửa hết thành `tools/baseline_db.py` · `capture()`
`compare()` `print_snapshot()` · `AGGREGATES` `ROW_COUNT_TABLES` · `--save` `--compare` ·
`rows` `row_counts` `account_by_kind`.

⚠️ Thư mục `tools/` hiện có **16 file khác vẫn mang tên tiếng Việt** (`dien_tap_gateway.py`,
`do_tien_suy_ra.py`, `soat_khoa_api.py`, …). Đổi tên chúng **không thuộc change này** — nếu
làm thì phải là một change riêng, vì `dien_tap_gateway.py` được nhắc tên trong nhật ký và
trong change đã lưu trữ `admit-gateway-as-a-fourth-source`.

**Commit: mỗi nhóm một commit, gộp lại thành MỘT ở cuối.** Quyết định 24/08 — chỉ đưa vào
lịch sử một change đã hoàn thiện, nhưng vẫn giữ điểm quay lui giữa chừng:

```
   trong luc lam    commit sau moi nhom     -> co diem quay lui tung buoc
   khi 44/44 xong   git reset --soft <goc>  -> gop thanh MOT commit duy nhat
                    git commit              -> lich su cuoi cung gon
```


## 1. Bảo toàn trước, đụng sau

Nhóm này không sửa gì cả. Nó tồn tại vì phần còn lại đụng vào chỗ chứa dữ liệu không dựng
lại được, và một bước sai ở đó không có đường lùi.

- [ ] 1.1 ⚪ **Chép `data/` (2,3 GB) sang ổ khác — nên làm, nhưng KHÔNG chặn change này.**

      Bản đầu của task này đánh 🔴 và nói phải làm trước mọi thứ. **Đo lại 24/08 thì đó là
      lo quá mức**: change này không bao giờ ghi vào `data/`.

      Kiểm cả 8 script trên đường nạp (`load_billing` · `load_hd` · `load_monitoring` ·
      `load_org` · `load_ralli` · `build_performance` · `build_usage_daily` ·
      `rebuild_db`) — tìm `open(...,'w')`, `write_text`, `shutil.move/copy/rmtree`,
      `os.remove/unlink`, `to_csv`, `json.dump`:

      ```
         ket qua:  8/8 script CHI DOC doi voi o dia
                   chung chi ghi vao DATABASE
      ```

      Thứ ghi vào `data/` là các script `pull_*` và `merge_*`, và change này **không gọi
      cái nào**. Dữ liệu gốc trong thư mục dự án là đủ để viết và chạy migration.

      Vẫn nên chép, nhưng vì lý do khác và không gấp: `data/` chỉ có **1 file trong git**
      trên tổng 2,3 GB, và `raw_google_console/` (1.023 MB) + `da_xu_ly/` (829 MB) **không
      kéo lại được** — cửa sổ lưu giữ của Google trượt 196 → 112 ngày trong một tuần. Đó
      là rủi ro **thường trực** của dự án (ổ hỏng, gõ nhầm `rm`), không phải rủi ro do
      change này tạo ra.
- [x] 1.2 ✅ **Làm thành công cụ, không phải file tĩnh** — `tools/baseline_db.py`.

      Task này ban đầu chỉ nói *"ghi vào một file tạm"*. Nhưng task 5.4 phải **so lại** đúng
      những con số này trên database mới, và so bằng mắt thì dễ bỏ sót một chữ số. Công cụ
      chụp được cả hai đầu rồi tự so từng khoá:

      ```
         python tools/baseline_db.py --save var/baseline-2026-08-24.json
         python tools/baseline_db.py --db <dsn v2> --compare var/baseline-2026-08-24.json
      ```

      Đã chụp: `var/baseline-2026-08-24.json`, **23 khoá**, khớp toàn bộ bất biến.

      **Đường so đã được kiểm bằng cả hai chiều** — một công cụ so không bao giờ báo lệch
      thì tệ hơn không có công cụ:

      | Phép | Kết quả |
      |---|---|
      | So với chính nó | 23/23 khớp · **exit 0** |
      | So với bản chụp gieo 4 loại lệch | **4/4 bắt được · exit 1** |

      Bốn loại gieo: lệch **đúng 1 token** · thiếu 1 dòng `fact_monitoring` · một
      `service_account` biến mất · mất hẳn một `source`. Cả bốn đều bị chỉ tên.

      Hai chi tiết cài đặt đáng ghi, đều là bẫy đã biết của dự án:
      - Đọc qua `usage_resolved`, **không** cộng thẳng `fact_usage_daily` — bảng đó để ba
        nguồn cạnh nhau (1.845 dòng cho 1.189 khoá), cộng thẳng là đếm ba lần
      - Tiền so bằng **chuỗi**, không phải `float`. `cost_usd` là `NUMERIC(14,6)`; đổi sang
        float để so là tự tạo sai số ở chữ số thứ 15

      Bộ số mốc:

      | | |
      |---|---|
      | `usage_resolved` | 1.189 dòng · 867.657.110 token · $291,985601 · 01/01→17/08 |
      | `usage_by_account` | 320 dòng · 107.926.810 token |
      | `account` | 953 = real 937 · service_account 6 · whole_agent 2 · unattributed 8 |
      | `fact_usage_daily` | 1.845 — billing 965 · monitoring 539 · app 341 |
      | `fact_monitoring` | 583.917 |
      | `fact_billing_daily` | 2.441 |
      | `fact_call` | 8.330 |
      | `fact_app_daily` | 77 |
      | `ref_source` | 4 |

- [x] 1.3 ✅ **Mốc bộ kiểm, đo 24/08/2026:**

      ```
         audit_db.py    36 phep | 31 dat | 5 luu y | 0 hong   exit 0
         check_api.py   19 phep | 19 dat | 0 hong             exit 0
      ```

      Cả hai khớp mốc ghi trong `nhat-ky-22-08-sang.md`. 5 "lưu ý" là dữ liệu thiếu đã
      biết, **không phải lỗi** — có sẵn từ trước, không được lẫn vào kết quả nhóm 5.

      `check_api.py` cần máy chủ sống **và** `DASHBOARD_KEY` khớp hai đầu. Không cần khoá
      thật: dựng uvicorn bằng một khoá dùng một lần rồi tắt, vì hai đầu chỉ cần giống nhau.

- [x] 1.4 ✅ `git status` sạch trước khi bắt đầu — `d716cc7` (sửa giấy tờ) và
      `5718389` (nhật ký). Ba commit của change này đã được gỡ theo yêu cầu 24/08:
      chỉ commit khi change hoàn thiện, xem ghi chú cuối file

## 2. Dựng Alembic, chưa đụng database nào

- [x] 2.1 ✅ `alembic 1.19.1` (kéo theo `SQLAlchemy 2.0.52`, `Mako`, `greenlet`,
      `MarkupSafe`). Đã thêm vào `backend/requirements.txt` kèm ghi chú vì sao chọn Alembic
      dù dự án **không dùng ORM**: nó là **tập cha** của `yoyo` — vẫn viết được SQL thuần,
      mà ngày nào service nạp Gateway muốn dùng model thì thêm được, không phải đổi công cụ
- [x] 2.2 ✅ `alembic init db/migrations` → `alembic.ini` (gốc repo) + `db/migrations/`
      (`env.py`, `script.py.mako`, `versions/`)
- [x] 2.3 ✅ `env.py` viết lại: DSN lấy từ `connect.DEFAULT_DSN`, thêm hai đường ghi đè cho
      nhóm 5, và **in DSN đã che** mỗi lần chạy vì `upgrade` là lệnh sửa schema — nhầm
      database là chuyện đắt giá.

      Thêm `_sqlalchemy_url()` vì quy ước DSN của dự án **không phải** URL SQLAlchemy:
      `connect.py` phân biệt hai hệ bằng **đuôi file**, nên đường dẫn SQLite trần phải được
      thêm tiền tố. Đã kiểm 4 trường hợp:

      | DSN dự án | → URL SQLAlchemy |
      |---|---|
      | `postgresql://…/token_ledger` | giữ nguyên |
      | `postgresql://…/token_ledger_v2` | giữ nguyên |
      | `var	oken_ledger.sqlite` | `sqlite:///var/token_ledger.sqlite` |
      | `var/doi_chieu.db` | `sqlite:///var/doi_chieu.db` |

      `target_metadata = None` là **cố ý**, có ghi chú tại chỗ: `--autogenerate` vô dụng ở
      đây vì Alembic **không quản view**, mà `usage_resolved` mới là *"cửa chính để hỏi số
      liệu"*. Autogenerate sẽ im lặng bỏ qua cả ba view rồi báo "không có gì thay đổi".
- [x] 2.4 ✅ Gỡ `sqlalchemy.url` khỏi `alembic.ini`, thay bằng ghi chú giải thích vì sao để
      trống — để người sau không "sửa lại cho đủ"
- [x] 2.5 ✅ **Ba phép kiểm, đều đạt:**

      ```
         alembic current                      -> postgresql://token:***@127.0.0.1:5432/token_ledger
         alembic -x db=<dsn khac> current     -> doi dung theo -x
         TOKEN_LEDGER_DSN=<dsn khac> alembic  -> doi dung theo bien moi truong
      ```

      Mật khẩu che ở cả ba. `token_ledger` **chưa có bảng `alembic_*` nào** — đúng, vì
      `current` chỉ đọc. Bộ số bất biến so lại sau nhóm 2: **23/23 khớp**.

## 3. Migration 001 — bản đóng băng của schema hôm nay

- [x] 3.1 ✅ Chép sang `db/migrations/sql/001_baseline.sql`. **Thân file trùng khít từng
      byte** với `db/01_schema.sql` — 749 dòng, `sha256` thân `750a12d30263c158` ở cả hai
- [x] 3.2 ✅ 18 dòng đầu là ghi chú đóng băng: *"KHÔNG BAO GIỜ ĐƯỢC SỬA FILE NÀY"*, kèm lý
      do (máy này áp bản cũ, máy đồng nghiệp áp bản mới, `alembic_version` ở cả hai đều nói
      "đã áp 001") và nhắc ràng buộc trung lập hai hệ
- [x] 3.3 ✅ `versions/001_baseline_baseline.py` chỉ đọc file `.sql` rồi chạy. SQL **không**
      nhét vào chuỗi Python: 749 dòng đó là trí nhớ thiết kế của dự án, nhét vào chuỗi là
      mất tô màu cú pháp và không `grep` ra được.

      ⚠️ **Ba đường gọi đều hỏng, và hỏng vì cùng một thứ** — 11 dấu `%` trong ghi chú
      tiếng Việt (`"12,4%"`, `"85,6%"`) cộng một `LIKE '%token_count'`:

      | Cách gọi | Kết quả |
      |---|---|
      | `op.execute(chuoi)` | qua SQLAlchemy `text()` — `:tên` thành tham số buộc, `%` qua paramstyle `pyformat` |
      | `op.get_bind().exec_driver_sql(chuoi)` | **`TypeError: immutabledict is not a sequence`** — đo thật, không phải suy |
      | `exec_driver_sql(chuoi, ())` | có tham số = **bật** nội suy `%` → 11 dấu kia vỡ |

      Đúng: lấy **kết nối DBAPI thật** rồi `cur.execute(sql)` **không đối số thứ hai** —
      psycopg2 chỉ bỏ qua `%` khi gọi không tham số. Đây chính là cách
      `db/connect.py:run_sql_file()` đã làm, và là lý do hàm đó tồn tại.
- [x] 3.4 ✅ `downgrade()` ném `NotImplementedError` kèm lý do và chỉ đường thay thế. Kiểm
      thật: `alembic downgrade base` → **exit 1**, in đúng thông điệp
- [x] 3.5 ✅ **RÚT — ràng buộc này không còn đối tượng.**

      Task gốc đòi `001_baseline.sql` *"giữ trung lập hai hệ"*. Ngày 24/08 phát hiện
      `db/01_schema.sql` **đã không dựng được trên SQLite từ 21/08** — `INSERT INTO
      ref_source` nối hai chuỗi liền kề, PostgreSQL nhận, SQLite báo lỗi cú pháp. Kiểm
      bằng đường **cũ** (`sqlite3.executescript`, không qua Alembic): hỏng y hệt, tức lỗi
      có sẵn chứ không do change này.

      Điều đó dẫn tới change `drop-the-sqlite-escape-hatch`, và sau nó ràng buộc trung lập
      **biến mất cùng với đối tượng nó phục vụ**. Migration về sau được phép dùng `JSONB`,
      `GENERATED`, partial index.

      *(Bản đầu của task này đánh ✅ với lý do sai: phép quét `SERIAL|JSONB|GENERATED` tìm
      **kiểu dữ liệu** riêng của một hệ, trong khi lỗi nằm ở **cú pháp**. Ghi lại vì cùng
      loại nhầm sẽ quay lại: một phép kiểm quá hẹp không phải là một phép kiểm đạt.)*

### ✅ Nghiệm thu nhóm 3 — schema dựng bằng migration giống hệt schema đang chạy

Dựng database rác `scratch_001`, chạy `alembic upgrade head`, so `information_schema` với
`token_ledger` (đã bỏ `alembic_version` là bảng của chính Alembic):

| | `token_ledger` | `scratch_001` | |
|---|---:|---:|---|
| bảng | 19 | 19 | **khớp** |
| view | 3 | 3 | **khớp** |
| cột | 199 | 199 | **khớp** |
| ràng buộc khoá | 66 | 66 | **khớp** |

`alembic current` trên bản rác: `001_baseline (head)`. Database rác đã xoá; `token_ledger`
so lại **23/23 khớp**, không đụng một token.

## 4. Đổi nguồn schema trong `connect.rebuild()` — giữ nguyên bước xoá sạch

- [ ] 4.1 ⚠️ **`DROP SCHEMA` KHÔNG biến mất — nó ở lại đúng chỗ của nó.**

      Bẫy dễ mắc: change này tên là *"đổi schema không phải xoá database"*, nên phản xạ đầu
      tiên là gỡ bỏ `DROP SCHEMA`. **Làm thế sẽ vỡ `rebuild_db.py`**: bước 1 gọi
      `load_billing.py --rebuild`, và `--rebuild` có nghĩa *"xoá sạch, dựng schema + danh
      mục, nạp hoá đơn"*. Không xoá sạch thì nạp lại danh mục vào bảng đã có dòng → đụng
      khoá chính ngay.

      Việc đúng là **tách hai thao tác đang bị gộp làm một**:

      ```
         connect.rebuild()          "xoa sach roi dung lai tu data/"
         ├── open_db()                          GIU
         ├── DROP SCHEMA / unlink()             GIU  ← van can, cho duong nap lai
         ├── run_sql_file(01_schema.sql)   ➡️  alembic upgrade head
         └── run_sql_file(02_catalog.sql)       GIU nguyen mot chu

         alembic upgrade head       "doi schema TAI CHO"   ← NANG LUC MOI
         (khong xoa gi, chay doc lap, khong qua connect.rebuild)
      ```

      Thứ biến mất là **`01_schema.sql` với tư cách nguồn schema**, không phải bước xoá.
      Hai đường dùng chung một chuỗi migration, khác nhau ở chỗ có xoá trước hay không.

- [x] 4.2 ✅ **ĐÃ CHỨNG MINH 24/08/2026** — không còn là suy luận.

      Dựng database rác `kiem_thu_alembic`, tạo `alembic_version` (có dòng `'001_baseline'`) và
      một bảng dữ liệu, chạy `DROP SCHEMA public CASCADE; CREATE SCHEMA public;`, rồi đọc
      lại `information_schema.tables`:

      | | trước | sau |
      |---|---|---|
      | bảng trong `public` | `alembic_version`, `du_lieu_gia` | **(rỗng)** |
      | `alembic_version` ghi gì | `'001_baseline'` | **bảng không tồn tại** |

      Kết luận: `alembic_version` **bị xoá**, vì nó là một bảng bình thường nằm trong
      `public` như mọi bảng khác. Nhờ vậy `alembic upgrade head` ngay sau đó thấy database
      trắng và chạy lại toàn bộ chuỗi từ `001` — đúng hành vi cần cho đường nạp lại.

      Database rác đã xoá; `token_ledger` không bị đụng (kiểm lại: 1.189 dòng ·
      867.657.110 token).
- [ ] 4.3 Nửa danh mục là **dữ liệu gieo**, sinh bởi `gen_catalog.py`, Alembic không thay.
      Giữ cả nhánh `raise SystemExit` khi thiếu file — nó đang chỉ đúng cách sửa
- [ ] 4.4 Giữ nguyên chữ ký hàm và giá trị trả về `(cn, placeholder)` — `load_billing.py`
      gọi nó và không được biết bên trong đã đổi
- [ ] 4.5 Đọc lại toàn bộ hàm sau khi sửa. Bước này bắt buộc: `rebuild()` là chỗ duy nhất
      biết cách dựng database, sửa sai là mọi thứ sau đó sai theo

## 5. Dựng `token_ledger_v2` song song — database cũ KHÔNG bị đụng

- [x] 5.1 ✅ `CREATE DATABASE token_ledger_v2`
- [x] 5.2 ✅ `alembic upgrade head` → schema rỗng. So `information_schema` với database
      đang chạy (bỏ `alembic_version` là bảng của chính Alembic):

      | | `token_ledger` | `v2` | |
      |---|---:|---:|---|
      | bảng | 19 | 19 | **khớp** |
      | view | 3 | 3 | **khớp** |
      | cột | 199 | 199 | **khớp** |
      | ràng buộc khoá | 66 | 66 | **khớp** |

- [x] 5.3 ✅ `TOKEN_LEDGER_DSN=…v2 python scripts/rebuild_db.py` — **cả 7 bước đạt nghiệm
      thu, 74 giây.** `fact_monitoring` 583.917 dòng · `fact_perf_daily` 600 · tiền billing
      `$291,985601`
- [x] 5.4 ✅ **PHÉP NGHIỆM THU QUYẾT ĐỊNH — 23/23 khớp, `exit 0`.**

      Database dựng **hoàn toàn từ chuỗi migration** rồi nạp lại từ `data/` cho ra số y hệt
      bản đang chạy — kể cả `$291,985601` tới sáu chữ số thập phân và `867.657.110` token
      không lệch một đơn vị.

      Đây là thứ chứng minh đường migration **đúng**, không chỉ **chạy được**.
- [x] 5.5 ✅ `audit_db.py` trên v2: **36 phép · 31 đạt · 5 lưu ý · 0 hỏng** — trùng khít mốc
      task 1.3. Không phép nào hỏng thêm, cũng không phép nào bỗng đạt
- [x] 5.6 ✅ `check_api.py` trỏ backend vào v2: **19 · 19 đạt · 0 hỏng**

### ✅ Nghiệm thu nhóm 5 — và `token_ledger` gốc KHÔNG bị đụng

Kiểm sau khi xong cả nhóm:

```
   token_ledger  ->  23/23 khop, khong lech mot token
                 ->  KHONG co bang alembic_* nao
                     (dung: no chua qua migration lan nao)
```

Suốt nhóm 5, đường lui vẫn là **đổi một biến** `DEFAULT_DSN`. Database cũ chưa bị sửa một
chữ.

## 6. Đổi sang v2, rồi trả tên về

Chỉ làm nhóm này khi nhóm 5 khớp **hết**.

- [ ] 6.1 Đổi `connect.DEFAULT_DSN` sang `token_ledger_v2`
- [ ] 6.2 Chạy dashboard thật, xem bằng mắt: tổng token, tổng tiền, ma trận, cây phòng ban
- [ ] 6.3 **Chờ vài ngày.** Một database rỗng không tốn gì ngoài dung lượng đĩa, và đây là
      chỗ rẻ nhất để mua sự an tâm
- [ ] 6.4 `DROP DATABASE token_ledger`
- [ ] 6.5 ⚠️ Đóng backend, pgAdmin và mọi script, rồi `ALTER DATABASE token_ledger_v2
      RENAME TO token_ledger`. Còn kết nối thì lệnh **treo** chứ không báo lỗi rõ
- [ ] 6.6 Trả `connect.DEFAULT_DSN` về `token_ledger`. Sau bước này không còn chữ `_v2` ở
      đâu — kiểm bằng `grep -rn "_v2"` trên toàn repo
- [ ] 6.7 Chạy lại `audit_db.py` + `check_api.py` lần cuối

## 7. Dọn và ghi lại

- [ ] 7.1 Xoá `db/01_schema.sql` — nội dung đã nằm trong `001_baseline.sql`. Còn hai file là còn
      trôi khỏi nhau
- [ ] 7.2 Xoá `scripts/copy_to_postgres.py` — đã chết sẵn: đòi một file SQLite làm nguồn mà
      `var/token_ledger.sqlite` bị xoá từ 17/08, `var/` hiện rỗng
- [ ] 7.3 `grep -rn "01_schema\|copy_to_postgres"` toàn repo, sửa mọi chỗ còn trỏ tới. Biết
      trước có `db/connect.py`, `scripts/rebuild_db.py`, và vài file `.md` trong `docs/`
- [ ] 7.4 Cập nhật `docs/reference/dong-bo-may-dong-nghiep-*.md`: lệnh dựng nay có thêm
      bước `alembic upgrade head`
- [ ] 7.5 Cập nhật `docs/reference/cay-thu-muc.md` cho khớp cây thư mục mới
- [ ] 7.6 Ghi vào `db/migrations/README.md`: cách thêm migration mới, luật *"đã chạy thì
      không sửa"*, và vì sao `02_catalog.sql` không nằm trong migration

## 8. Nghiệm thu

- [ ] 8.1 Trên một database trắng: `alembic upgrade head` + `rebuild_db.py` ra đúng 9 con số
- [ ] 8.2 `audit_db.py` không có phép hỏng mới so với mốc 1.3
- [ ] 8.3 `check_api.py` không có phép hỏng mới so với mốc 1.3
- [ ] 8.4 `node --test tests/*.test.js` vẫn xanh
- [ ] 8.5 `python tools/chay_dashboard_trong_node.js` exit 0
- [ ] 8.6 Chứng minh năng lực mới thật sự có — **diễn tập trên database THẬT đang có dữ
      liệu**, vì đó mới là điều hôm nay không làm được:

      1. Viết migration `002_dien_tap.sql`: thêm một cột nullable vô hại
      2. `alembic upgrade head` lên database thật
      3. **So lại 9 con số của task 1.2** — phải không suy suyển một token
      4. Viết migration `003_go_dien_tap.sql` gỡ cột đó ra
      5. `alembic upgrade head` lần nữa, so số lần nữa

      ⚠️ **Không dùng `alembic downgrade`** — task 3.4 đã chốt forward-only, `downgrade()`
      ném `NotImplementedError`. Gỡ ra bằng một migration TIẾN, không phải migration LÙI.

      Giá phải trả: lịch sử migration có thêm hai bản ghi không mang giá trị nghiệp vụ. Đó
      là giá đúng — lịch sử migration vốn chỉ được thêm, không được sửa, và hai dòng đó là
      bằng chứng ngày năng lực này được chứng minh.

      Nếu bước này không chạy được thì change **chưa đạt mục đích**, dù mọi task trên đều
      xanh.
