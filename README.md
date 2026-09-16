# Agent Analytics · Token Ledger

Bảng điều khiển chi phí AI agent. Dữ liệu lấy từ hoá đơn Google Cloud, Cloud Monitoring
và hai web app nội bộ, gom vào một database rồi hiển thị qua API chỉ-đọc.

## Cách chạy

```bash
# 1. Database — PHẢI lên trước, PostgreSQL là mặc định từ 17/08/2026
docker compose up -d

# 2. Backend chỉ-đọc — phục vụ dữ liệu từ database
python -m uvicorn backend.main:app --port 8000

# 3. Dashboard — LƯU Ý cả hai vế của lệnh này đều cần thiết
cd web && python -m http.server 8080 --bind 127.0.0.1
```

Mở `http://127.0.0.1:8080`.

**Vì sao PostgreSQL, không phải SQLite:** SQLite là *một file* — không đi qua mạng nên
container khác không đọc được, và không có schema riêng lẫn `GRANT` theo user nên không
chia quyền theo service được. Cả hai chặn đường việc chạy nhiều bản sau một load balancer.

Đường SQLite **đã bị gỡ hẳn** ngày 24/08/2026: nó không còn dữ liệu (file bị xoá 17/08),
không dựng lại được (tệp schema đơn khối cũ hỏng cú pháp trên SQLite từ 21/08), và chưa từng có
phép kiểm nào chạy trên nó. Đưa vào một DSN `.sqlite` nay dừng ngay với thông báo rõ.

Đổi database bằng **một** biến, có hiệu lực cho cả backend và mọi script:

```bash
export TOKEN_LEDGER_DSN=postgresql://token:token_local@127.0.0.1:5432/token_ledger_v2
```

Thông số kết nối lấy từ `PGHOST` / `PGPORT` / `PGUSER` / `PGPASSWORD` / `PGDATABASE` —
**cùng tên** với `docker-compose.yml`, nên đặt trong `.env` là cả container lẫn script đều
theo.

> ⚠️ `docker compose down -v` **xoá sạch** volume `pgdata`, tức mất database đang chạy.
> Dựng lại được bằng `python scripts/rebuild_db.py` (~1 phút) **miễn là `data/` còn** —
> `data/` là thứ duy nhất mất là mất vĩnh viễn.

**`cd web`** chặn *cái gì* lộ ra: chạy ở gốc repo thì `.env`, database (937 nhân viên
kèm email) và `data/` đều tải được qua HTTP. **`--bind 127.0.0.1`** chặn *ai* vào được:
mặc định của `http.server` là mọi giao diện mạng, tức cả LAN công ty.

**Không có backend thì dashboard KHÔNG hiện số** — nó báo lỗi kèm địa chỉ đã thử và
cách khắc phục. Trước 17/08/2026 bấm đúp `index.html` vẫn xem được nhờ dữ liệu dự phòng
vá sẵn trong `app.js`; đã bỏ, vì chính cơ chế đó che mất mọi lỗi backend: dữ liệu dự
phòng không tự biết mình cũ, nên số cũ hiện lên trông y hệt số mới. Đã đo lúc bỏ — khối
dự phòng lệch 15,6% so với database, chỉ 25/224 ngày khớp.

## Cập nhật dữ liệu

```bash
python scripts/update_dashboard.py        # 9 bước, ~15 phút, có 1 bước tay
```

Chi tiết từng chặng: [`docs/reference/toan-trinh-du-lieu.md`](docs/reference/toan-trinh-du-lieu.md)

## Phép kiểm

```bash
node --test tests/*.test.js                          # 51 phép
python -m unittest discover -s tests -p "test_*.py"  # 11 phép
```

**Không cần cài gì** — không có `package.json`, không có `requirements` cho phần kiểm. Đã đo trong
container trắng: `node:24-alpine` và `python:3.12-slim` đều chạy đủ, không cài gói nào.

