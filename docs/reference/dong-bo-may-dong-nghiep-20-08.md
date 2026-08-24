# Những thay đổi cần đồng bộ trên máy đồng nghiệp — ngày 20/08/2026

**Ai cần đọc:** bất kỳ ai lần cuối `git pull` **trước ngày 17/08/2026**.

`origin/main` trước sáng 18/08 nằm ở `4d7060e` (16/08). Từ đó tới nay có **14 commit** —
2 commit tài liệu ngày 16/08 (`ed55d06`, `4e1ef52`, không cần làm gì) và 12 commit thay đổi
mã nguồn.

Trong đó có một thay đổi **không tự chạy được** sau khi pull: database mặc định chuyển từ
SQLite sang PostgreSQL. Pull code về mà không làm gì thêm thì dashboard sẽ **báo lỗi
không nối được database** — không phải hiện số sai, mà là hiện thông báo lỗi.

---

## Làm gì — 5 bước chung, với đúng một đường database

```bash
# 1. Lấy code
git pull

# 2. psycopg2 giờ BẮT BUỘC, không còn là tuỳ chọn
pip install -r backend/requirements.txt

# 3. Dựng PostgreSQL cục bộ (Docker Desktop phải đang chạy)
docker compose up -d
```

**4A — Database hiện có dữ liệu phải giữ:** nâng schema tại chỗ, **không rebuild**.

```bash
alembic upgrade head
```

**4B — Cố ý dựng lại toàn bộ từ `data/`:** chỉ dùng khi chấp nhận xoá sạch database.
Lệnh này tự gọi migrations rồi nạp catalog và dữ liệu; không chạy Alembic riêng trước nó.
Chưa có `data/` thì xem mục "Dữ liệu nguồn" ở dưới trước khi chạy.

```bash
python scripts/rebuild_db.py
```

```bash
# 5. Mở backend, rồi mở dashboard
#    TỪ 21/08: phải có DASHBOARD_KEY trong .env, xem mục bổ sung (2) ở cuối file.
python -m uvicorn backend.main:app --port 8000
#    và mở web/index.html, bấm Ctrl+Shift+R (tải lại bỏ qua bộ đệm)
```

Kiểm xem đã đúng chưa:

```bash
python scripts/audit_db.py       # kỳ vọng: 0 hong
python backend/check_api.py      # kỳ vọng: 18 dat, 0 hong (cần DASHBOARD_KEY)
```

---

## Chi tiết từng thay đổi, và vì sao nó cần bạn làm gì

### 🔴 `e6cfe2e` — PostgreSQL thành database mặc định, SQLite bị xoá

Một trong **hai** commit bắt buộc phải làm gì (cái kia là `3dc795b` ở cuối file). Ba việc
kéo theo:

| | |
|---|---|
| **`psycopg2` bắt buộc** | Trước đây bỏ qua được vì SQLite nằm sẵn trong Python. Giờ không. → chạy bước 2 |
| **Phải có Postgres chạy** | `docker-compose.yml` đã khai sẵn Postgres + pgAdmin. → chạy bước 3 |
| **`var/token_ledger.sqlite` không còn dùng** | File cũ trên máy bạn (nếu có) giờ là file mồ côi. Không cần xoá, nhưng đừng tưởng dashboard đang đọc nó |

DSN mặc định dựng từ biến môi trường, và **giá trị mặc định chạy được ngay không cần `.env`**:

```
PGHOST=127.0.0.1  PGPORT=5432  PGUSER=token  PGPASSWORD=token_local  PGDATABASE=token_ledger
```

Muốn đổi thì `cp .env.example .env` rồi sửa. Đổi mật khẩu thì phải `docker compose down -v`
rồi `up -d` lại — mật khẩu chỉ được đặt lúc container khởi tạo lần đầu.

~~Vẫn chạy được SQLite làm bản đối chiếu.~~ **Hết hiệu lực 24/08/2026** — SQLite đã bị
gỡ khỏi dự án (change `drop-the-sqlite-escape-hatch`). Đưa vào một DSN `.sqlite` nay
dừng ngay với thông báo nói rõ, chứ không im lặng tạo file.

### 🔴 `1de289f` — dashboard chỉ đọc từ database, không còn dữ liệu nhúng cứng

`web/js/app.js` trước đây nhúng sẵn 268 KB số liệu (`SEED_DAYS`), bảng giá, ngân sách. Đã
xoá hết (−6.127 dòng).

**Hệ quả bạn sẽ thấy ngay:** trước đây mở `web/index.html` là có số ngay cả khi backend
chưa chạy — số cũ, nhưng có. **Giờ không còn.** Backend chưa chạy thì trang hiện đúng
một thông báo lỗi nói rõ lỗi gì (4 loại: không gọi được, endpoint lỗi, database rỗng, mở
bằng `file://`).

