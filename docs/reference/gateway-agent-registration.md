# Đăng ký agent Gateway-only cho dashboard

Workflow này dành cho **agent mới gửi request qua Gateway**. Không crawl web,
không cần `users.json`, billing CSV hay monitoring export. Chỉ cấu hình dashboard;
không tự tạo tuyến model, Virtual Key hoặc hạn mức ở Gateway.

## 1. Nâng cấp một lần

Sao lưu DB theo quy trình vận hành trước khi nâng cấp. Chạy từ root project,
kiểm tra đúng database đích trong `.env` (không đưa mật khẩu vào YAML).
Dừng ngay nếu một lệnh trả exit code khác 0; không tiếp tục các bước sau.

```powershell
docker compose --profile refresh stop ledger-refresh
docker compose --profile refresh build ledger-refresh
docker compose --profile refresh run --rm ledger-refresh python3 -m alembic upgrade head
docker compose build api web
docker compose up -d api web
```

Migration `014_gateway_agent_registry` thêm bảng/sequence, không xóa facts hay
pricing history. Migration trước đó `013` cũng chạy nếu DB đang ở `012`.
Không chạy `rebuild_db.py`, `load_org.py` hoặc `load_billing.py --rebuild`.
Khi registry đã có agent, các lệnh bulk này bị chặn trước thao tác phá dữ liệu.

## 2. Chỉ sửa một file khi thêm agent

File `config/gateway-agents.yaml` mặc định `agents: []`, chưa đăng ký ai.
Thay bằng ví dụ dưới đây, dùng code/tag thật của agent:

```yaml
version: 1
agents:
  - code: support-helper
    name: Trợ lý hỗ trợ
    user_mode: multiple
    reporting_start_date: '2026-09-24'
    active: true
  - code: auto-classifier
    name: Bộ phân loại tự động
    user_mode: single
    reporting_start_date: '2026-09-24'
    active: true
```

- `code`: phải khớp duy nhất một tag định danh trong log Gateway. Chữ thường,
  số và dấu gạch ngang. Không nhập agent_id: database tự cấp.
- `name`: tên hiển thị, được phép sửa sau.
- `user_mode: single`: dùng tài khoản dịch vụ `svc.<code>`. Ví dụ
  `svc.auto-classifier`; không tính thành nhân viên.
- `user_mode: multiple`: lấy ID người dùng từ `end_user` của log Gateway.
  Agent server gửi `X-User` ổn định theo hợp đồng Gateway hiện hữu. Dashboard
  tự tạo identity khi thấy request hợp lệ, không cần import danh bạ.
- `reporting_start_date`: ngày bắt đầu nhận dữ liệu, theo giờ Việt Nam.
- `active`: trạng thái hiển thị. `false` không ngừng ingest và không thu hồi key.

ID được giữ nguyên chữ hoa/thường và khoảng trắng; `Alice` khác `alice`.
Tối đa 256 byte UTF-8, không chấp nhận chuỗi trắng hoặc ký tự điều khiển.
Hai agent cùng gửi `admin` tạo hai identity riêng. Không gộp với nhân viên thật.
Agent server chịu trách nhiệm xác thực user; header tự nó không chứng minh danh tính.

## 3. Sau khi lưu YAML

```powershell
docker compose --profile refresh stop ledger-refresh
docker compose --profile refresh run --rm ledger-refresh python3 scripts/apply_gateway_agents.py --config /app/config/gateway-agents.yaml --dry-run
docker compose --profile refresh run --rm ledger-refresh python3 scripts/apply_gateway_agents.py --config /app/config/gateway-agents.yaml
docker compose --profile refresh run --rm ledger-refresh python3 scripts/refresh_gateway.py
docker compose --profile refresh up -d ledger-refresh
```

Kiểm tra `$LASTEXITCODE` ngay sau **từng lệnh**. Chỉ chạy lệnh tiếp theo khi bằng 0.
`dry-run` chỉ in create/update/unchanged/retained; không cấp ID, không ghi DB.
Lệnh apply sau đó mới ghi một transaction. Không cần sửa Python, không chạy
`gen_catalog.py`, không sửa `SINGLE_USER_AGENTS`.

Apply và refresh dùng chung khóa DB; nếu một tiến trình đang chạy, tiến trình
thứ hai từ chối và yêu cầu thử lại. Thư mục config được mount read-only vào
container. Worker refresh chỉ đọc registry trong DB, không cần đọc YAML nữa.

## 4. Agent đã có / chưa có request

Chưa có request: vẫn đăng ký được, UI hiện trạng thái chưa có usage thành công.
Đã có request: lần refresh đầu đọc lại log còn lưu của riêng agent mới, kể cả
trước watermark chung; chỉ nhận từ `reporting_start_date`. Không khôi phục được
log đã bị Gateway xóa theo retention.

Cờ pending chỉ hết sau khi loader, rollup ngày/giờ, performance và heartbeat
đều thành công. Nếu lỗi, giữ pending để lần sau thử lại. Chạy loader riêng
không hoàn tất vòng backfill. Chạy lại không nhân đôi facts.

Trong tab Agents, xem bảng **Định danh qua Gateway**. Bảng áp dụng agent và
khoảng ngày, không áp dụng bộ lọc nhân viên/phòng ban. Request lỗi xuất hiện
trong phạm vi quan sát nhưng không cộng thành successful usage. Mục chưa quy
được giữ token/calls thiếu identity. Multiple không có danh bạ nên tỷ lệ áp
dụng là **chưa biết**, không phải 100% số identity đã thấy.

Kiểm log refresh: missing/invalid/unresolvable identity, unknown tag, nhiều
tag, cache duplicate, before reporting start date và whole-ledger check.
Chỉ bật lịch tự động sau khi các cảnh báo đã được hiểu và exit code bằng 0.

## 5. Quy tắc bảo vệ lịch sử

`code` là khóa đăng ký: không rename bằng cách đổi chuỗi. Chuỗi mới tạo agent
mới, entry cũ được retained; đây không phải di chuyển lịch sử.
`user_mode` và `reporting_start_date` không được đổi sau apply. Agent legacy
không được tự chuyển quyền quản lý sang YAML. Chuyển policy cần migration riêng.
Bỏ entry không xóa agent; apply in `retained`. Có thể sửa `name`/`active`.

Rollback vận hành: dừng worker, giữ nguyên schema/accounts/facts/mappings.
Không downgrade bằng cách drop bảng hay rebuild. Nếu chỉ UI có lỗi, rollback
UI trước; reader cũ cần được kiểm chứng hiểu kind `gateway_observed`.

## 6. Phần vẫn cấu hình ngoài dashboard

Gateway vẫn quản lý tuyến/model, provider credentials, Virtual Key, tag và quota.
Agent vẫn phải gọi Gateway thay vì gọi provider trực tiếp, gửi đúng key và X-User.
YAML ở đây **không cấu hình Gateway** và không thay đổi quyền gọi model.
