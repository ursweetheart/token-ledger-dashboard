# Những thay đổi cần đồng bộ trên máy đồng nghiệp — ngày 20/08/2026

**Ai cần đọc:** bất kỳ ai lần cuối `git pull` **trước ngày 17/08/2026**.

`origin/main` trước sáng 18/08 nằm ở `4d7060e` (16/08). Từ đó tới nay có **11 commit** —
2 commit tài liệu ngày 16/08 (`ed55d06`, `4e1ef52`, không cần làm gì) và 9 commit thay đổi
mã nguồn.

Trong đó có một thay đổi **không tự chạy được** sau khi pull: database mặc định chuyển từ
SQLite sang PostgreSQL. Pull code về mà không làm gì thêm thì dashboard sẽ **báo lỗi
không nối được database** — không phải hiện số sai, mà là hiện thông báo lỗi.

---

## Làm gì — 5 bước, khoảng 3 phút (chưa tính bước nạp dữ liệu)

```bash
# 1. Lấy code
git pull

# 2. psycopg2 giờ BẮT BUỘC, không còn là tuỳ chọn
pip install -r backend/requirements.txt

# 3. Dựng PostgreSQL cục bộ (Docker Desktop phải đang chạy)
docker compose up -d

# 4. Dựng lại database — CHỈ chạy được nếu máy bạn đã có thư mục data/
#    Chưa có data/ thì xem mục "Dữ liệu nguồn" ở dưới TRƯỚC khi chạy bước này.
python scripts/rebuild_db.py

# 5. Mở backend, rồi mở dashboard
python -m uvicorn backend.main:app --port 8000
#    và mở web/index.html, bấm Ctrl+Shift+R (tải lại bỏ qua bộ đệm)
```

Kiểm xem đã đúng chưa:

```bash
python scripts/audit_db.py       # kỳ vọng: 0 hong
python backend/check_api.py      # kỳ vọng: 16 dat, 0 hong
```

---

## Chi tiết từng thay đổi, và vì sao nó cần bạn làm gì

### 🔴 `e6cfe2e` — PostgreSQL thành database mặc định, SQLite bị xoá

Đây là thay đổi duy nhất **bắt buộc** phải làm gì. Ba việc kéo theo:

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

Vẫn chạy được SQLite làm bản đối chiếu, nhưng phải chỉ định tường minh:
`python scripts/rebuild_db.py --db var/token_ledger.sqlite`.

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
và phòng ban**. `db/01_schema.sql` ghi rõ database này không được ra mạng.

Cách lấy dữ liệu là **tự kéo bằng tài khoản của chính bạn**:

```bash
cp .env.example .env      # điền RALLI_USER/PASS và HD_USER/PASS
python scripts/update_dashboard.py    # trọn luồng 9 bước, ~14 phút
```

Bước này cần thêm quyền đọc Google Cloud Billing và Cloud Monitoring của 8 project. Chưa
có quyền thì nhắn cho người chủ trì — **đừng** chép thư mục `data/` hay bản `pg_dump` qua
chat hay ổ chung: cả hai đều là mang dữ liệu cá nhân của 953 người ra ngoài.

---

## Đang chờ commit — chưa pull được, nhưng biết trước thì đỡ ngạc nhiên

Bốn file đang sửa trên máy chủ trì, sẽ commit sau khi rà soát xong:

| File | Nội dung |
|---|---|
| `db/load_org.py` | Thêm `kind = 'service_account'` cho 6 agent một-người-dùng |
| `db/01_schema.sql` | Ghi lại vì sao `kind` có giá trị thứ tư |
| `backend/store.py` | `health()` đếm độ phủ trên `usage_resolved` thay vì `fact_usage_daily` |
| `scripts/audit_db.py` | 2 phép kiểm mới (30 → 32 phép) |

**Khi đợt này về, sẽ PHẢI chạy lại `python scripts/rebuild_db.py`** — nó đổi giá trị cột
`kind` trong bảng `account`, tức đổi *nội dung* database chứ không chỉ đổi code.

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
| `python scripts/audit_db.py` | `32 phep kiem \| ... \| 0 hong` (4 dòng "lưu ý" là lỗ hổng dữ liệu đã biết, không phải lỗi) |
| `python backend/check_api.py` | `16 phep kiem \| 16 dat \| 0 hong` |
| `node tests/date-range-filter.test.js` | `pass 6, fail 0` |
| `node tests/load-failure-states.test.js` | `pass 7, fail 0` |
| Mở `web/index.html` | có số liệu, **không** có dải cảnh báo ở đầu trang |

Còn hỏng chỗ nào thì gửi nguyên văn dòng `[ HONG ]` — mỗi phép kiểm đều tự nói nó kiểm
gì và lệch bao nhiêu.