Đó là chủ ý, không phải hồi quy: một bảng số cũ trông y hệt một bảng số mới.

**Bộ lọc trên trang sẽ bị đặt lại.** Khoá `localStorage` đổi từ
`agent-dash-state-v19-du-lieu-13-08` sang `agent-dash-prefs-v20`, và bản mới **chỉ** lưu
lựa chọn của người dùng chứ không lưu cả số liệu.

**Nhớ `Ctrl+Shift+R`.** Trình duyệt giữ `app.js` cũ trong bộ đệm là chuyện đã xảy ra và
tốn vài lượt để nhận ra.

### 🟢 `cbb4323` + `641b506` — đổi định danh sang tiếng Anh

Đổi tên biến/hàm trong `scripts/`, `db/`, `web/js/` (677 thêm / 677 xoá, cân bằng tuyệt đối).

**Không cần làm gì, và quan trọng hơn: mọi lệnh bạn đang nhớ vẫn nguyên.** Cờ dòng lệnh
(`--dot`, `--ra`, `--tho`, `--db`…) được giữ y hệt bằng `dest=` tường minh. Chú thích vẫn
tiếng Việt. Quy ước đặt tên ghi ở `docs/reference/cay-thu-muc.md`.

### 🟡 `b40ca39` — sửa 3 khoá dict mà đợt đổi tên làm gãy

Nếu bạn tình cờ pull đúng khoảng giữa `cbb4323` và `b40ca39`, đường ống sẽ **gãy ở bước
`[1/9]`** với `KeyError: 'login'`. Pull tới `HEAD` là hết. Không cần làm gì thêm.

### 🟡 `3ff22be` — `check_api.py` tự suy khoảng ngày từ database

Trước đây ngày kết thúc ghim cứng `2026-08-13`, nên sau mỗi lần nạp dữ liệu mới nó báo
lệch dù cả API lẫn database đều đúng. Giờ lấy `MIN(day), MAX(day)` từ `usage_resolved`.

### 🟡 `f6459e9` + `5b917f8` — chữ hiển thị cho người đọc

- `backend/store.py`: 4 chuỗi cảnh báo viết lại **có dấu** tiếng Việt → **phải khởi động
  lại backend** mới thấy.
- `web/js/app.js`: gỡ hẳn dải cảnh báo chất lượng dữ liệu khỏi đầu trang. `#load-note`
  giờ chỉ dùng khi nạp lỗi.

---

## Năm file đã bị XOÁ — lệnh cũ gọi tới chúng sẽ báo không tìm thấy

```
scripts/sinh_du_lieu_dashboard.py     sinh dữ liệu nhúng vào app.js  (501 dòng)
scripts/va_app_js.py                  vá app.js sau khi sinh          (150 dòng)
scripts/seed-days-that.js             dữ liệu mẫu                   (1.842 dòng)
web/js/app.js.bak                     bản sao lưu                   (3.222 dòng)
web/js/fallback/ralli-users.js         danh bạ Excel 622 dòng
```

Cả năm đều thuộc kiến trúc **cũ**, nơi số liệu được sinh ra rồi nhúng vào `app.js`. Kiến
trúc mới không có bước đó nữa: backend đọc database, frontend gọi backend.

Nếu bạn có script hay ghi chú cá nhân gọi tới chúng thì bỏ đi được.

---

## Dữ liệu nguồn — chỗ dễ tắc nhất

`rebuild_db.py` đọc **chỉ** từ thư mục `data/`, mà `data/` **không nằm trong git**
(`.gitignore` loại `data/*`, chỉ giữ đúng 1 file danh mục SKU của Google). Nên:

> **Nếu máy bạn chưa từng có `data/` thì bước 4 sẽ không chạy được.**

Dữ liệu không đưa lên git là có chủ ý: nó chứa danh sách **953 tài khoản kèm họ tên, email
và phòng ban**. Baseline `db/migrations/sql/001_baseline.sql` ghi rõ database này không
được ra mạng.

Cách lấy dữ liệu là **tự kéo bằng tài khoản của chính bạn**:

```bash
cp .env.example .env      # điền RALLI_USER/PASS và HD_USER/PASS
python scripts/update_dashboard.py    # trọn luồng 9 bước, ~14 phút
```

Bước này cần thêm quyền đọc Google Cloud Billing và Cloud Monitoring của 8 project. Chưa
có quyền thì nhắn cho người chủ trì — **đừng** chép thư mục `data/` hay bản `pg_dump` qua
chat hay ổ chung: cả hai đều là mang dữ liệu cá nhân của 953 người ra ngoài.

---

## 🔴 `3dc795b` — đổi giá trị cột `kind`, BẮT BUỘC rebuild

