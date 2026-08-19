# Kế hoạch đóng gói và triển khai trên Windows VM

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tạo gói source sạch từ commit Docker đã review, build Linux images trực tiếp trên Windows VM, nạp dữ liệu vào PostgreSQL volume riêng, nghiệm thu local, rồi bật TLS tại `https://dashboard.rangdong.com.vn:45501`.

**Architecture:** Windows VM chạy Docker Desktop với WSL2 Linux containers. Nginx là cổng duy nhất ra host; FastAPI và PostgreSQL chỉ giao tiếp qua mạng Compose, còn dữ liệu PostgreSQL nằm trong named volume `pgdata`. Source, SQLite, `.env`, certificate và private key đi theo các kênh riêng; chỉ source được dùng làm build context.

**Tech Stack:** Windows 10 Pro 22H2 x64, WSL2, Docker Desktop, Docker Compose v2, Nginx Alpine, Python 3.12 slim, FastAPI/Uvicorn, PostgreSQL 17 Alpine, PowerShell.

**Spec:** `docs/superpowers/specs/2026-08-18-docker-packaging-design.md`

## Global Constraints

- Source phát hành cố định tại commit `1bb0280` trên nhánh `feature/docker-packaging`.
- Docker server trên VM phải báo `OS=linux`; kiến trúc của VM này phải báo `Arch=x86_64`.
- Chỉ `gateway` được publish: local là `127.0.0.1:8080`, production là TCP `45501` tới container port `443`.
- API port `8000`, PostgreSQL port `5432` và pgAdmin port `5050` không được public ra LAN.
- PostgreSQL chạy container riêng và dùng named volume `pgdata`; không build database vào image ứng dụng.
- `.env`, SQLite, dữ liệu nguồn, certificate và private key không được đưa vào Git, source ZIP hoặc Docker image.
- `PGUSER` và `API_PGUSER` phải khác nhau; `PGPASSWORD` và `API_PGPASSWORD` phải khác nhau.
- Không chạy `docker compose down -v` trên stack thật.
- Production chỉ được mở cho mạng công ty, VPN hoặc allowlist đã duyệt vì ứng dụng chưa có login/SSO.

## Bản đồ artefact

| Artefact | Trách nhiệm | Cách chuyển lên VM |
|---|---|---|
| `token-ledger-dashboard-1bb0280.zip` | Source sạch để build | Git archive, kèm SHA-256 |
| `token_ledger.sqlite` | Dữ liệu nguồn cho lần import đầu | Kênh truyền dữ liệu nội bộ được duyệt |
| `.env` | Tài khoản, mật khẩu và đường dẫn runtime | Tạo trực tiếp trên VM từ `.env.example` |
| `fullchain.pem`, `private.key` | TLS production | Quản trị viên đặt ngoài checkout, ACL NTFS hạn chế |
| `token-ledger-api:local` | API và các công cụ import/audit | Build trực tiếp trên VM |
| `token-ledger-gateway:local` | Frontend và reverse proxy Nginx | Build trực tiếp trên VM |
| `token-ledger_pgdata` | Dữ liệu PostgreSQL bền vững | Docker tạo trên VM; không sao chép bằng ZIP |

## Luồng tổng thể

```text
Commit 1bb0280
  -> source ZIP + SHA-256
  -> chuyển ZIP và SQLite riêng lên VM
  -> Docker Linux/x86_64 đạt yêu cầu
  -> tạo .env và kiểm tra Compose
  -> build api + gateway
  -> tạo PostgreSQL volume
  -> import SQLite -> cấp quyền reader -> audit
  -> chạy local + smoke + kiểm tra persistence
  -> backup và thử restore
  -> nhận certificate + DNS/firewall 45501
  -> chạy production + smoke TLS
  -> bàn giao vận hành
```

---

### Task 1: Tạo gói source sạch

**Files:**
- Read: toàn bộ file được Git theo dõi tại commit `1bb0280`
- Create outside checkout: `C:\token-ledger-dashboard\token-ledger-dashboard-1bb0280.zip`
- Create outside checkout: bản ghi SHA-256 từ PowerShell

**Interfaces:**
- Consumes: commit đã review `1bb0280`
- Produces: source ZIP không chứa `.git`, `.env`, SQLite, certificate hoặc private key

- [ ] **Step 1: Xác nhận commit phát hành tồn tại và worktree sạch**