Cả hai lệnh này chạy tự động trên mỗi lần đẩy code, kèm một nhóm canh cấu hình. Xem
[`.github/workflows/ci.yml`](.github/workflows/ci.yml) — đừng chép lại nội dung nó vào đây, hai bản
sao sẽ trôi khỏi nhau.

## Thư mục

| | |
|---|---|
| `web/` | Dashboard — **document root**, chỉ thư mục này được phục vụ ra mạng |
| `backend/` | API chỉ-đọc, 8 endpoint |
| `scripts/` | Đường ống: kéo → gộp → điều phối |
| `db/` | Migration, danh mục `.sql`, và các module nạp |
| `data/` | Dữ liệu thô — mất là mất vĩnh viễn |
| `var/` | Artifact dựng lại được: `baselines/` và `snapshots/`; database chạy nằm trong volume Docker `pgdata` |
| `tests/` | Phải luôn xanh |
| `tools/` | `diagnostics/`, `bench/`, `probes/`, `gateway-smoke/` — không thuộc production pipeline |
| `docs/` | `reference/` đang là gì · `decisions/` · `archive/` |
| `planning/` | Tài liệu nghiệp vụ và sketch; không phải runtime input |

Quy tắc đầy đủ, kèm bảng "thêm file mới thì để đâu":
[`docs/reference/cay-thu-muc.md`](docs/reference/cay-thu-muc.md)

## Tài liệu

- [Toàn trình dữ liệu](docs/reference/toan-trinh-du-lieu.md) — 9 bước từ nguồn tới màn hình
- [Mô tả database](docs/reference/mo-ta-database.md) — 18 bảng, 30 phép kiểm
- [Cây thư mục](docs/reference/cay-thu-muc.md)
- [API TLA Hợp Đồng](docs/reference/api-map-tla-hd.md)
- [Luật cho lệnh triển khai tự động](docs/reference/luat-trien-khai-tu-dong-13-09.md) — ba thứ bị cấm, mỗi thứ một lý do đã đo

---

## ⚠️ Phần dưới đây đã lỗi thời

Nội dung dưới mô tả cách làm việc **trước khi có database và backend**, khi dữ liệu
được gõ tay vào form và lưu trong `localStorage` của trình duyệt. Cách đó đã bị thay
thế hoàn toàn bởi đường ống dữ liệu. Giữ lại để đối chiếu, **không làm theo**.

<details>
<summary>Hướng dẫn cũ (nhập liệu tay)</summary>

**Nhập liệu theo ngày:** panel `✎ Dữ liệu nguồn` (nút, form, và cả hai nút 💾 Lưu ngày
này / 🗑 Xoá ngày) **đã bị xoá 17/08/2026**. Nó trở thành cái bẫy khi dashboard chỉ đọc
database: người dùng gõ số, số hiện lên và cộng vào tổng — trộn với số từ database mà
không gì nói ra — rồi tải lại trang là mất sạch.

**Cấu hình giá:** `⚙ Cấu hình giá` **vẫn còn và vẫn dùng được** — sửa đơn giá
input/output theo model để thử "nếu giá khác thì tiền bao nhiêu". Nó chỉ đổi trong phiên,
không ghi xuống đâu, và không giả vờ là số đo.

**Lưu ý cũ:** `localStorage` từng giữ cả số liệu; nay nó **chỉ giữ lựa chọn** (tab, giao
diện, khoảng ngày, cây đang bung). Cây phòng ban còn nhúng trong `app.js`, nhưng danh bạ
937 tài khoản thì đến từ `/api/accounts` — bản Excel 622 dòng nhúng cứng đã bỏ.

</details>

Hai thứ dưới đây thì **vẫn đúng**:

- **Khoảng thời gian** — ô "Từ → Đến" hoặc nút 7/30/90 ngày. Dashboard cộng mọi ngày
  nằm trong khoảng.
- **Giao diện sáng/tối** — nút ☀️ / 🌙 trên thanh công cụ.
