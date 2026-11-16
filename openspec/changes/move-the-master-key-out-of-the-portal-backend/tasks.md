> TRẠNG THÁI 03/11 (đang dở, chưa commit, chưa test): nhóm 1-3 đã sửa code (api không còn master key; worker có quota-list/quota-set/quota-top-up). CHƯA làm: 1.4, nhóm 4-5. VẤN ĐỀ MỞ: `scripts/watch_quota.py` (service quota-watch) cũng giữ master key và ĐANG HỎNG vì gateway.py đã bỏ các hàm nó dùng — chờ chốt PA1 (giữ key riêng) hay PA2 (qua worker). Cân nhắc thêm change vá fork chặn pass-through.

## 1. Worker: thêm hai thao tác hạn mức

- [x] 1.1 Thêm `quota_list(self)` vào `Worker` (`backend/connection_worker.py`): dùng `self.gateways[0]` gọi `/key/list` với `return_full_object=true`, phân trang (chặn vòng lặp như `backend/gateway.py` hiện làm), trả danh sách key thô.
- [x] 1.2 Thêm `quota_set(self, key_alias, amount, actor)`: kiểm key `connection-…` (từ chối bằng `Conflict`/409 trước khi gọi Gateway), đọc key, gộp metadata + ghi nhật ký (chuyển `_merge` và luật `QUOTA_FIELD`/`LOG_FIELD` từ `backend/gateway.py`), rồi `/key/update`. Kiểm giá trị tiền (`parse_amount`) trong worker, trả `ValueError`/422 khi sai.
- [x] 1.3 Thêm hai nhánh vào thực đơn RPC `build_app`: `action=='quota-list' and not body → worker.quota_list()`; `action=='quota-set' and set(body)=={'key_alias','amount','actor'} → worker.quota_set(...)`. Giữ kiểu kiểm tập trường chặt như các lệnh khác.
- [x] 1.4 Viết test worker cho `quota_list`/`quota_set` và hai nhánh RPC: trả 409 cho key `connection-…`, 422 cho tiền sai, 200 + nhật ký đúng cho key thường (dùng Gateway giả như các test kết nối đang có).

## 2. `api`: chuyển ba endpoint hạn mức sang gọi worker

- [x] 2.1 Tách client RPC worker khỏi `connection_api.router` thành hàm/đối tượng dùng lại (giữ TLS, `CONNECTION_WORKER_KEY`, chống redirect, làm sạch thân lỗi), để `main.py` gọi được `quota-list`/`quota-set`.
- [x] 2.2 Sửa `GET /api/quota` (`quota_list`) gọi RPC `quota-list` thay cho `gateway.list_keys`; giữ nguyên phần dựng dòng (`_agent_view`, đếm sibling theo tag) và hình dạng trả về.
- [x] 2.3 Sửa `POST /api/quota` (`quota_set`) và `POST /api/quota/top-up` gọi RPC `quota-set` (truyền `actor = who.name`); map 409 (key `connection-…`) và 503 (worker không chạy) ra như cũ; giữ nguyên dữ liệu trả về.
- [x] 2.4 `_quota_ready`: đổi điều kiện 503 từ "có master key" sang "worker cấu hình/với tới được" (vẫn tôn trọng `QUOTA_DISABLED=1`).

## 3. Bỏ master key khỏi `api`

- [x] 3.1 `backend/gateway.py`: bỏ `_call`, `configure`, `_master_key`, `list_keys`, `set_quota` (và các hằng đường dẫn `/key/*`); giữ lại các hàm thuần `quota_of`, `spend_of`, `tag_of`, `log_of`, `parse_amount`, `sanitize_incoming`, `QUOTA_FIELD`, `LOG_FIELD` dùng cho hiển thị ở `api`. (Hoặc chuyển các hàm thuần sang module khác và xoá `gateway.py` nếu gọn hơn.)
- [x] 3.2 `backend/main.py`: bỏ đọc `LITELLM_MASTER_KEY` và `gateway.configure(...master...)`; sửa cửa chặn khởi động (dòng ~178) để không còn đòi master key.
- [x] 3.3 `docker-compose.yml`: bỏ `LITELLM_MASTER_KEY` khỏi service `api` (giữ ở worker và các service LiteLLM). Rà không còn nơi nào bơm master key vào `api`.

## 4. Kiểm thử và đối chiếu

- [x] 4.1 Cập nhật test chạm `/api/quota` (đọc/đặt/cộng thêm, 409, 503) để đi qua worker; sửa fixture nếu cần.
- [x] 4.2 Dựng Gateway máy dev, đối chiếu `GET /api/quota` trước và sau change: cùng danh sách, cùng số (hạn mức, đã tiêu, cảnh báo, đếm sibling).
- [x] 4.3 Kiểm an toàn: `docker exec` vào container `api` xác nhận môi trường KHÔNG có `LITELLM_MASTER_KEY`; thử tạo pass-through từ trong `api` phải thất bại (không có master key).
- [ ] 4.4 Chạy `backend/check_api.py` và bộ test kết nối; chạy CI (Python + JavaScript) phải xanh.

## 5. Tài liệu và dọn dẹp

- [x] 5.1 Cập nhật tài liệu/slide: đổi "hướng sửa (chưa làm)" thành "đã vá" sau khi triển khai; ghi rõ tab Setting cần worker. XONG phần tài liệu trong repo 16/11 (`docs/reference/quota-internals.md` mục 8 và sơ đồ/bảng file, `quota-han-muc.md` bước 2 và 5, `noi-agent-vao-gateway-hai-phia.md`, `.env.example`). CÒN CHỜ TRIỂN KHAI: sơ đồ C4 hiện trạng (RDAH_C4, Drive) và slide vẫn vẽ `api` giữ master key vì server chưa chạy bản này - đổi sau khi lên server.
- [x] 5.2 Ghi lại cách rollback (đặt lại `LITELLM_MASTER_KEY` cho `api`) trong ghi chú vận hành. Ở `docs/reference/quota-internals.md` mục 8, kèm bước tay thêm khối `quota-watch` vào `runtime.yaml` cho máy đã setup.

## 6. Hệ quả phát sinh

- [x] 6.1 `scripts/watch_quota.py` (service quota-watch) đang hỏng vì dùng `gateway.list_keys/configure/GatewayError` đã bị bỏ. ĐÃ CHỐT PA2 (16/11/2026): quota-watch gọi RPC `quota-list` của worker, không giữ master key, gửi một thư khi 2 nhịp liên tiếp không đọc được.

> TRẠNG THÁI 16/11 (chưa commit): xong 1.4, 4.1, 4.2, 4.3, 6.1. Đo trên stack cô lập (LiteLLM 1.100.5, khoá giả): `GET /api/quota` bản cũ và bản mới trả JSON giống hệt (7 dòng); container `api` và `quota-watch` không có master key, tạo pass-through từ trong đó bị 401 (bản cũ có master key: 200). 4.4 mới chạy tại máy (check_api 31/31, 80 phép connection, 258 phép máy sạch + 3 của test_merge_billing_discount chưa commit, 117 JS) - CI trên GitHub CHƯA chạy vì chưa commit. Xong thêm 5.1 (phần repo), 5.2. CÒN LẠI: 4.4 (chờ CI của chính commit này trên GitHub), và sau khi lên server: thêm khối `quota-watch` vào runtime.yaml của server, đổi sơ đồ C4 hiện trạng + slide sang "đã vá".
