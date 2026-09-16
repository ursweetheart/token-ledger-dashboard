# Gateway fallback — cập nhật và retest 11/09/2026

## Trạng thái

**App focused tests PASS; Docker fallback và hồi quy LB retest PASS. Chưa commit/push hoặc đổi nhánh.**
Cập nhật sau khi Docker hoạt động: 11/09/2026, 09:43 +0700.

- `law_insight`: sửa SMTP 587 sang STARTTLS trước authentication; bổ sung metadata `route=direct`/operation_id cho direct helpers. Mỗi thay đổi đều có regression test RED → GREEN.
- Kiểm thử lại 8 module pytest: **140 passed, 19 warnings, 7.57 giây**. Không phải toàn bộ app suite.
- Syntax app/migration: PASS 8 file; `git diff --check`: PASS hai repo.
- Blocker Docker daemon đã được giải quyết. Đã xác minh network internal, DB volume riêng, LB bind 127.0.0.1:4101; chỉ khởi động các container mock hiện có, không rebuild hoặc chạy production Compose.
- Báo cáo đầy đủ và template config nằm trong repo app: `backend/GATEWAY-FALLBACK-TEST-REPORT.md`, `backend/GATEWAY.md`, `backend/gateway-fallback.env.example`.

## Bằng chứng Docker của lượt retest mới

[Fallback JSON](../artifacts/current/law-fallback-e3cee80a23d0.json): **20/20 stage PASS**; 18 lần gọi Gateway SDK; 9 direct-fallback mock attempts; 12 row dựng trong memory (5 gateway, 7 direct_fallback); 1 SMTP mock email. Hai direct attempts cố ý lỗi không tạo row thành công. Bao gồm LB dừng thật, request liên tiếp/đồng thời, fallback tắt, direct failure, phục hồi và outage lần hai. Không ghi app PostgreSQL, không Gmail/Google thật.

[LB hồi quy mới](../artifacts/current/law-lb-815c700c6af2.json): **PASS, 93 request thành công / 8 user / 93 SpendLogs**, 93 response ID duy nhất khớp user và token, cả hai Proxy có traffic. Concurrency 1 → 2 → 4 → 8; Proxy-down 8/8; recovery 4/4. Fallback tắt + LB-down: một SDK attempt, không bypass. Không phát hiện canary ở các trường log đã kiểm tra.

Hai lượt đều xóa key test với delete 200, đọc lại 404. Inspect độc lập sau test xác nhận LB, hai Proxy và DB mock đều running/healthy. Stack được để chạy sau test. Không có egress app ngoài allowlist trong hai harness.

[Sơ đồ logic đã bổ sung giới hạn](gateway-architecture-diagram.html): port 4101 là mock; fallback và alert mặc định tắt. LB failover không bảo đảm mọi request đều thành công; kết quả phụ thuộc loại lỗi, timeout và upstream.

## Chưa nghiệm thu

Provider/Gmail thật, migration PostgreSQL staging, authenticated HTTP/UI E2E, OCR/Marker/LlamaParse, ETL/dashboard và production capacity. Mail best-effort/process-local cooldown; không có durable queue hoặc dedup nhiều worker. Không dùng lời khẳng định “100% production ready”.

## Lệnh đã thực thi

Chạy từ repo Gateway với interpreter app đã cài dependency; giữ nguyên guard và mock credentials local, không in secrets:

```bash
C:/law_insight/.venv-gateway/Scripts/python.exe -B tools/gateway-smoke/harnesses/law_fallback_test.py
C:/law_insight/.venv-gateway/Scripts/python.exe -B C:/Users/teamv/AppData/Local/Temp/law_lb_guarded_retest.py
```

Wrapper thứ hai chạy `law_lb_test.py` hiện có với guard dotenv/egress và Docker allowlist. Đây là file hỗ trợ local trong Temp, chưa nằm trong repo; không dùng bare harness làm lệnh offline an toàn. Kết quả tải mock không đại diện capacity production.

Lượt retest mock đã hoàn tất; chờ người dùng cung cấp tên nhánh cho từng repo trước commit/push. Không stage toàn bộ thư mục: còn nhiều file WIP, artifact FAIL/BLOCKED và dữ liệu smoke lịch sử ngoài phạm vi.