```powershell
Set-Location C:\token-ledger-dashboard\.worktrees\docker-packaging
git show -s --format='%h %s' 1bb0280
git status --short
```

Expected: dòng đầu bắt đầu bằng `1bb0280 fix: make reader grants and clean restores safe`; `git status --short` không in file thay đổi. ZIP luôn lấy từ commit cố định này nên tài liệu kế hoạch được commit sau đó không đi vào gói runtime.

- [ ] **Step 2: Tạo ZIP chỉ từ file được Git theo dõi**

```powershell
git archive --format=zip --prefix=token-ledger-dashboard/ --output C:\token-ledger-dashboard\token-ledger-dashboard-1bb0280.zip 1bb0280
```

Expected: lệnh exit `0`; ZIP được tạo ngoài checkout.

- [ ] **Step 3: Ghi checksum bàn giao**

```powershell
Get-FileHash C:\token-ledger-dashboard\token-ledger-dashboard-1bb0280.zip -Algorithm SHA256
```

Expected: lưu lại chuỗi SHA-256 cùng biên bản chuyển file.

- [ ] **Step 4: Kiểm tra gói không chứa secret/data**

```powershell
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead('C:\token-ledger-dashboard\token-ledger-dashboard-1bb0280.zip')
try {
    $forbidden = @($zip.Entries | Where-Object {
        $_.FullName -match '(^|/)(\.env|data|var|secrets)(/|$)' -or
        $_.FullName -match '\.(sqlite|sqlite3|db|key|pfx|p12)$'
    })
    if ($forbidden.Count -gt 0) { throw "Forbidden entries: $($forbidden.FullName -join ', ')" }
} finally {
    $zip.Dispose()
}
```

Expected: không có exception.

### Task 2: Chuẩn bị Windows VM và nhận source

**Files:**
- Create: `C:\Users\RAL-DASHBOARD\deploy\token-ledger-dashboard\`
- Read: source ZIP và SHA-256 từ Task 1

**Interfaces:**
- Consumes: source ZIP sạch
- Produces: checkout phát hành trên VM và Docker Linux engine sẵn sàng

- [ ] **Step 1: Xác minh WSL2 và Docker Desktop**

```powershell
wsl --status
wsl --update
docker version
docker compose version
docker info --format "Server={{.ServerVersion}}; OS={{.OSType}}; Arch={{.Architecture}}"
```

Expected: Docker client kết nối được server; server báo `OS=linux` và `Arch=x86_64`. Dừng kế hoạch nếu Docker báo Windows containers hoặc không kết nối được engine.

- [ ] **Step 2: Kiểm tra checksum ZIP sau khi chuyển vào Downloads**

```powershell
Get-FileHash C:\Users\RAL-DASHBOARD\Downloads\token-ledger-dashboard-1bb0280.zip -Algorithm SHA256
```

Expected: SHA-256 trùng hoàn toàn với kết quả Task 1.

- [ ] **Step 3: Giải nén vào thư mục mới**

```powershell
$deployRoot = 'C:\Users\RAL-DASHBOARD\deploy'
$deployPath = Join-Path $deployRoot 'token-ledger-dashboard'
New-Item -ItemType Directory -Force $deployRoot | Out-Null
if (Test-Path $deployPath) { throw "Deployment directory already exists: $deployPath" }
Expand-Archive C:\Users\RAL-DASHBOARD\Downloads\token-ledger-dashboard-1bb0280.zip -DestinationPath $deployRoot
Set-Location $deployPath
Get-Item docker-compose.yml, docker-compose.local.yml, docker-compose.prod.yml, .env.example
```

Expected: bốn file bắt buộc tồn tại.

### Task 3: Đặt dữ liệu nguồn và tạo cấu hình runtime

**Files:**
- Create outside checkout: `C:\Users\RAL-DASHBOARD\deploy-data\token_ledger.sqlite`
- Create on VM: `.env` từ `.env.example`
- Never commit: `.env`, `token_ledger.sqlite`

**Interfaces:**
- Consumes: SQLite đã được audit và ba mật khẩu riêng
- Produces: Compose environment hợp lệ cho local và production

- [ ] **Step 1: Đặt SQLite ngoài checkout**

```powershell
New-Item -ItemType Directory -Force C:\Users\RAL-DASHBOARD\deploy-data | Out-Null
Copy-Item C:\Users\RAL-DASHBOARD\Downloads\token_ledger.sqlite C:\Users\RAL-DASHBOARD\deploy-data\token_ledger.sqlite
Get-Item C:\Users\RAL-DASHBOARD\deploy-data\token_ledger.sqlite
```

Expected: file tồn tại và kích thước lớn hơn `0` byte. Dừng nếu chưa có file SQLite nguồn.

- [ ] **Step 2: Tạo ba secret URL-safe khác nhau**

```powershell
function New-TokenLedgerSecret {
    $bytes = New-Object byte[] 16
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    -join ($bytes | ForEach-Object { $_.ToString('x2') })
}
1..3 | ForEach-Object { New-TokenLedgerSecret }
```

Expected: ba chuỗi hex, mỗi chuỗi 32 ký tự và không chuỗi nào trùng nhau.

- [ ] **Step 3: Tạo `.env` và điền cấu hình**

```powershell
Set-Location C:\Users\RAL-DASHBOARD\deploy\token-ledger-dashboard
Copy-Item .env.example .env
notepad .env
```

Giữ `PGUSER=token`, giữ `API_PGUSER=token_reader`, điền ba secret khác nhau vào `PGPASSWORD`, `API_PGPASSWORD`, `PGADMIN_PASSWORD`, và đặt:

```dotenv
SQLITE_SOURCE=C:/Users/RAL-DASHBOARD/deploy-data/token_ledger.sqlite
LOCAL_PORT=8080
PUBLIC_PORT=45501
TLS_CERT_FILE=C:/certs/dashboard/fullchain.pem
TLS_KEY_FILE=C:/certs/dashboard/private.key
APP_TAG=local
```

- [ ] **Step 4: Render cấu hình local**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Local Compose configuration is invalid.' }
```

