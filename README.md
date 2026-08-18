# Agent Analytics · Token Ledger

Bảng điều khiển chi phí AI agent. Dữ liệu lấy từ hoá đơn Google Cloud, Cloud Monitoring
và hai web app nội bộ, gom vào một database rồi hiển thị qua API chỉ-đọc.

## Cách chạy

```bash
# 1. Backend chỉ-đọc — phục vụ dữ liệu từ database
python -m uvicorn backend.main:app --port 8000

# 2. Dashboard — LƯU Ý cả hai vế của lệnh này đều cần thiết
cd web && python -m http.server 8080 --bind 127.0.0.1
```

Mở `http://127.0.0.1:8080`.

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

## Triển khai bằng Docker

Phần này dành cho máy ảo Windows chạy dashboard trong mạng nội bộ. Dashboard hiện chưa có đăng nhập hoặc SSO, vì vậy không được công khai trực tiếp ra Internet.

### Điều kiện máy và cài Docker Desktop

Máy cần Windows 10 Pro 22H2 x64, đã bật ảo hóa phần cứng và SLAT, có WSL2 để chạy Linux containers, Docker Desktop kèm Docker Compose v2, và có phê duyệt/licensing của công ty. Cài đặt theo tài khoản người dùng là đủ, trừ khi quản trị viên yêu cầu quản lý cho mọi người dùng. Trong trình cài đặt Docker Desktop, bật `Use the WSL 2 based engine`; không chọn hoặc chuyển sang Windows Containers.

Sau khi cài, mở Windows PowerShell và kiểm tra:

```powershell
wsl --update
docker version
docker info --format 'Server={{.ServerVersion}}; OS={{.OSType}}; Arch={{.Architecture}}'
```

Docker server phải báo `OS=linux`; trên VM x64 này thông thường sẽ là `Arch=x86_64`.

### Chuẩn bị môi trường và nạp dữ liệu lần đầu

Tại thư mục checkout của dự án, tạo `.env` từ mẫu, sinh rồi điền cả hai mật khẩu còn trống, kiểm tra `SQLITE_SOURCE`, và tuyệt đối không commit `.env`. Giá trị mặc định Git-ignored `./var/token_ledger.sqlite` được phép dùng, nhưng phải luôn nằm ngoài Git và Docker image; nếu chính sách công ty yêu cầu, có thể đặt `SQLITE_SOURCE` thành một đường dẫn tuyệt đối bên ngoài checkout đã được phê duyệt:

```powershell
Copy-Item .env.example .env
notepad .env
docker compose -f docker-compose.yml -f docker-compose.local.yml config
docker compose up -d postgres
docker compose --profile tools run --rm db-import
docker compose --profile tools run --rm db-audit
```

`db-import` đọc SQLite qua bind mount chỉ-đọc, nhưng nó **xóa và tạo lại PostgreSQL schema `public`**. Đây là thao tác bảo trì chủ động, không phải bước khởi động thường lệ. Với lần import sau: sao lưu trước, dừng API/gateway, import, audit, rồi khởi động lại.

### Chạy cục bộ, smoke test và log

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
powershell -ExecutionPolicy Bypass -File tests/docker-smoke.ps1
docker compose -f docker-compose.yml -f docker-compose.local.yml ps
docker compose -f docker-compose.yml -f docker-compose.local.yml logs --tail 200 gateway api postgres
```

Mở dashboard cục bộ tại `http://127.0.0.1:8080`. Smoke test kiểm tra trang gốc, `/api/health`, trạng thái/health của `gateway`, `api`, `postgres`, và xác nhận API/Postgres không có cổng host công khai. `pgAdmin` không là điều kiện smoke vì thuộc profile `tools` tùy chọn và khi bật chỉ bind loopback.

### Sao lưu và phục hồi ngoài repository