Đây là commit thứ hai trong đợt này **đổi nội dung database chứ không chỉ đổi code**, nên
bước 4 ở đầu file không phải tuỳ chọn.

| File | Nội dung |
|---|---|
| `db/load_org.py` | Thêm `kind = 'service_account'` cho 6 agent một-người-dùng |
| `db/migrations/sql/001_baseline.sql` | Ghi lại vì sao `kind` có giá trị thứ tư |
| `backend/store.py` | `health()` đếm độ phủ trên `usage_resolved` thay vì `fact_usage_daily` |
| `scripts/audit_db.py` | 2 phép kiểm mới (30 → 32 phép) |

Sau rebuild, bảng `account` sẽ là: `real` 937 · **`service_account` 6** ·
**`whole_agent` 2** · `unattributed` 8. Trước đó `whole_agent` có 8 dòng.

Không rebuild thì `audit_db.py` sẽ báo hỏng đúng một dòng, kèm sẵn lệnh phải chạy:

```
[ HONG ] Moi agent khong co danh ba co mot tai khoan dich vu
         0 tai khoan service_account / 6 agent khong co danh ba -
         database co the dung tu truoc 20/08/2026, chay lai scripts/rebuild_db.py
```

Con số sẽ đổi: cảnh báo độ phủ ở `/api/health` từ *"chỉ 12,4% quy được về tài khoản
thật"* thành *"98,5% quy được về một danh tính (12,1% người thật + 86,4% tài khoản dịch
vụ), 1,5% không quy được"*. Con số cũ không sai phép tính — nó gộp 6 agent
một-người-dùng, nơi ta **biết chính xác** ai dùng, vào cùng rổ với phần Google thật sự
không biết.

---

## Vì sao chưa tự động được

Git **cố ý** không chạy code khi bạn `git pull` — nếu chạy thì pull code lạ về là bị chạy
code lạ. Hook thì không đi theo repo, mỗi máy phải tự cài. Nên hiện tại vẫn cần đọc một
file như file này.

Hướng đang bàn để lần sau không cần nữa:

1. **Vân tay code ghi trong database** — bảng `schema_meta` giữ sha256 của `db/*.sql` +
   `db/*.py`. Backend và `audit_db.py` so lại lúc chạy, lệch thì in đúng lệnh cần chạy.
   Phép kiểm `service_account` ở trên đã làm đúng việc này cho **một** loại lệch; vân tay
   bắt **mọi** loại.
2. **Một lệnh duy nhất** `python scripts/setup.py` — kiểm Docker, kiểm `.env`, rebuild nếu
   vân tay lệch. Đọc một dòng README thay cho cả file này.

Chưa làm. Nếu thấy cần thì nói, nó là một đề xuất riêng.

---

## Tự kiểm: coi như đã đồng bộ đúng khi

| Lệnh | Kết quả mong đợi |
|---|---|
| `docker compose ps` | `token-ledger-postgres` trạng thái `healthy` |
| `python scripts/audit_db.py` | `36 phep kiem \| 31 dat \| 5 luu y \| 0 hong` (các dòng "lưu ý" là lỗ hổng dữ liệu đã biết, không phải lỗi) |
| `python backend/check_api.py` | `18 phep kiem \| 18 dat \| 0 hong` (cần `DASHBOARD_KEY`) |
| `node tests/date-range-filter.test.js` | `pass 6, fail 0` |
| `node tests/load-failure-states.test.js` | `pass 11, fail 0` |
| Mở `web/index.html` | hỏi khoá một lần, rồi có số liệu và **không** có dải cảnh báo |

Còn hỏng chỗ nào thì gửi nguyên văn dòng `[ HONG ]` — mỗi phép kiểm đều tự nói nó kiểm
gì và lệch bao nhiêu.


---

## Bổ sung 21/08/2026 — lại phải rebuild

Change `admit-gateway-as-a-fourth-source` **đổi schema**, nên bước rebuild ở trên là bắt
buộc lần nữa. Pull code mới mà không rebuild thì backend sẽ ném lỗi ở `ref_source` —
**hỏng ồn ào, không hỏng im lặng**, nên không sợ chạy nhầm trên database cũ.

```bash
git pull
docker compose up -d
python scripts/rebuild_db.py        # ~60 giây, 7/7 bước
python scripts/audit_db.py          # 36 phép, 0 hỏng
```

**Ba thứ mới trong database:**

| | |
|---|---|
| Bảng `ref_source` | 4 dòng, nói mỗi nguồn có biết người dùng / có tiền hoá đơn không |
| `usage_resolved` | thêm nhánh `gateway`, đứng **đầu** thứ tự ưu tiên |
| 6 tài khoản dịch vụ | đổi tên `__whole_agent_<id>__` → **`svc.<code>`** |

