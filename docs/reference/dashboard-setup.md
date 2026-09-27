# Setup và khởi động dashboard trên Windows / Linux

Chạy lệnh tại gốc project. UI, API, worker và script setup đều có trong Git. Mỗi máy tự tạo `.local/connections/` để lưu venv, credential, chứng chỉ và snapshot; thư mục này không nằm trong Git hoặc Docker image.

## Điều kiện trước khi chạy

- Python 3.11 trở lên, có pip và venv. Linux chỉ có `python3` thì dùng `python3` thay `python`; Debian/Ubuntu thường cần gói `python3-venv`.
- Docker Desktop đang chạy trên Windows; Docker Engine với Compose v2 trên Linux. Tài khoản chạy script phải dùng được `docker compose version` và `docker info`.
- Điền cấu hình database hiện có trong `.env` nếu máy đã có dữ liệu. Setup có thể tạo `.env` và hỏi các provider key bắt buộc: `KEY_GOOGLE_AI_STU`, `KEY_CRM_FEEDBACK`, `KEY_RALLI`, `KEY_TLA_HD`. Đây là yêu cầu của các route Gateway hiện có; không dùng key giả.
- Cần quyền pull image Gateway. Nếu registry báo unauthorized, đăng nhập registry hoặc cấu hình `LITELLM_IMAGE` trong `.env`.
- Cổng mặc định: dashboard 8080/8443, PostgreSQL 5432, Gateway 8088/443/9443, instance 4401/4402, worker 8766. Linux dùng thêm HTTPS 8767 cho proxy worker.

## Lần đầu trên mỗi máy

```bash
python scripts/dashboard.py setup
python scripts/dashboard.py start
```

Setup tạo venv, cài dependencies, tạo credential riêng, backup database trước migration, nâng schema bằng Alembic và cấu hình quyền API/worker. Không rebuild database, không xoá dữ liệu, không tự import dữ liệu công ty. Máy có database mới chỉ có schema; cần nạp dữ liệu qua quy trình dữ liệu của dự án để có báo cáo.

Nếu thiếu chứng chỉ dashboard/Gateway, setup tạo chứng chỉ tự ký dùng local. Chứng chỉ sản xuất cần được cung cấp qua `docker/gateway/tls/` trước khi triển khai. Chứng chỉ worker có hạn một năm, cần gia hạn và cập nhật CA API trước khi hết hạn.

Setup trên máy đã có `worker-env.json` giữ nguyên credential và không provision lại. Sau khi pull code mới, start build lại API/UI. Nếu code mới có migration mới, backup và nâng schema theo [quy trình migration](../../db/migrations/README.md) trước khi start; setup không tự nâng lại installation đã hoàn tất.

## Lần sau

```bash
python scripts/dashboard.py start
```

Start giữ worker chạy nền, bật container, nạp override do worker sinh ra và kiểm tra API dữ liệu/quản trị. Không cần kích hoạt venv bằng tay. Đóng terminal không dừng worker. Sau reboot, bật Docker rồi chạy start; script không tự cài service khởi động cùng hệ điều hành.

Start cũng cấp quyền chỉ đọc cho sổ Gateway bằng `gateway-readonly-init`, rồi bật `ledger-refresh` để đưa SpendLogs vào ledger liên tục. Chu kỳ mặc định là 300 giây, đổi bằng `REFRESH_EVERY_SECONDS` trong `.env`. `gateway-watch` là dịch vụ báo động, không phải dịch vụ nạp dữ liệu và không được tự bật bởi script này.

Windows PowerShell cũng dùng được:

```powershell
.\start-dashboard.ps1 setup
.\start-dashboard.ps1
```

Windows Git Bash hoặc Linux Bash dùng cùng lệnh:

```bash
bash start-dashboard.sh setup # lần đầu
bash start-dashboard.sh       # lần sau
```

Git Bash gọi cùng script Python trên Windows, không biến Windows thành Linux. Không dùng chung venv/credential giữa hai hệ điều hành.

## Sử dụng

Mở http://127.0.0.1:8080 → tab Kết nối agent. Copy `.local/connections/admin-key.txt` vào Khoá quản trị kết nối, bấm Mở quản trị. Đây không phải Virtual Key của ứng dụng agent. Key xem dashboard là `DASHBOARD_KEY` trong `.env`. Tab Setting dùng để xem và nạp hạn mức.

Agent mới → lưu provider key để lấy tham chiếu → model/ngân sách → Lưu bản nháp → Xem thay đổi → Áp dụng → Cấp key. Copy Virtual Key ngay; dùng Hướng dẫn host/Docker để cấu hình ứng dụng. Request thử có thể phát sinh phí provider. Agent legacy không tự chuyển ownership cho UI; xem [quản trị kết nối](gateway-connection-management.md).

Áp dụng qua UI tự ghi route/key reference và triển khai cấu hình trên cả hai instance Gateway, đồng thời đăng ký agent vào ledger. Với agent mới do UI quản lý, không cần sửa `config.gateway.yaml` hoặc `gateway-agents.yaml` bằng tay. Bạn vẫn phải cấp provider key thật và cấu hình ứng dụng agent cùng đường mạng tới Gateway. Hướng dẫn endpoint luôn có đúng một `/v1`, kể cả cấu hình worker đã chứa `/v1`.

Đổi `DASHBOARD_KEY` hoặc `CONNECTION_ADMIN_KEY` không làm Gateway drift; vẫn cần recreate API để nạp key mới. Các thay đổi khác như provider key, master key, route, Compose và registry vẫn phải được kiểm tra/reconcile. Installation dùng baseline cũ trước khi nâng thuật toán fingerprint cần review rồi chấp nhận baseline một lần qua Xem thay đổi ngoài UI → Chấp nhận baseline đã xem; không bootstrap lại để xóa ownership.

## Linux và triển khai server

Worker nghe `127.0.0.1:8766`. Proxy HTTPS dùng host network để gọi loopback này; API Docker gọi `https://host.docker.internal:8767` qua mapping host-gateway. Windows dùng proxy trong bridge network của Docker Desktop. Không mở RPC HTTP 8766 ra LAN.

Luồng Linux áp dụng Docker Engine trên chính host, không áp dụng daemon từ xa/rootless Docker hoặc Docker Desktop for Linux. Chạy setup/start bằng cùng tài khoản dịch vụ. Bảo vệ HTTPS 8767 bằng firewall máy chủ; RPC vẫn yêu cầu credential. Bộ script phục vụ khởi động local/server thủ công, chưa thay thế cấu hình systemd hoặc vận hành production.

## Khi gặp lỗi

- Thiếu cấu hình: điền `.env`, chạy setup; không đưa key vào Git.
- Worker: `.local/connections/worker.log`. Script từ chối cổng 8766 nếu listener không xác thực bằng credential của máy này.
- Container: `docker compose logs --tail 100 api`. Khi vận hành riêng phải nạp `runtime.yaml` và `compose.connections.yaml` nếu có; dùng script start để không bỏ sót.
- Dữ liệu 500: kiểm tra migration/quyền database; không rebuild để chữa lỗi schema.
- Di chuyển project: cập nhật đường dẫn trong `worker-env.json`/`runtime.yaml` và xử lý baseline drift theo tài liệu quản trị. Không copy venv Windows sang Linux.
- Setup gián đoạn: kiểm tra log/backup trước retry. Nếu đã bootstrap nhưng thiếu completion marker, đối chiếu baseline trước sử dụng; không bỏ qua cảnh báo drift.
