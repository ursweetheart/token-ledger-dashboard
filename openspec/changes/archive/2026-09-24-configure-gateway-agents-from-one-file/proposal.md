## Why

Dashboard đã nạp usage từ Gateway nhưng chưa có cách đăng ký agent mới và nhận diện người gọi chỉ từ Gateway: operator vẫn bị dẫn qua generator phụ thuộc file cũ và luồng rebuild không phù hợp. Cần một change thống nhất để khai agent trong một YAML, áp dụng không mất dữ liệu, và hiển thị usage theo định danh trong request mà không crawl app hay nhập danh bạ.

## What Changes

- Thêm `config/gateway-agents.yaml` có schema version, agent code/name, chế độ `single` hoặc `multiple`, ngày bắt đầu báo cáo và trạng thái hoạt động; không chứa secret.
- Thêm lệnh kiểm tra/áp dụng cấu hình có dry-run, transaction, kiểm tra xung đột và chạy lại không tạo bản sao; tạo agent, đơn vị kỹ thuật và tài khoản neo bằng ghi bổ sung, không gọi generator, `load_org.py` hoặc rebuild.
- Agent single dùng `svc.<code>`; agent multiple tự ghi nhận định danh từ `end_user` của sổ Gateway (đầu vào `X-User`), tách theo agent, không cần danh bạ ngoài.
- Tích hợp vào bộ nạp và refresh hiện có; đăng ký trước khi có request vẫn được, có lịch sử thì backfill có kiểm soát. Giữ nguyên token, tiền, request ID và sổ Gateway chỉ đọc.
- Thêm API/hiển thị định danh Gateway đã quan sát, không giả định đó là nhân viên đã được cấp quyền; không dùng số người từng gọi làm mẫu số adoption. Giữ `/api/accounts` chỉ cho `kind='real'`.
- Đóng gói YAML vào đường vận hành Docker và tài liệu: sửa một file, chạy một lệnh apply, bật refresh. Sửa chỉ dẫn onboarding cũ; chặn các legacy loader có thể xóa dữ liệu agent được quản lý mới.
- Giữ nguyên hành vi agent cũ khi chưa khai trong registry mới; phối hợp với change `keep-a-person-visible-in-every-agent-they-use` đang làm, không gộp hoặc sửa lịch sử người dùng cũ.

## Capabilities

### New Capabilities

- `gateway-agent-registration`: cấu hình một file và đăng ký tăng dần an toàn, không phụ thuộc source exports.
- `gateway-observed-identities`: nhận diện người gọi từ log theo chính sách single/multiple và phạm vi agent.
- `gateway-observed-reporting`: API và UI usage cho định danh Gateway, phân biệt với danh bạ được cấp quyền.

### Modified Capabilities

- `gateway-ledger-loading`: dùng registry đã áp dụng để phân giải agent/người gọi và nạp lại lịch sử cho agent được cấu hình.

## Impact

- Database: migration bổ sung registry/mapping định danh, cấp ID an toàn và quyền đọc; không đổi ID/username của account cũ, không reset schema hoặc giá.
- Python: module cấu hình mới, CLI apply, `db/load_gateway.py`, `db/connect.py`, refresh, guard ở generator/org loader và các entrypoint bulk load liên quan. Thêm parser YAML vào dependency được khai báo rõ.
- Backend/web: endpoint chỉ đọc có xác thực cho định danh Gateway; bảng usage và nhãn nguồn/độ phủ, không phá hợp đồng danh bạ cũ.
- Docker/CI/docs: config mount, tools image, test PostgreSQL thật trong môi trường cách ly, kiểm hồi quy số liệu và runbook.
- Gateway routing/key generation và agent gửi `X-User` vẫn là trách nhiệm riêng. Không thêm crawl, gọi Google có phí, tự cấp Virtual Key, đồng bộ phòng ban hay sửa cách tính giá trong change này.