Expected: exit `0` và không in secret ra biên bản/log chia sẻ.

### Task 4: Build và kiểm tra images trên VM

**Files:**
- Build input: `docker/api.Dockerfile`, `docker/gateway.Dockerfile`, `.dockerignore`
- Produce: `token-ledger-api:local`, `token-ledger-gateway:local`

**Interfaces:**
- Consumes: source sạch và Docker Linux/x86_64
- Produces: hai image ứng dụng đã build; PostgreSQL vẫn là image/service riêng

- [ ] **Step 1: Build hai image**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml build
if ($LASTEXITCODE -ne 0) { throw 'Docker image build failed.' }
```

Expected: cả `api` và `gateway` build thành công.

- [ ] **Step 2: Kiểm tra image OS, architecture và user API**

```powershell
docker image inspect token-ledger-api:local --format '{{.Os}}/{{.Architecture}} User={{.Config.User}}'
docker image inspect token-ledger-gateway:local --format '{{.Os}}/{{.Architecture}} User={{.Config.User}}'
```

Expected: cả hai là `linux/amd64`; API có user không phải `root` và không rỗng.

- [ ] **Step 3: Kiểm tra image không chứa dữ liệu/secret**

```powershell
docker run --rm --entrypoint python token-ledger-api:local -c "import os; banned={'.git','.env','token_ledger.sqlite','fullchain.pem','private.key'}; found=[]; [found.append(os.path.join(r,n)) for r,ds,fs in os.walk('/') for n in ds+fs if n in banned]; print(found); raise SystemExit(bool(found))"
```

Expected: in `[]` và exit `0`.

### Task 5: Khởi tạo PostgreSQL và nạp dữ liệu lần đầu

**Files:**
- Read-only mount: `C:\Users\RAL-DASHBOARD\deploy-data\token_ledger.sqlite`
- Read-only mount: `docker/read-only-api.sql`
- Create: Docker named volume `token-ledger_pgdata`

**Interfaces:**
- Consumes: SQLite nguồn, image API, admin/reader credentials
- Produces: PostgreSQL đã import, reader chỉ-đọc và audit đạt

- [ ] **Step 1: Khởi động riêng PostgreSQL và chờ healthy**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --wait postgres
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not become healthy.' }
```