**Con số phải giữ nguyên sau rebuild** — lệch là có chuyện:

```
   usage_resolved     1.189 dòng · 867.657.110 token · $291,985601
   usage_by_account     320 dòng · 107.926.810 token
   độ phủ             104.990.903 / 749.483.267 / 13.182.940
```

**Một công cụ mới đáng biết:** `python tools/dien_tap_gateway.py` chèn dữ liệu Gateway giả
mang username thật, đo xem dashboard có nhúc nhích không, rồi `ROLLBACK`. Nó **không để lại
gì** trong database. Chạy được bất cứ lúc nào, và phải ra `DAT 7/7`.

---

## 🔴 Bổ sung 21/08/2026 (2) — API giờ ĐÒI MỘT KHOÁ, không có khoá thì máy chủ không chạy

Change `require-a-key-to-read-the-api`. **Đây là thay đổi dễ làm bạn tắc nhất trong cả
tuần**, vì triệu chứng của nó không giống một lỗi:

```
   Chua dat DASHBOARD_KEY  ->  uvicorn KHONG khoi dong duoc
   Da dat, chua nhap tren  ->  dashboard hien O NHAP KHOA, khong hien so
   trinh duyet
```

Máy chủ **cố tình** không chạy khi thiếu khoá. Chế độ hỏng phải là *"không chạy"*, tuyệt
đối không phải *"chạy mở"* — chạy mở là có đúng lỗ hổng cũ cộng thêm niềm tin sai rằng đã
khoá.

### Làm gì — một lần, rồi thôi

```bash
git pull

# 1. Sinh một khoá (chuoi ngau nhien, khong phai mat khau tu nghi)
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 2. Dan vao .env o goc repo  (backend doc file nay, khong can `set`)
#       DASHBOARD_KEY=<khoa vua sinh>
#    File .env nam trong .gitignore nen khoa khong len git.
#    Xem mau day du o .env.example.

# 3. Chay nhu cu
python -m uvicorn backend.main:app --port 8000
```

Rồi mở dashboard: nó hỏi khoá **một lần**, dán đúng chuỗi ở bước 1 vào. Trình duyệt nhớ cho
các lần sau (`localStorage`, theo từng máy và từng trình duyệt).

> **Khoá của bạn không cần giống khoá của người khác.** Mỗi máy chạy backend riêng, nên
> mỗi người tự sinh một khoá cho máy mình. Chỉ khi nào dùng chung một máy chủ thì mới phải
> thống nhất.

### Bốn triệu chứng và cách đọc chúng

| Thấy gì | Nghĩa là | Làm gì |
|---|---|---|
| `THIEU BIEN MOI TRUONG: DASHBOARD_KEY`, uvicorn thoát ngay | Chưa có khoá | Làm bước 1–2 ở trên |
| Dashboard hiện **ô nhập khoá** màu xanh | Máy chủ chạy đúng, trình duyệt chưa có khoá | Dán khoá vào |
| Ô nhập khoá màu **đỏ**, "Khoá không đúng" | Khoá trên trình duyệt khác khoá của máy chủ | Dán lại khoá trong `.env` |
| `check_api.py` thoát với *"tra 401 - khoa khong dung"* | Máy chủ đang chạy bằng một khoá khác `.env` hiện tại | Khởi động lại uvicorn |

### Chỉ khi phát triển, và phải khai ra

```bash
DASHBOARD_OPEN=1   # bo qua xac thuc; may chu IN CANH BAO moi lan khoi dong
```

Đặt biến này trên máy có thể ra mạng là mở lại đúng lỗ hổng vừa bịt. `check_api.py` sẽ
**báo hỏng** khi máy chủ chạy ở chế độ này — đó là chủ ý, để chế độ mở không bao giờ im lặng.

### Một công cụ mới, chạy được trên máy trắng

```bash
python tools/soat_khoa_api.py     # ky vong: 24 dat, 0 hong
```

Nó **tự dựng máy chủ** ở nhiều cấu hình (có khoá · thiếu khoá · thiếu khoá kèm
`--reload` · khoá toàn khoảng trắng · `DASHBOARD_OPEN=1`) rồi tự tắt. **Không cần
Docker, không cần database, không đụng `.env` của bạn** — nên đây là thứ duy nhất trong
repo chạy được ngay sau khi `git clone`.

Vì sao nó không trùng với `check_api.py`: bộ kia gọi một máy chủ **đang** chạy, nên nó
vẫn xanh nếu ai đó lỡ tay gỡ mất phần chặn — lúc ấy máy chủ vẫn trả lời bình thường.
Bộ này tự dựng máy chủ nên bắt được cả trường hợp *đáng lẽ không được chạy mà vẫn chạy*.
