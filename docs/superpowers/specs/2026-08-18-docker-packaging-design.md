# Thiết kế đóng gói Docker cho Token Ledger Dashboard

**Ngày:** 18/08/2026  
**Phạm vi:** đóng gói ứng dụng để kiểm thử cục bộ trên Windows VM và chuẩn bị triển khai tại `https://dashboard.rangdong.com.vn:45501`.

## 1. Mục tiêu

Đóng gói hệ thống thành các container Linux có trách nhiệm tách biệt:

1. `gateway` phục vụ frontend tĩnh và reverse proxy `/api/*`.
2. `api` chạy FastAPI/Uvicorn và chỉ đọc PostgreSQL.
3. `postgres` lưu dữ liệu trong named volume bền vững.

Chỉ `gateway` được publish ra host. Mã nguồn, image và registry không được chứa database thật, dữ liệu nguồn, `.env`, certificate hay private key.

## 2. Bối cảnh và ràng buộc

- Máy đích là Windows 10 Pro 22H2 64-bit chạy trong VM.
- Nested virtualization và SLAT đã được bật; Docker Desktop sẽ chạy Linux containers qua WSL2.
- IP nội bộ của VM là `192.168.20.111`.
- Địa chỉ dự kiến sau triển khai là `https://dashboard.rangdong.com.vn:45501`.
- PostgreSQL phải là container riêng và dữ liệu phải tồn tại sau khi container/image được thay thế.
- Chỉ một cổng ứng dụng được mở; API, PostgreSQL và pgAdmin không được public.
- Certificate do công ty cấp và được mount lúc chạy, không được copy vào image.
- Ứng dụng chưa có đăng nhập. Cho tới khi có SSO/access gateway, endpoint production phải được giới hạn bằng mạng nội bộ, VPN hoặc allowlist của công ty; domain và TLS không thay thế xác thực.
- Dữ liệu thật hiện không có trong Git. `.gitignore` loại `data/*`, `*.sqlite`, `.env` và các file dữ liệu bảng tính.

DNS, NAT/firewall ngoài VM và việc cấp certificate thuộc phạm vi vận hành sau khi bộ container đã chạy cục bộ thành công.

## 3. Các phương án đã cân nhắc

### Phương án chọn: ba service `gateway` + `api` + `postgres`

Mỗi container có một tiến trình chính và một trách nhiệm rõ ràng. Frontend và reverse proxy cùng nằm trong Nginx vì đều là nhiệm vụ HTTP tĩnh/định tuyến. API và database có vòng đời độc lập. Đây là phương án ít thành phần nhất mà vẫn giữ đúng ranh giới vận hành.

### Không chọn: gộp Nginx và FastAPI vào một container

Phương án này cần supervisor hoặc script quản lý hai tiến trình. Việc restart, health check và đọc log trở nên khó hơn, trong khi chỉ giảm được một container nhỏ.

### Không chọn: IIS trên Windows làm gateway

IIS phục vụ được frontend và reverse proxy vào container API, nhưng làm bộ triển khai phụ thuộc vào cấu hình thủ công của Windows. Mục tiêu hiện tại là một bộ Compose có thể tái tạo nhất quán.

## 4. Kiến trúc container

