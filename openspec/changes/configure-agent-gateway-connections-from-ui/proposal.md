## Why

Kết nối một agent hiện yêu cầu sửa route, môi trường container, Virtual Key và registry dashboard ở nhiều nơi. Một request thành công chưa chứng minh đúng Google project hoặc usage đã vào dashboard; cần giao diện quản trị dẫn dắt và xác minh toàn bộ quá trình.

## What Changes

- Thêm trang quản trị Kết nối agent: thông tin agent, provider key, model, RPM/TPM, hạn mức spend tích lũy từng Virtual Key, chế độ quota chat/batch và trạng thái từng bước.
- Thêm preview không mutation và tác vụ apply có revision, khóa, lịch sử và phục hồi khi lỗi.
- Quản lý route/tag, tham chiếu secret, Virtual Key và đăng ký dashboard bằng các adapter giới hạn quyền; áp dụng nhất quán lên hai Gateway instance.
- Sinh hướng dẫn cấu hình phía agent và kiểm tra routing, log, usage bằng request thử có chủ đích; phân biệt kiểm chứng Gateway với kiểm chứng request từ ứng dụng agent đã triển khai.
- Duy trì lịch sử khi ngừng agent; tách ngừng hiển thị khỏi thu hồi quyền truy cập.
- Không triển khai agent từ xa, không quản lý toàn bộ cấu hình LiteLLM, không thay mô hình identity hoặc quota hiện có.

## Capabilities

### New Capabilities

- `gateway-connection-management`: Hồ sơ kết nối, giao diện quản trị, preview và vòng đời Virtual Key.
- `gateway-connection-application`: Áp dụng cấu hình có kiểm soát, nguồn cấu hình, secret, đồng bộ hai instance và phục hồi.
- `gateway-connection-verification`: Cấu hình mẫu phía agent và bằng chứng kết nối đúng qua Gateway đến dashboard.

### Modified Capabilities

Không thay requirement của registry, quota, identity hoặc API đọc hiện tại; các capability mới gọi lại các hợp đồng đó.

## Impact

- UI: `web/index.html`, `web/js`, `web/css`; API: `backend/main.py` và các module quản trị mới.
- Tái sử dụng `db/gateway_registry.py`, `backend/gateway.py`, cơ chế quota và refresh hiện có.
- Thêm migration additive cho hồ sơ, revision, operation và audit; quyền ghi riêng ngoài connection role đọc dashboard.
- Thêm worker vận hành giới hạn quyền, cơ chế lưu secret và cấu hình Compose cho apply/recreate Gateway.
- Không rebuild database, không tự chuyển agent legacy sang registry mới; không thay đổi Gateway đang chạy khi chỉ tạo proposal.
