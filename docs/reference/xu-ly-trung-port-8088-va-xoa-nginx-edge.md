# Xử lý trùng port 8088 và xóa Nginx Edge cũ

## Hiện tượng

Khi chuyển cổng đầu vào `8088` từ `token-ledger-gateway-edge` sang
`token-ledger-gateway-lb`, Docker có thể báo:

```text
failed to set up container networking:
Bind for 127.0.0.1:8088 failed: port is already allocated
```

Lệnh kiểm tra:

```powershell
docker ps --filter "publish=8088" --format "table {{.Names}}\t{{.Ports}}"
```

Nếu kết quả là:

```text
token-ledger-gateway-edge   127.0.0.1:8088->8080/tcp
```

thì Edge cũ vẫn đang giữ port `8088`.

## Nguyên nhân

Edge đã được xóa khỏi mã nguồn và `docker-compose.yml`, nhưng `git pull` chỉ cập
nhật file. Nó không tự dừng hoặc xóa container đã được tạo từ phiên bản Compose
cũ. Không nên dùng `docker compose down` hoặc `--remove-orphans` để xử lý vì root
Compose dùng chung với Dashboard, PostgreSQL, pgAdmin và các volume dữ liệu.

## Quy trình chuyển port an toàn

Chạy trong PowerShell tại `C:\token-ledger-dashboard`.

### 1. Xác nhận đúng container đang giữ port

```powershell
docker ps --filter "publish=8088" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

Chỉ tiếp tục nếu container giữ port là `token-ledger-gateway-edge`. Nếu là tên
khác, dừng lại và điều tra; không dừng container không xác định.

### 2. Kiểm tra cấu hình mới

```powershell
docker compose --profile gateway config --quiet
if ($LASTEXITCODE -ne 0) { throw "Compose configuration is invalid" }
```

### 3. Dừng riêng Edge cũ để giải phóng port

```powershell
docker stop token-ledger-gateway-edge
if ($LASTEXITCODE -ne 0) { throw "Cannot stop the old Edge container" }
```

Chưa cần xóa container ở bước này. Giữ nó ở trạng thái stopped giúp điều tra hoặc
rollback nếu LB mới không khởi động.

### 4. Build và recreate riêng LB

Bản một-container chứa cả Nginx LB và Web Status nên phải build image mới:

```powershell
docker compose build gateway-lb
if ($LASTEXITCODE -ne 0) { throw "Gateway LB image build failed" }

docker compose --profile gateway up -d --no-deps --force-recreate --wait --wait-timeout 60 gateway-lb
if ($LASTEXITCODE -ne 0) { throw "Gateway LB recreation failed" }
```

`--no-deps` tránh recreate LiteLLM, Redis và các dịch vụ Dashboard.

### 5. Xác minh LB đã nhận port và vào đúng network

```powershell
docker inspect token-ledger-gateway-lb --format 'State={{.State.Status}} Health={{.State.Health.Status}} Networks={{json .NetworkSettings.Networks}}'
docker port token-ledger-gateway-lb

curl.exe --noproxy "*" --fail --max-time 10 `
  -H "Host: apigateway.rangdong.com.vn" `
  http://127.0.0.1:8088/lb-health
```

Kết quả mong đợi:

```text
4000/tcp -> 127.0.0.1:8088
lb-ok
```

`Networks` phải chứa `token-ledger-dashboard_default`; không được là `{}`.

Kiểm tra web và collector nội bộ:

```powershell
curl.exe --noproxy "*" -i --max-time 10 `
  -H "Host: apigateway.rangdong.com.vn" `
  http://127.0.0.1:8088/

docker compose --profile gateway exec -T gateway-lb `
  wget -q -O- --header "Host: localhost" http://127.0.0.1:8089/api/status
```

Web `/` có thể trả `403` nếu TCP peer chưa nằm trong ACL quản trị. Điều đó khác
với lỗi kết nối hoặc container không chạy.

### 6. Chỉ xóa Edge sau khi LB mới đã được xác minh

```powershell
docker rm token-ledger-gateway-edge
```

Lệnh này chỉ xóa container Edge đã dừng; không xóa image, network, volume hoặc dữ
liệu Dashboard.

## Trạng thái mạng dở dang

Nếu Docker báo LB `running` nhưng:

```text
Ports={"4000/tcp":[]}
Networks={}
```

thì lần tạo container trước đã để lại trạng thái networking chưa hoàn chỉnh. Chỉ
recreate riêng LB:

```powershell
docker compose --profile gateway up -d --no-deps --force-recreate --wait --wait-timeout 60 gateway-lb
```

Sau đó kiểm tra lại `docker inspect`, `docker port` và `/lb-health`. Không xóa
network dùng chung để sửa lỗi này.

## Luồng sau khi chuyển đổi

```text
Reverse proxy hạ tầng :443
  -> VM :8088
     -> token-ledger-gateway-lb (Nginx + Node Status)
        /                              -> Web Status
        /api/status                    -> Status API
        /gateway/v1/chat/completions   -> LiteLLM 1/2
        /v1/chat/completions           -> đường tương thích cũ
```

Host chỉ publish `8088`. Port Node `8089` chỉ dùng trong mạng/container và không
publish ra host.

## Không được dùng

Không dùng các lệnh sau để xử lý trùng port:

```text
docker compose down
docker compose --profile gateway down
docker compose down -v
docker compose up --remove-orphans
docker network rm token-ledger-dashboard_default
docker volume prune
docker system prune
```

Chúng có thể dừng/xóa các dịch vụ Dashboard hoặc làm mất kết nối tới volume dữ
liệu. Chỉ thao tác trên đúng container `token-ledger-gateway-edge` và
`token-ledger-gateway-lb`.
