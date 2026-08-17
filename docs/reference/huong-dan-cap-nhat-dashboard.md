# Hướng dẫn cập nhật dữ liệu dashboard

> Dashboard đọc số từ **database qua backend chỉ-đọc**. `api.js` gọi 8 endpoint của
> FastAPI; `app.js` chỉ nhận và vẽ.
>
> Vẫn còn một **bản dự phòng ngoại tuyến**: số liệu được vá cứng vào `app.js` ở bước
> cuối, để bấm đúp `web/index.html` không cần backend vẫn xem được. Đó là đường phụ,
> không phải đường chính.
>
> "Cập nhật dashboard" = thu thập lại mọi nguồn → dựng lại database → vá bản dự phòng.

---

## Chạy

```bash
python scripts/update_dashboard.py
```

Hết. Khoảng 12–17 phút, phần lớn là bước kéo Cloud Monitoring.

Xem kết quả:

```bash
python -m uvicorn backend.main:app --port 8000        # backend chỉ-đọc
cd web && python -m http.server 8080 --bind 127.0.0.1  # dashboard
```

Cả hai vế của lệnh thứ hai đều cần: `cd web` chặn *cái gì* lộ ra, `--bind` chặn *ai*
vào được. Xem [`cay-thu-muc.md`](cay-thu-muc.md#ranh-giới-phục-vụ--chỉ-web-ra-được-mạng).

### Lần đầu: tạo `.env`

```bash
cp .env.example .env
```

Rồi điền một trong hai:

```bash
# Cách A — script tự đăng nhập, không phải dán gì
RALLI_USER=...
RALLI_PASS=...
HD_USER=...
HD_PASS=...

# Cách B — dán JWT sẵn (ưu tiên hơn A nếu điền cả hai)
RALLI_JWT=eyJ...
HD_JWT=eyJ...
```

`.env` đã nằm trong `.gitignore`. Biến môi trường thật (`export`/`set`) luôn thắng giá
trị trong file.

Thử riêng phần xác thực trước khi chạy cả chuỗi:

```bash
python scripts/pull_web_apps.py --chi-kiem-token
```

Nó chỉ lấy token, in hạn dùng rồi dừng. **Không in token ra màn hình.**

---

## Mười bước, đánh số 0→10

```
 0  Kiểm hoá đơn đã mới chưa           vài giây   ← DỪNG nếu cũ
 1  Kiểm/lấy token 2 web app           vài giây   ← DỪNG nếu hỏng
 2  Kéo Cloud Monitoring               10–15 ph
 3  Gộp các đợt kéo Monitoring         ~30 giây
 4  Kéo Ralli + TLA Hợp Đồng           ~1 phút
 5  Kéo chiều người dùng TLA HĐ        ~100 lượt GET
 6  Gộp hoá đơn từ 7 file Console      ~1 giây
 7  Gộp histogram độ trễ theo ngày     ~1 giây
 8  Dựng lại database                  ~15 giây   ← schema + 7 khâu nạp
 9  Soi database                       ~5 giây    ← 30 phép kiểm
10  Vá dữ liệu dự phòng vào app.js     ~5 giây    ← bản offline
```

Hỏng bước nào là **dừng ngay**. Không bước nào chạy tiếp trên đầu ra dở dang của bước
trước.

**Vì sao bước 0 và 1 đứng đầu:** bước 2 mất hơn 10 phút. Phát hiện thiếu file hoá đơn
hoặc token hỏng *sau* đó là vứt đi 10 phút vô cớ, trong khi cả hai phép kiểm chỉ mất vài
giây. Bước 1 đăng nhập một lần rồi vứt token đi, bước 4 đăng nhập lại — hai lần đăng
nhập rẻ hơn nhiều so với một lần kéo Monitoring bị bỏ.

**Vì sao bước 5 tách khỏi bước 4:** `pull_web_apps.py` chỉ lấy các trang tổng hợp có
sẵn. Chiều `ngày × người × model` của TLA Hợp Đồng phải kéo riêng, mỗi người một lượt
GET — xem docstring `pull_hd_usage.py`. Thiếu bước này thì bước 8 dừng vì `load_org.py`
không tìm thấy `usage-day-user-model.json`.

### Cờ dòng lệnh

| Cờ | Dùng khi |
|---|---|
| `--bo-monitoring` | Đã kéo Monitoring hôm nay rồi. Vẫn gộp lại từ các đợt đã có. |
| `--hoa-don-cu` | Cố ý chạy với hoá đơn chưa tải mới. |
| `--ngay-monitoring N` | Đổi cửa sổ kéo (mặc định 196). Google chỉ giữ một phần, xin rộng không hại gì. |

---

## Từng script làm gì

**Trong đường ống** — `update_dashboard.py` gọi tự động, không cần chạy tay:

| Script | Vai trò | Bước |
|---|---|---|
| `update_dashboard.py` | Điều phối cả 9 bước | — |
| `pull_monitoring.py` | Kéo time series từ Cloud Monitoring qua `gcloud` | 2 |
| `merge_monitoring.py` | Gộp nhiều đợt kéo, khử trùng lặp | 3 |
| `pull_web_apps.py` | Kéo Ralli + TLA HĐ qua API của chúng | 4 |
| `pull_hd_usage.py` | Chiều ngày × người × model của TLA HĐ | 5 |
| `merge_billing.py` | Gộp 7 CSV Console thành một file chuẩn hoá | 6 |
| `merge_latency_daily.py` | Gộp histogram độ trễ, đọc ra p50/p95/p99 | 7 |
| `rebuild_db.py` | Dựng lại database (PostgreSQL mặc định): schema + 7 khâu nạp | 8 |
| `audit_db.py` | 30 phép kiểm chia 5 nhóm | 9 |

**Chạy tay khi cần** — không nằm trong đường ống:

| Script | Vai trò |
|---|---|
| `copy_to_postgres.py` | Sao database SQLite sang PostgreSQL, bản sao 1:1 |
| `pull_sku_catalog.py` | Kéo danh mục SKU + bảng giá chính chủ của Google |
| `pull_latency_distribution.py` | Kéo histogram độ trễ thô |
| `check_monitoring.py` | Lọc một đợt kéo và in số liệu chứng minh nó lành |
| `make_readable.py` | Đổi một đợt kéo thô thành file mở được bằng Excel |

Script chẩn đoán một lần nằm ở `tools/`, **không** ở đây — chúng được phép mục.

Mọi script `pull_*` và `merge_*` đều **ghi vào thư mục mới theo ngày, không bao giờ ghi
đè đợt cũ**. Xem §"Đừng xoá thư mục kéo cũ" để biết vì sao đó không phải cẩn thận thừa.

---

## Việc vẫn phải làm tay: tải hoá đơn

Google Cloud Console không cho tải báo cáo GMSSub qua API với quyền hiện có. Mỗi lần
cập nhật:

1. Cloud Console → Billing → Reports
2. Tải 7 file, mỗi project một file
3. Bỏ vào `data/billing/`, giữ nguyên tên
   `rangdong.com.vn - GMSSub_Reports, <khoảng ngày>,<TÊN HIỂN THỊ>.csv`

Bước 0 đọc cột `Date` trong các file đó. Ngày mới nhất cũ hơn hôm qua ⇒ dừng.

**Không được chạy tiếp với hoá đơn cũ.** Khi đó dashboard sẽ có request của hôm nay
nhưng token của tuần trước — sai mà trông như thật.

⚠️ **Tên file mang tên hiển thị, không phải project ID.** `AI-sale_agent` ↔
`tranquil-post-471401-c1`, không chữ nào chung. Bảng ánh xạ 7 dòng khai báo cứng trong
`scripts/merge_billing.py`. Tên lạ ⇒ script dừng và in tên đó ra. Đoán gần đúng sẽ trúng
5/7 và trượt đúng 2 project chiếm **81% số tiền**.

---

## Khi hỏng

### "Hoa don CU: ngay moi nhat 2026-08-XX"
Tải lại 7 file GMSSub. Xem mục trên.

### "khong co token va khong co tai khoan de dang nhap"
Chưa có `.env`, hoặc chưa điền. `cp .env.example .env` rồi điền.

### "HTTP 401/403 khi dang nhap - sai tai khoan/mat khau"
Sai user/pass. Script không thử lại vì đổi kiểu body cũng vô ích.

### "dang nhap OK nhung khong tim thay token; khoa: [...]"
Đăng nhập được nhưng tên trường chứa token khác dự kiến. Script đã thử `access_token`,
`token`, `accessToken`, `jwt`, và cả `data.<...>`. Xem danh sách khoá nó in ra rồi bổ
sung vào `dang_nhap()` trong `scripts/pull_web_apps.py`.

### "HTTP 422" khi đăng nhập TLA HĐ
TLA HĐ không phơi `openapi.json` nên kiểu body là **suy đoán**. Script tự thử JSON rồi
form-encoded. Hỏng cả hai thì mở DevTools → Network, đăng nhập tay một lần, xem request
thật gửi gì.

### `load_org.py` báo thiếu `usage-day-user-model.json`
Bước 5 chưa chạy. Xem §"Vì sao bước 5 tách khỏi bước 4".

### Dashboard mở lên không hiện số
Từ 17/08/2026 dashboard **không còn dữ liệu dự phòng**: nạp không được thì nó báo lỗi
trên màn hình kèm địa chỉ đã thử, chứ không lặng lẽ hiện số cũ. Đọc đúng dòng thông báo
đó — nó phân biệt bốn trường hợp:

| Thông báo | Nghĩa | Làm gì |
|---|---|---|
| Không nối được backend | không tới được máy chủ | `docker compose ps` · bật uvicorn · kiểm cổng |
| Backend trả về lỗi | máy chủ trả mã HTTP lỗi | xem log uvicorn, thông báo có nói endpoint nào |
| Database chưa có dữ liệu sử dụng | nối được, `/api/health` không có khoảng ngày | `rebuild_db.py` rồi `audit_db.py` |
| Đang mở bằng `file://` | thiếu máy chủ tĩnh | chạy `http.server` từ trong `web/` |

`localStorage` từ nay **chỉ giữ lựa chọn người dùng** (tab, giao diện, khoảng ngày, cây
đang bung) — không giữ số liệu, nên nó không còn là nguồn số cũ. Không cần bump khoá theo
mỗi lần cập nhật dữ liệu nữa.

### `merge_monitoring.py` báo "lech gia tri"
Cùng một phép đo, cùng mốc thời gian, hai đợt kéo cho số khác nhau. Script giữ giá trị
của **đợt mới** và in ví dụ ra. Đo ngày 13/08: 3 khoá lệch trên 500.879 khoá chồng nhau
(0,0006%), và đợt mới đều cho số **nhỏ hơn** — dấu hiệu Google hạ độ phân giải dữ liệu
cũ theo thời gian. Số ít thì bỏ qua được; nhiều lên thì phải xem lại quy tắc ưu tiên.

### `audit_db.py` báo "hong"
Đọc kỹ dòng báo. Mục `luu y` là dữ liệu thiếu **đã biết**, không phải lỗi — hiện có 4
mục như vậy. Mục `hong` thì phải dừng: nó nghĩa là hai nguồn cùng mô tả một thứ mà cho
số khác nhau.

---

## Ba cái bẫy đã biết

### 1. Đừng xoá thư mục kéo Monitoring cũ

Cửa sổ lưu giữ của Google **không có độ rộng cố định**. Đo hai lần bằng cùng script:

| Ngày kéo | Ngày sớm nhất trả về | Độ rộng |
|---|---|---|
| 06/08/2026 | 22/01/2026 | 196 ngày |
| 13/08/2026 | **23/04/2026** | **112 ngày** |

Bảy ngày trôi qua, mép cửa sổ nhảy **91 ngày**. Dữ liệu 22/01–22/04 giờ chỉ còn tồn tại
trên đĩa ở `data/raw_google_console/du_lieu_giam_sat/2026-08-06-1m/`.

⇒ Một đợt kéo đơn lẻ **không còn phủ hết dải ngày**. Phải gộp. Xoá thư mục cũ là mất
vĩnh viễn.

### 2. Ngày cuối của mỗi bản export hoá đơn là số TẠM

Đối chiếu bản export 05/08 với bản 13/08: 0 dòng biến mất, nhưng **8 dòng bị viết lại —
toàn bộ nằm trên ngày cuối cùng** của bản cũ. Mức lệch không nhỏ:

```
SKU 07D6-73CA-C859    22.326  ->  2.646.520 token   (118 lần)
SKU F2C1-F842-5D84    55.829  ->  1.606.920 token   ( 29 lần)
```

Nguyên nhân: hoá đơn tính theo **giờ Pacific**. Tải lúc 10h sáng giờ Việt Nam là ngày
Google mới chạy được ~20 tiếng.

⇒ Lịch sử bất biến từ ngày kề-cuối trở về trước (2.251/2.259 dòng khớp tuyệt đối), nhưng
**ngày cuối luôn phải coi là chưa chốt**.

### 3. Ngày cuối trên dashboard: tiền là ƯỚC TÍNH, không phải số đo

Monitoring và Ralli có dữ liệu tới hôm nay; hoá đơn chỉ tới hôm qua.

**Triệu chứng này đã đảo chiều khi backend ra đời.** Trước kia ngày cuối hiện gần như
không có tiền — thiếu rõ ràng, dễ nhận ra. Bây giờ `api.js` trả `cost_usd = NULL` cho
dòng chưa có hoá đơn, và `app.js` hàm `cost(r)` **tự ước tính theo bảng giá**. Ngày cuối
giờ hiện một con số **trông y như đã đo**.

Đo ngày 16/08/2026, khoảng 01/08–13/08:

```
hoa don that : $26.93
hien thi     : $39.73        <- 32% la uoc tinh
13/08        : 100% uoc tinh (hoa don chua ve)
02/08        :  86% uoc tinh (hien 8.69, hoa don chi 1.24)
```

⇒ Giao diện **chưa phân biệt hai loại số này**. Trước khi trích số chi phí ra báo cáo,
kiểm bằng:

```bash
curl -s "http://127.0.0.1:8000/api/usage?start=...&end=..." \
  | python -c "import json,sys; r=json.load(sys.stdin); \
      print(sum(x['cost_usd'] for x in r if x['cost_usd'] is not None))"
```

Chênh giữa số đó và số trên màn hình chính là phần ước tính.

---

## Kỷ luật chỉ-đọc

Mọi endpoint dữ liệu của `pull_web_apps.py` và `pull_hd_usage.py` là `GET` trên **danh
sách trắng khai báo cứng**. Không phải sự cẩn thận thừa: hai API này còn phơi ra

```
POST   /trigger-data-fetch          POST   /logs/cleanup
POST   /api/ctda/refresh-data       DELETE /users/{id}
POST   /upload-product-excel        PUT    /api/units/{id}
```

Ngoại lệ **duy nhất** là `POST /auth/login` để lấy token — được chọn có ý thức ngày
13/08/2026 để chạy được một lệnh. Token không bao giờ được in ra màn hình hay ghi xuống
đĩa.

Backend cũng chỉ-đọc: `store.py` mở SQLite bằng `mode=ro`, và kiểm `p.exists()` trước
đó nên đường dẫn sai **báo lỗi** thay vì lặng lẽ tạo database rỗng.

---

## Sau khi chạy

### Database

```bash
python scripts/audit_db.py        # 30 phep kiem, 5 nhom
```

Kỳ vọng hiện tại: `26 dat | 4 luu y | 0 hong`.

### Bản dự phòng ngoại tuyến

Bước 10 chỉ đổi **3 loại literal** trong `web/js/app.js`: khối `SEED_DAYS`, hằng `STORE`,
và khoảng ngày mặc định. Không hàm nào, không thẻ HTML nào bị đụng. Kiểm nhanh:

```bash
node --check web/js/app.js
git diff --stat web/js/app.js
```

Khoảng ngày mặc định được **suy từ ngày cuối cùng có dữ liệu**, không ghim cứng — nên
dashboard mở ra luôn ở tháng hiện tại mà không cần sửa gì thêm.

Đường ống **không ghi vào `web/`** nữa: chạy trọn xong thì `git status web/` phải trống.

### API

```bash
python backend/check_api.py                                   # 16 phep kiem
python backend/check_api.py --compare http://127.0.0.1:8001   # 24, so SQLite voi PostgreSQL
```
