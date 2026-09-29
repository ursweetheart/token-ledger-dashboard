## 0. Kiểm hiện trạng trước khi sửa

- [x] 0.1 Với mỗi key `connection-…` đang hoạt động: so `quota_usd` trên Gateway với `budget` trong `gateway_connection_key` (chỉ đọc); ghi số key lệch vào `verification.md` của change này

## 1. Backend

- [x] 1.1 `backend/gateway.py`: thêm kiểu lỗi riêng cho key được quản lý nơi khác (không kế thừa `GatewayError`) và hằng tiền tố `connection-`
- [x] 1.2 `backend/gateway.py`: hàm kiểm `ensure_dashboard_writable(key_alias)` ném lỗi mới với key mang tiền tố; `set_quota` gọi nó **đầu tiên**, trước `find_key`
- [x] 1.3 `backend/main.py`: `quota_top_up` gọi `ensure_dashboard_writable` trước `find_key` ở dòng 538 (nếu không, nó gọi Gateway rồi mới bị từ chối); cả hai endpoint đổi lỗi mới thành HTTP 409
- [x] 1.4 `backend/main.py:61-66`: sửa chú thích "sửa được hạn mức của mọi project" → trừ key do tab Kết nối cấp, nêu lý do

## 2. Kiểm thử

- [x] 2.1 `tests/test_quota_gateway.py`: `set_quota("connection-x", …)` ném lỗi mới và không có lệnh gọi Gateway nào
- [x] 2.2 Ca kiểm key thường (`dms-feedback-tagged`) vẫn đặt được như cũ
- [x] 2.3 Ca kiểm endpoint: đặt thành và cộng thêm cho `connection-x` trả 409; danh sách hạn mức vẫn có key đó (kiểm bằng đọc mã nguồn `main.py`, cùng kiểu `RouteTests`, vì bộ stdlib không nạp được FastAPI)
- [x] 2.4 Ca kiểm ở bộ test của worker: key do worker cấp có tên bắt đầu bằng `connection-` (đổi mẫu tên thì test đỏ)
- [x] 2.5 Chạy bộ test quota và bộ `tests/connection_*_cases.py`, ghi kết quả

## 3. Tài liệu

- [x] 3.1 `docs/reference/gateway-connection-management.md:3`: bỏ "tab Setting giữ phần hạn mức" và câu dặn "chỉ một operator"; nói rõ key `connection-…` chỉ sửa ở tab Kết nối
- [x] 3.2 `docs/reference/dashboard-setup.md:54`: tab Setting xem và nạp hạn mức cho key **không** do tab Kết nối cấp
- [x] 3.3 Ghi cách chặn khẩn cấp key `connection-…`: hạn mức 0 hoặc thu hồi ở tab Kết nối (cần khoá quản trị)

## 4. Kiểm trên dashboard local

- [x] 4.1 Tab Setting: bấm "Đặt thành" cho key `connection-750ea85b-…` của `dms-tap` → hiện "Không lưu được: … tab Kết nối agent", số giữ nguyên
- [x] 4.2 Tab Setting: một key thường vẫn đặt được
