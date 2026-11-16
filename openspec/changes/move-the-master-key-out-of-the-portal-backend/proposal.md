## Why

Container `api` của portal đang giữ `LITELLM_MASTER_KEY` để đọc và sửa hạn mức qua `/key/list` và `/key/update`. Ngày 03/11/2026 đã **chứng minh trên máy dev**: ai chạy được code trong container `api` thì dùng chính master key đó tạo một đường chuyển tiếp (`POST /config/pass_through_endpoint`) với header `os.environ/KEY_GOOGLE_AI_STU` trỏ về máy ngoài, và lấy được khoá Google thật (header nhận ở máy nghe có SHA-256 khớp khoá trong `.env`). Master key ở trong `api` là quyền rộng hơn mức cần cho một dashboard chỉ-đọc, và là đường rò khoá Google.

Worker trên host (`backend/connection_worker.py`) đã sẵn giữ master key và đã sẵn một thực đơn RPC cố định; nó là nơi đúng để đặt mọi thao tác cần master key.

## What Changes

- Thêm hai RPC vào worker: `quota-list` (không tham số) và `quota-set` (`key_alias`, `amount`, `actor`). Worker gọi `/key/list`, `/key/update` bằng master key sẵn có; logic gộp metadata, ghi nhật ký, chặn key `connection-…` (409) chuyển vào worker.
- Ba endpoint hạn mức của `api` (`GET /api/quota`, `POST /api/quota`, `POST /api/quota/top-up`) chuyển sang gọi worker qua đường RPC đang có (`backend/connection_api.py`), thay cho gọi thẳng LiteLLM. Chứng danh và hình dạng dữ liệu của endpoint giữ nguyên để **frontend không phải sửa**.
- **BREAKING (vận hành):** bỏ `LITELLM_MASTER_KEY` khỏi container `api` trong `docker-compose.yml`; bỏ `gateway.configure(..., master_key)` và cửa chặn khởi động đòi master key trong `backend/main.py`. Từ nay tab Setting **cần worker đang chạy**; worker tắt thì ba endpoint hạn mức trả 503.
- `backend/gateway.py` không còn nhận master key; phần tính thuần (đọc `quota_of`, `spend_of`, `tag_of`, dựng dòng cho tab Setting) giữ lại ở `api` vì chỉ thao tác trên dữ liệu khoá worker trả về.

- **Bổ sung 16/11/2026 (PA2):** `scripts/watch_quota.py` (service `quota-watch`) cũng bỏ master key, đọc hạn mức qua RPC `quota-list` của worker, và gửi một thư khi không đọc được. `docker-compose.yml` bỏ `LITELLM_MASTER_KEY` khỏi `quota-watch`; `scripts/dashboard.py` cấp cho nó chứng chỉ của worker. Sau change này master key chỉ còn ở worker và ở chính các container LiteLLM.

Không làm trong change này (non-goal): vá bản fork LiteLLM để chặn `/config/pass_through_endpoint` — để lại như một lớp phòng thủ sâu cân nhắc sau.

## Capabilities

### New Capabilities
<!-- không có capability mới; thao tác ánh xạ vào spec đã có -->

### Modified Capabilities
- `project-quota-budgets`: đọc và ghi hạn mức SHALL đi qua worker; backend `api` KHÔNG giữ master key của Gateway nữa; luật từ chối key `connection-…` (409) SHALL được thi hành ở worker; worker không chạy thì đường hạn mức SHALL trả 503.
- `api-access-control`: cửa chặn khởi động của `api` SHALL không còn đòi `LITELLM_MASTER_KEY`; `api` khởi động không mang master key và không có đường nào trong `api` gọi thẳng API quản trị của Gateway.

## Impact

- Mã: `backend/connection_worker.py` (thêm `quota_list`/`quota_set` + nhánh RPC), `backend/connection_api.py` (lộ đường gọi RPC dùng chung hoặc thêm route hạn mức), `backend/main.py` (ba endpoint hạn mức + bỏ cấu hình master key), `backend/gateway.py` (bỏ master key, thu hẹp còn hàm tính thuần), `docker-compose.yml` (bỏ `LITELLM_MASTER_KEY` ở service `api`).
- Vận hành: tab Setting phụ thuộc worker; cần cập nhật tài liệu/slide (đã ghi hướng sửa này). `QUOTA_DISABLED` vẫn cho chạy `api` không có hạn mức.
- Kiểm thử: các test chạm endpoint `/api/quota` và RPC worker; CI (`backend/check_api.py`, test kết nối).
- Không đổi: frontend (`web/js`), lược đồ database, kỷ luật chỉ-đọc của PostgreSQL.
