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

Đổi database bằng **một** biến, có hiệu lực cho cả backend và mọi script:

```bash
export TOKEN_LEDGER_DSN=var/token_ledger.sqlite     # quay về SQLite để đối chiếu
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

Không có backend thì mở `web/index.html` bằng cách bấm đúp vẫn xem được — dashboard
quay về dữ liệu dự phòng đã vá sẵn trong `app.js`, nhưng số sẽ cũ.

## Cập nhật dữ liệu

```bash
python scripts/update_dashboard.py        # 10 bước, ~15 phút, có 1 bước tay
```

Chi tiết từng chặng: [`docs/reference/toan-trinh-du-lieu.md`](docs/reference/toan-trinh-du-lieu.md)

## Thư mục

| | |
|---|---|
| `web/` | Dashboard — **document root**, chỉ thư mục này được phục vụ ra mạng |
| `backend/` | API chỉ-đọc, 8 endpoint |
| `scripts/` | Đường ống: kéo → gộp → điều phối |
| `db/` | Schema `.sql` và các module nạp |
| `data/` | Dữ liệu thô — mất là mất vĩnh viễn |
| `var/` | Database đang chạy — dựng lại được bằng `rebuild_db.py` |
| `tests/` | Phải luôn xanh |
| `tools/` | Chẩn đoán một lần — được phép mục |
| `docs/` | `reference/` đang là gì · `decisions/` · `archive/` |

Quy tắc đầy đủ, kèm bảng "thêm file mới thì để đâu":
[`docs/reference/cay-thu-muc.md`](docs/reference/cay-thu-muc.md)

## Tài liệu

- [Toàn trình dữ liệu](docs/reference/toan-trinh-du-lieu.md) — 10 bước từ nguồn tới màn hình
- [Mô tả database](docs/reference/mo-ta-database.md) — 18 bảng, 30 phép kiểm
- [Cây thư mục](docs/reference/cay-thu-muc.md)
- [API TLA Hợp Đồng](docs/reference/api-map-tla-hd.md)

---

## ⚠️ Phần dưới đây đã lỗi thời

Nội dung dưới mô tả cách làm việc **trước khi có database và backend**, khi dữ liệu
được gõ tay vào form và lưu trong `localStorage` của trình duyệt. Cách đó đã bị thay
thế hoàn toàn bởi đường ống dữ liệu. Giữ lại để đối chiếu, **không làm theo**.

<details>
<summary>Hướng dẫn cũ (nhập liệu tay)</summary>

**Nhập liệu theo ngày:** Bấm ✎ Dữ liệu nguồn → chọn Ngày nhập liệu → nhập
token/request cho từng agent → 💾 Lưu ngày này. Xoá một ngày: chọn ngày rồi 🗑 Xoá ngày.

**Cấu hình giá:** ⚙ Cấu hình giá → sửa đơn giá input/output theo model → 💾 Lưu bảng giá.

**Lưu ý cũ:** Dữ liệu nhập lưu trong `localStorage` của máy đang mở; gửi thư mục sang
máy khác thì máy đó bắt đầu từ dữ liệu Excel tháng 6 và tháng 7. Cây phòng ban và số
user Ralli chuẩn hoá từ `data/phong_ban_phan_quyen.xlsx` rồi nhúng vào `app.js`.

</details>

Hai thứ dưới đây thì **vẫn đúng**:

- **Khoảng thời gian** — ô "Từ → Đến" hoặc nút 7/30/90 ngày. Dashboard cộng mọi ngày
  nằm trong khoảng.
- **Giao diện sáng/tối** — nút ☀️ / 🌙 trên thanh công cụ.