- [ ] **Step 2: Import SQLite vào PostgreSQL**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml --profile tools run --rm db-import
if ($LASTEXITCODE -ne 0) { throw 'Initial SQLite import failed.' }
```

Expected: script đối chiếu dữ liệu thành công. Không chạy lại bước này trên DB đang phục vụ nếu chưa backup và mở cửa sổ bảo trì.

- [ ] **Step 3: Tạo/cập nhật reader role**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml --profile tools run --rm db-grant
if ($LASTEXITCODE -ne 0) { throw 'Read-only grant migration failed.' }
```

- [ ] **Step 4: Audit bằng reader DSN**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml --profile tools run --rm db-audit
if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL audit failed.' }
```

Expected: audit không có lỗi chặn trước khi API được khởi động.

### Task 6: Nghiệm thu local và độ bền volume

**Files:**
- Execute: `tests/docker-smoke.ps1`
- Preserve: named volume `token-ledger_pgdata`

**Interfaces:**
- Consumes: DB đã audit và hai image ứng dụng
- Produces: bằng chứng local smoke và persistence đạt

- [ ] **Step 1: Khởi động stack local mà không build lại**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --wait --no-build
if ($LASTEXITCODE -ne 0) { throw 'Local stack did not become healthy.' }
```

- [ ] **Step 2: Chạy smoke test**

```powershell
powershell -ExecutionPolicy Bypass -File tests/docker-smoke.ps1
if ($LASTEXITCODE -ne 0) { throw 'Local smoke test failed.' }
```

Expected: `/`, `/api/health`, health của ba service và ranh giới host port đều đạt. Kiểm tra trình duyệt tại `http://127.0.0.1:8080`.

- [ ] **Step 3: Kiểm tra volume sống qua thay container**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml down
docker compose -f docker-compose.yml -f docker-compose.local.yml up -d --wait --no-build
docker compose -f docker-compose.yml -f docker-compose.local.yml --profile tools run --rm db-audit
```

Expected: audit vẫn đạt sau `down`/`up`; không dùng tùy chọn `-v`.

### Task 7: Backup và thử restore cô lập

**Files:**
- Create outside checkout: `C:\token-ledger-backups\token-ledger-<timestamp>.dump`
- Create for restore test: Compose project `token-ledger-restore-test`

**Interfaces:**
- Consumes: PostgreSQL đã nghiệm thu
- Produces: dump không chứa ACL cũ và bằng chứng restore vào volume mới

- [ ] **Step 1: Tạo custom-format dump ngoài repository**

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupDir = 'C:\token-ledger-backups'
New-Item -ItemType Directory -Force $backupDir | Out-Null
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-acl -f /tmp/token-ledger.dump'
if ($LASTEXITCODE -ne 0) { throw 'Backup failed inside postgres container.' }
$backupFile = Join-Path $backupDir "token-ledger-$stamp.dump"
docker compose cp postgres:/tmp/token-ledger.dump $backupFile
if ($LASTEXITCODE -ne 0) { throw 'Backup copy failed.' }
docker compose exec -T postgres rm -f /tmp/token-ledger.dump
Get-FileHash $backupFile -Algorithm SHA256
```

Expected: dump tồn tại ngoài checkout, có kích thước lớn hơn `0`, và có SHA-256 lưu trong biên bản.

- [ ] **Step 2: Khởi tạo PostgreSQL restore-test bằng project riêng**

```powershell
$backupFile = Get-ChildItem C:\token-ledger-backups\token-ledger-*.dump |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 -ExpandProperty FullName
if ([string]::IsNullOrWhiteSpace($backupFile)) { throw 'No PostgreSQL backup was found.' }
docker compose -p token-ledger-restore-test -f docker-compose.yml -f docker-compose.local.yml up -d --wait postgres
docker compose -p token-ledger-restore-test -f docker-compose.yml -f docker-compose.local.yml cp $backupFile postgres:/tmp/restore.dump
```

- [ ] **Step 3: Restore không phục hồi ACL cũ rồi cấp lại reader**

```powershell
docker compose -p token-ledger-restore-test -f docker-compose.yml -f docker-compose.local.yml exec -T postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-acl /tmp/restore.dump'
if ($LASTEXITCODE -ne 0) { throw 'Isolated restore failed.' }
docker compose -p token-ledger-restore-test -f docker-compose.yml -f docker-compose.local.yml --profile tools run --rm db-grant
docker compose -p token-ledger-restore-test -f docker-compose.yml -f docker-compose.local.yml --profile tools run --rm db-audit
```