```text
Trình duyệt
    |
    | local: http://127.0.0.1:8080
    | prod : https://dashboard.rangdong.com.vn:45501
    v
gateway (Nginx)
    |-- /                 -> /usr/share/nginx/html
    `-- /api/*            -> http://api:8000/api/*
                               |
                               v
                         api (FastAPI)
                               |
                               v
                         postgres:5432
                               |
                               v
                         named volume pgdata
```

### `gateway`

- Build từ image Nginx Alpine chính thức.
- Chỉ copy thư mục `web/` vào document root; không copy gốc repository.
- Reverse proxy `/api/` sang `api:8000` và giữ nguyên đường dẫn `/api/...`.
- Frontend dùng API cùng origin. `web/js/api.js` không còn mặc định gọi `http://127.0.0.1:8000` khi được phục vụ qua HTTP/HTTPS.
- Cấu hình local lắng nghe HTTP port 80 trong container.
- Cấu hình production lắng nghe HTTPS port 443, mount certificate và private key read-only.

### `api`

- Build từ Python 3.12 slim.
- Cài `backend/requirements.txt` trước khi copy mã nguồn để tận dụng Docker layer cache.
- Chứa `backend/`, `db/`, `scripts/copy_to_postgres.py` và `scripts/audit_db.py`. Hai script chỉ được gọi bởi service công cụ chạy một lần; chúng không tự chạy khi API khởi động.
- Chạy `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
- Không publish port 8000 ra Windows.
- Nhận `TOKEN_LEDGER_DSN` từ Compose, trỏ tới hostname service `postgres`, không trỏ `127.0.0.1`.
- Chạy bằng user không phải root trong container.

### `postgres`

- Dùng `postgres:17-alpine` như cấu hình hiện có.
- Không publish port 5432 ra Windows.
- Dùng named volume `pgdata:/var/lib/postgresql/data`.
- Tên database, user và password lấy từ `.env`; production không dùng mật khẩu mặc định `token_local`.
- Health check dùng `pg_isready`.
- `restart: unless-stopped`.

### Công cụ quản trị tùy chọn

pgAdmin được giữ lại trong Compose profile `tools`, không nằm trong luồng chạy mặc định, chỉ bind `127.0.0.1:5050` và không có mặt trên mạng public.

## 5. Compose và môi trường chạy

Ba file Compose tách trách nhiệm:

- `docker-compose.yml`: định nghĩa service, volume, network, health check; không publish cổng gateway.
- `docker-compose.local.yml`: publish `127.0.0.1:8080:80` để kiểm thử trên VM mà không lộ ra LAN.
- `docker-compose.prod.yml`: publish `45501:443`, mount cấu hình TLS và certificate read-only.

Lệnh local dự kiến:

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --build
```

Lệnh production dự kiến:

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Compose có hai mạng:

- `edge`: `gateway` và `api`.
- `data`: `api` và `postgres`, đặt `internal: true`.

Gateway không tham gia mạng `data`, vì vậy nó không thể kết nối trực tiếp PostgreSQL.

## 6. Dữ liệu và khởi tạo PostgreSQL

Named volume chỉ giữ dữ liệu; nó không tự tạo dữ liệu nghiệp vụ. Lần triển khai đầu cần file SQLite đã được dựng và audit trên máy có đủ dữ liệu nguồn.

Quy trình nhập lần đầu:

1. Khởi động `postgres` và đợi health check thành công.
2. Mount `var/token_ledger.sqlite` read-only vào một service chạy một lần tên `db-import`.
3. `db-import` chạy `scripts/copy_to_postgres.py`, kết nối tới `postgres:5432` và đối chiếu từng bảng.
4. Chạy `db-audit` với `scripts/audit_db.py` trên PostgreSQL.
5. Chỉ khởi động/đưa `api` vào phục vụ sau khi import và audit đạt yêu cầu.

`db-import` và `db-audit` dùng cùng image Python với `api`, thuộc Compose profile `tools`, không có restart policy và không chạy trong lệnh `up` thông thường.

`db-import` là thao tác phá hủy schema PostgreSQL đích trước khi chép lại. Nó không chạy tự động trong `docker compose up`; người vận hành phải gọi rõ ràng trong cửa sổ bảo trì. Với lần cập nhật dữ liệu sau, dừng `api`, chạy import + audit, rồi khởi động lại `api`.

Không mount toàn bộ `data/` vào container phục vụ web hoặc API. Pipeline thu thập dữ liệu bên ngoài phạm vi triển khai runtime.

## 7. Secrets và certificate

`.dockerignore` loại tối thiểu:

- `.git/`, `.env`, `.env.*` ngoại trừ file mẫu;
- `data/`, `var/`, `*.sqlite`, `*.db`;
- certificate và private key (`*.key`, `*.pfx`, `*.p12`, thư mục `secrets/`);
- cache Python, log, tài liệu/archive không cần cho runtime.

`.env.example` mô tả biến nhưng không có giá trị thật. Compose phải dừng với lỗi rõ ràng nếu thiếu `PGPASSWORD` ở cấu hình production. Mật khẩu dùng trong PostgreSQL URI phải là chuỗi URL-safe; hướng dẫn sinh chuỗi hex ngẫu nhiên để tránh lỗi escape.

TLS production hỗ trợ dạng PEM mà Nginx đọc trực tiếp:

- `fullchain.pem` hoặc certificate chain tương đương;
- `private.key`.

Nếu công ty cấp `.pfx/.p12`, người vận hành chuyển sang PEM ngoài repository. File được mount `:ro`; không build hoặc copy vào image.

## 8. Health check, khởi động và lỗi

- `postgres`: healthy khi `pg_isready` kết nối được đúng database/user.
- `api`: healthy khi `GET /api/health` trả 2xx và truy vấn được database.
- `gateway`: healthy khi document root trả HTTP 200.
- `api` phụ thuộc `postgres` healthy; `gateway` phụ thuộc `api` healthy trong luồng chạy đầy đủ.
- Ba service chạy lâu dài `gateway`, `api` và `postgres` dùng `restart: unless-stopped`; các service công cụ chạy một lần không tự restart.
- Log Nginx và Uvicorn đi ra stdout/stderr để xem bằng `docker compose logs`.

Nếu PostgreSQL không sẵn sàng, API không được coi là healthy. Nếu API hỏng sau khi gateway đã chạy, `/api/*` trả lỗi gateway thay vì mở cổng API khác. Frontend hiện vẫn có cơ chế fallback dữ liệu nhúng; vì vậy nghiệm thu bắt buộc phải kiểm tra trực tiếp `/api/health`, không chỉ nhìn dashboard có hiển thị số.

## 9. Backup và khôi phục

Named volume bảo vệ dữ liệu khi container bị thay thế hoặc khi chạy `docker compose down`, nhưng không phải là backup.

Backup PostgreSQL dùng `pg_dump -Fc` chạy trong container rồi `docker compose cp` file dump ra thư mục backup ngoài repository. Khôi phục dùng một database trống và `pg_restore`. Hướng dẫn vận hành ghi rõ:

- không dùng `docker compose down -v` trên production;
- luôn tạo dump trước import dữ liệu mới hoặc nâng phiên bản PostgreSQL;
- thử restore định kỳ, vì file backup chưa được thử restore chưa được coi là backup hợp lệ.

## 10. Tập tin dự kiến thay đổi

- Thêm `.dockerignore`.
- Thêm Dockerfile cho `gateway` và `api` trong `docker/`.
- Thêm cấu hình Nginx local và production trong `docker/`.
- Mở rộng `docker-compose.yml` từ PostgreSQL/pgAdmin thành stack runtime.
- Thêm `docker-compose.local.yml` và `docker-compose.prod.yml`.
- Cập nhật `.env.example` cho biến runtime/TLS cần thiết.
- Sửa `web/js/api.js` để dùng same-origin API khi chạy qua gateway.
- Cập nhật `README.md` với quy trình build, import, local test, production run, backup và xử lý lỗi.
- Thêm `tests/docker-smoke.ps1` để kiểm tra frontend, API health và các cổng không được publish; không thay đổi logic nghiệp vụ dashboard.

## 11. Nghiệm thu

### Cấu hình và image

- `docker compose ... config` hợp lệ cho cả local và production.
- Cả hai image build thành công từ checkout sạch.
- Image không chứa `.env`, SQLite, dữ liệu nguồn, certificate hoặc private key.
- API container chạy bằng user không phải root.

### Chạy local

- `http://127.0.0.1:8080/` trả frontend.
- `http://127.0.0.1:8080/api/health` trả JSON từ PostgreSQL.
- Windows không lắng nghe trực tiếp port 8000, 5432 hoặc 5050.
- Trình duyệt gọi `/api/*` cùng origin; không gọi `127.0.0.1:8000`.

### Dữ liệu bền vững

- Import SQLite sang PostgreSQL khớp từng bảng và audit không có lỗi chặn.
- Ghi nhận số dòng chuẩn, chạy `docker compose down` rồi `up -d`, số dòng không đổi.
- Thay image/container không làm mất named volume.

### Production

- Chỉ host port 45501 được publish tới gateway port 443.
- Certificate được mount read-only và hợp lệ cho `dashboard.rangdong.com.vn`.
- `https://dashboard.rangdong.com.vn:45501/` và `/api/health` hoạt động sau khi DNS/NAT/firewall hoàn tất.
- Không thể truy cập API/PostgreSQL/pgAdmin trực tiếp từ máy khác.
- Khi chưa có SSO/access gateway, firewall/VPN/allowlist chặn người ngoài phạm vi công ty dù họ biết URL.

## 12. Ngoài phạm vi

- Cấp DNS, NAT/firewall tại hạ tầng công ty và phát hành certificate.
- Xây dựng registry/CI/CD; lần đầu cho phép build image trực tiếp trên VM.
- Tự động hóa pipeline thu thập dữ liệu GCP/Ralli/TLA Hợp Đồng trên server production.
- Thay đổi giao diện, chỉ số hoặc logic nghiệp vụ của dashboard.
- Bổ sung hệ thống đăng nhập/SSO; đây là một thay đổi bảo mật riêng cần thiết kế riêng trước khi mở cho phạm vi người dùng rộng.
