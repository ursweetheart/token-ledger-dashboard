## Context

Hiện trạng (đã đọc code 03/11/2026):

- `backend/main.py` đọc `LITELLM_MASTER_KEY` (dòng 148) và gọi `gateway.configure(GATEWAY_BASE_URL, GATEWAY_MASTER_KEY)` (dòng 188). Cửa chặn khởi động (dòng 178) đòi có master key trừ khi `QUOTA_DISABLED=1`.
- `backend/gateway.py` gửi `Authorization: Bearer <master_key>` tới LiteLLM `/key/list`, `/key/update` (đường dẫn viết cứng trong `_call`). Chứa cả logic đọc (`quota_of`, `spend_of`, `tag_of`, `log_of`), gộp-ghi (`_merge`, `set_quota`), chặn key `connection-…` (`ensure_dashboard_writable`), và kiểm giá trị (`parse_amount`, `sanitize_incoming`).
- Ba endpoint hạn mức ở `main.py`: `GET /api/quota` (→ `gateway.list_keys`), `POST /api/quota` (→ `gateway.set_quota`), `POST /api/quota/top-up`. Chứng danh là khoá dashboard (`caller`).
- Worker (`backend/connection_worker.py`) đã có lớp `Gateway` (dòng 76) dựng với master key cho **cả hai** instance (`self.gateways = [Gateway(url, master) …]`), và đã dùng `/key/generate`, `/key/update`, `/key/list` cho tab Kết nối. Thực đơn RPC cố định ở `build_app` (`/rpc/{action}`) kiểm chính xác tập trường của mỗi lệnh.
- `backend/connection_api.py` có sẵn hàm `rpc(action, data)` gọi worker qua HTTPS, xác thực bằng `CONNECTION_WORKER_KEY`, và đã làm sạch thân lỗi.

Lỗ hổng: master key nằm trong `api` cho phép tạo pass-through rò khoá Google (đã chứng minh). Worker là nơi duy nhất nên giữ master key.

## Goals / Non-Goals

**Goals:**
- Bỏ hẳn `LITELLM_MASTER_KEY` khỏi container `api`; không đường nào trong `api` gọi API quản trị của Gateway.
- Đọc và sửa hạn mức vẫn chạy, qua worker.
- Frontend (`web/js`) không phải sửa: endpoint `/api/quota` giữ nguyên đường dẫn, chứng danh (khoá dashboard) và hình dạng dữ liệu.
- Luật 409 với key `connection-…` giữ nguyên hành vi.

**Non-Goals:**
- Vá bản fork LiteLLM để chặn `/config/pass_through_endpoint` (phòng thủ sâu, để sau).
- Đổi chứng danh tab Setting sang khoá quản trị (giữ khoá dashboard như cũ).
- Đổi cách tab Kết nối hoạt động.

## Decisions

**1. Đặt logic hạn mức ở worker, giữ hàm tính thuần ở `api`.**
- Worker thêm `quota_list()` và `quota_set(key_alias, amount, actor)`. Hai hàm này gọi `self.gateways[0]` (master key sẵn có), và mang theo phần cần master key: phân trang `/key/list`, gộp metadata, ghi nhật ký, kiểm key `connection-…`, kiểm giá trị tiền.
- `quota_list()` trả **danh sách key thô** (như LiteLLM trả) đã phân trang xong. Phần biến mỗi key thành dòng cho tab Setting (`quota_of`, `spend_of`, `tag_of`, `log_of`, đếm sibling theo tag) **giữ ở `api`** vì chỉ thao tác trên dict, không cần master key. Nhờ vậy `backend/gateway.py` co lại thành các hàm thuần, bỏ `_call`/`configure`/master key.
- *Phương án khác đã cân nhắc:* chuyển cả phần dựng dòng sang worker. Bỏ, vì nó kéo logic trình bày (đếm sibling, cờ cảnh báo) ra khỏi `api` mà không giảm được rủi ro — phần đó không đụng master key.

**2. `quota-set` nhận `actor` từ `api`, không tự đoán.**
- `api` biết người gọi (`who.name` từ khoá dashboard) nên truyền `actor` vào RPC để worker ghi đúng vào nhật ký khoá. Worker không có khái niệm người dùng dashboard.
- Tập trường cố định: `quota-set` = `{key_alias, amount, actor}`; `quota-list` = `{}`. Khớp kiểu kiểm chặt của thực đơn RPC hiện có.