Expected: restore, grant và audit đều exit `0`. Dừng project thử bằng lệnh dưới; volume thử được giữ lại để quản trị viên xóa có chủ đích sau khi đối chiếu đúng project name.

```powershell
docker compose -p token-ledger-restore-test -f docker-compose.yml -f docker-compose.local.yml down
```

### Task 8: Chuẩn bị TLS, DNS và firewall production

**Files:**
- Create outside checkout: `C:\certs\dashboard\fullchain.pem`
- Create outside checkout: `C:\certs\dashboard\private.key`
- Modify only on VM: `.env`

**Interfaces:**
- Consumes: certificate PEM do công ty cấp và thay đổi hạ tầng của quản trị viên
- Produces: production Compose render hợp lệ

- [ ] **Step 1: Quản trị viên cấu hình hạ tầng**

Yêu cầu chính xác gửi quản trị viên:

```text
DNS nội bộ: dashboard.rangdong.com.vn -> 192.168.20.111
Firewall/NAT: cho phép TCP 45501 tới VM, chỉ từ mạng công ty/VPN/allowlist
Certificate: SAN/CN chứa dashboard.rangdong.com.vn
Định dạng runtime: fullchain.pem + private.key PEM không mã hóa
```

- [ ] **Step 2: Đặt certificate ngoài checkout và kiểm tra sự tồn tại**

```powershell
Test-Path C:\certs\dashboard\fullchain.pem
Test-Path C:\certs\dashboard\private.key
Resolve-DnsName dashboard.rangdong.com.vn
```

Expected: hai kết quả `True`; DNS nội bộ trả IP `192.168.20.111`. Không in nội dung private key ra terminal/log.

- [ ] **Step 3: Render production Compose**

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Production Compose configuration is invalid.' }
```

### Task 9: Bật production và bàn giao

**Files:**
- Execute: `docker-compose.yml`, `docker-compose.prod.yml`, `tests/docker-smoke.ps1`
- Preserve: `.env`, TLS files, named volume và backup ngoài checkout

**Interfaces:**
- Consumes: local acceptance, restore-test, TLS/DNS/firewall
- Produces: production healthy tại domain công ty và bộ bằng chứng vận hành

- [ ] **Step 1: Dừng gateway local rồi chạy production**

```powershell
docker compose -f docker-compose.yml -f docker-compose.local.yml down
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --wait --no-build
if ($LASTEXITCODE -ne 0) { throw 'Production stack did not become healthy.' }
```

- [ ] **Step 2: Smoke test qua TLS/domain**

```powershell
powershell -ExecutionPolicy Bypass -File tests/docker-smoke.ps1 -BaseUrl 'https://dashboard.rangdong.com.vn:45501' -ComposeOverride 'docker-compose.prod.yml'
if ($LASTEXITCODE -ne 0) { throw 'Production smoke test failed.' }
```

- [ ] **Step 3: Kiểm tra service, host port và log**

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail 200 gateway api postgres
```

Expected: `gateway`, `api`, `postgres` đều running/healthy; chỉ gateway publish `0.0.0.0:45501->443/tcp`; log không chứa lỗi TLS, kết nối DB hoặc health check.

- [ ] **Step 4: Ghi biên bản bàn giao**

Biên bản phải ghi commit `1bb0280`, SHA-256 source ZIP, SHA-256 backup, thời điểm build, kết quả local smoke, restore-test, production smoke, đường dẫn backup, người giữ certificate và chính sách khởi động Docker Desktop sau khi VM reboot. Không ghi password hoặc private key vào biên bản.

## Cổng nghiệm thu cuối

- [ ] Source ZIP khớp SHA-256 và không chứa data/secret.
- [ ] Docker server là `linux/x86_64`.
- [ ] Hai image build thành công; API không chạy root.
- [ ] SQLite import, `db-grant` và `db-audit` đều đạt.
- [ ] Local smoke và kiểm tra persistence đều đạt.
- [ ] Backup có SHA-256 và restore-test trên volume mới đạt.
- [ ] Certificate nằm ngoài checkout/image và DNS đúng `192.168.20.111`.
- [ ] Production chỉ publish TCP `45501`; API/PostgreSQL không có host binding.
- [ ] `https://dashboard.rangdong.com.vn:45501/` và `/api/health` đạt.
- [ ] Quy trình reboot/auto-start của Docker Desktop đã được quản trị viên xác nhận.