Named volume giúp dữ liệu tồn tại qua việc thay container, nhưng **không phải bản sao lưu**. Lưu backup tại một đường dẫn được phê duyệt ở ngoài checkout, ví dụ:

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = 'C:\token-ledger-backups'
New-Item -ItemType Directory -Force $backupDir | Out-Null
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/token-ledger.dump'
if ($LASTEXITCODE -ne 0) { throw 'Backup failed: pg_dump in postgres container.' }
$backupFile = Join-Path $backupDir "token-ledger-$stamp.dump"
docker compose cp postgres:/tmp/token-ledger.dump $backupFile
if ($LASTEXITCODE -ne 0) { throw 'Backup failed: could not copy dump from postgres container.' }
docker compose exec -T postgres rm -f /tmp/token-ledger.dump
if ($LASTEXITCODE -ne 0) { throw 'Backup failed: could not remove temporary dump from postgres container.' }
```

Phục hồi cũng là bảo trì chủ động:

```powershell
$backupFile = 'C:\token-ledger-backups\token-ledger-YYYYMMDD-HHMMSS.dump'
docker compose stop gateway api
if ($LASTEXITCODE -ne 0) { throw 'Restore failed: could not stop gateway and api.' }
docker compose cp $backupFile postgres:/tmp/restore.dump
if ($LASTEXITCODE -ne 0) { throw 'Restore failed: could not copy backup into postgres container.' }
docker compose exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/restore.dump'
if ($LASTEXITCODE -ne 0) { throw 'Restore failed: pg_restore in postgres container.' }
docker compose exec -T postgres rm -f /tmp/restore.dump
if ($LASTEXITCODE -ne 0) { throw 'Restore failed: could not remove temporary restore dump from postgres container.' }
docker compose --profile tools run --rm db-audit
if ($LASTEXITCODE -ne 0) { throw 'Restore failed: database audit did not pass.' }
docker compose start api gateway
if ($LASTEXITCODE -ne 0) { throw 'Restore failed: could not restart gateway and api.' }
```

Luôn thử phục hồi định kỳ để xác nhận backup sử dụng được.

### Production: TLS, domain và mạng

URL production là `https://dashboard.rangdong.com.vn:45501`. Quản trị viên phải ánh xạ DNS nội bộ tới VM `192.168.20.111` và chỉ cho phép TCP `45501` từ mạng công ty/VPN/allowlist đã duyệt. Domain và TLS không thay thế xác thực; vì ứng dụng chưa có login/SSO, không được phơi trực tiếp ra Internet công cộng.

Nginx cần PEM full chain và **PEM private key không mã hóa** tại các đường dẫn khai báo trong `.env`. Nếu công ty chỉ cung cấp `.pfx`/`.p12`, hãy phối hợp chuyển đổi bảo mật ở ngoài repository; bảo vệ mật khẩu của file nguồn/export và private key đã trích xuất bằng NTFS access control phù hợp. Certificate/private key không bao giờ được đưa vào Git hoặc Docker image: `.env` chỉ chứa đường dẫn và secret values, còn các byte certificate/private key nằm ngoài Git/image.

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
curl.exe -k https://dashboard.rangdong.com.vn:45501/api/health
```

`-k` chỉ là chẩn đoán kết nối tạm thời trước khi corporate trust chain được cài. Trình duyệt/API sử dụng bình thường phải kiểm tra TLS thành công, không được bỏ qua certificate validation.

### An toàn và xử lý sự cố

- `docker compose down` xóa containers nhưng giữ named volumes.
- Không bao giờ chạy `docker compose down -v` trừ khi chủ đích xóa vĩnh viễn database và đã có bản phục hồi được thử nghiệm.
- Đổi mật khẩu trong `.env` không đổi mật khẩu của Postgres volume đã khởi tạo. Dùng quy trình xoay vòng mật khẩu có chủ đích; không xóa volume để làm đường tắt.
- Dùng `docker compose logs --tail 200 gateway api postgres` để chẩn đoán.
- Certificate paths và secret values ở `.env`; byte certificate/private key phải ở ngoài Git/image.

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