**3. `api` gọi worker qua đúng đường `connection_api.rpc`.**
- Tách `rpc(action, data)` khỏi `connection_api.router` thành hàm dùng lại (hoặc một client nhỏ), để ba endpoint hạn mức gọi `quota-list`/`quota-set` mà vẫn giữ chứng danh khoá dashboard của chính endpoint.
- Lỗi worker đã được làm sạch sẵn ở `rpc`; map 409 (key `connection-…`) và 503 (worker không chạy) ra như cũ.

**4. Bỏ cấu hình master key ở `api`.**
- `main.py`: bỏ đọc `LITELLM_MASTER_KEY`, bỏ `gateway.configure(...master...)`, đổi cửa chặn khởi động (không còn đòi master key). `docker-compose.yml`: bỏ `LITELLM_MASTER_KEY` ở service `api` (giữ ở worker và các service LiteLLM).

**5. `quota-watch` đọc qua worker (PA2, chốt 16/11/2026).**
- Phát sinh khi làm: `scripts/watch_quota.py` dùng `gateway.configure/list_keys/GatewayError`, các hàm đã bỏ ở quyết định 1, nên service `quota-watch` chết lúc khởi động.
- Chọn PA2: `quota-watch` gọi RPC `quota-list` qua `connection_api.worker_rpc` (nạp trễ trong `main()` vì nó kéo FastAPI; phần luật đổi bậc vẫn kiểm được trên máy sạch). Compose bỏ `LITELLM_MASTER_KEY` và `GATEWAY_BASE_URL` khỏi service, thêm ba biến `CONNECTION*`. `scripts/dashboard.py` cấp cho `quota-watch` đúng khối chứng chỉ TLS của worker mà `api` đang có.
- *Phương án khác đã cân nhắc (PA1):* `quota-watch` tự giữ master key và một client đọc riêng. Bỏ, vì nó để lại thêm một container mang đúng cái khoá tạo được pass-through, tức đi ngược mục tiêu của change. PA1 đơn giản hơn và `quota-watch` không mở cổng nào, nhưng "khó vào hơn" không phải "không có khoá".
- Hệ quả của PA2: worker tắt thì bộ canh mù. Xử lý: giữ nguyên bậc cũ, và sau 2 nhịp hỏng liên tiếp gửi một thư "không đọc được hạn mức". Việc CHẶN không bị ảnh hưởng (hook nằm trong Gateway).

## Risks / Trade-offs

- **Tab Setting phụ thuộc worker** → worker tắt thì `/api/quota` trả 503. Chấp nhận có chủ ý (đã ghi trong tài liệu/slide); thông báo 503 rõ ràng để người vận hành biết bật worker.
- **Thêm một chặng mạng** (api → worker → LiteLLM) cho mỗi lần đọc/ghi hạn mức → chậm hơn chút; không đáng kể với tần suất thao tác tab Setting.
- **Logic hạn mức bị chẻ đôi** (gọi + gộp ở worker, dựng dòng ở api) → nguy cơ hai nơi hiểu khác nhau về key `connection-…` hay tag. Giảm thiểu: worker là nơi DUY NHẤT quyết định 409 và gộp metadata; `api` chỉ đọc hiển thị. Test đối chiếu số trước/sau khi chuyển.
- **Máy đã `setup` từ trước 16/11/2026** có `.local/connections/runtime.yaml` sinh từ bản cũ, chưa có khối `quota-watch` → bộ canh không tin được chứng chỉ của worker và sẽ gửi thư "không đọc được hạn mức". Phải thêm khối đó bằng tay một lần (ghi trong `docs/reference/quota-internals.md`).
- **`QUOTA_DISABLED=1`** vẫn phải cho `api` khởi động và ẩn/che đường hạn mức như cũ, nay không kèm master key.

## Migration Plan

1. Thêm `quota_list`/`quota_set` + hai nhánh RPC ở worker; thêm test worker.
2. Tách client RPC để `api` dùng lại; chuyển ba endpoint hạn mức sang gọi worker; giữ hình dạng trả về.
3. Bỏ master key khỏi `main.py` và `docker-compose.yml`; sửa cửa chặn khởi động.
4. Chạy `backend/check_api.py` và test kết nối; đối chiếu `/api/quota` trước/sau phải ra cùng số.
5. Rollback: hoàn tác commit; đặt lại `LITELLM_MASTER_KEY` cho `api` trong `.env`/compose là quay về hành vi cũ.

## Open Questions

- Worker đang dùng `self.gateways[0]` cho thao tác key; `/key/list`, `/key/update` tác động LiteLLM DB chung nên một instance là đủ — xác nhận không có trạng thái chỉ-trong-RAM nào của key cần cả hai instance (khác với pass-through vốn chỉ trong RAM).
