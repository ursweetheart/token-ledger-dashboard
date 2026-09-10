# Law Insight → LB → Gateway: kết quả kiểm thử mock

Run đã đối soát: `law-lb-9cc2d0ed8f4f`.

## PASS trong phạm vi helper

- Helper thật `call_llm` và `call_llm_chat` → `http://127.0.0.1:4101/v1` → Nginx → hai LiteLLM Proxy mock → PostgreSQL `litellm_smoke` cô lập.
- 93 request thành công, 93 response ID duy nhất, 93 SpendLogs; 8 username giả lập, 2.790 token mock. Khớp username, request ID, prompt/completion/total token và tag `tla-hd`; không có chuỗi canary trong các trường SpendLogs đã kiểm tra.
- Trace Nginx thấy `X-User` trên từng request; 50 request tới Proxy thứ nhất, 42 tới Proxy thứ hai, 1 failover từ thứ hai sang thứ nhất.
- Thiếu identity ở cả hai helper: reject trước SDK/network.
- Virtual Key sai: HTTP 401 ở LB, không bypass.
- Dừng Proxy thứ hai: 8/8 request thành công. p95 khoảng 2.015 ms do timeout/failover.
- Dừng LB: một lượt gọi SDK thất bại sau khoảng 2,074 giây, không gọi direct provider; khởi động lại LB và 4/4 request phục hồi.
- Key tạm đã xóa; đọc lại `/key/info` trả 404.
- Các container mock healthy sau bài test; không thay đổi runtime production.

## Tải thăm dò (closed-loop, không phải capacity)

| Concurrency | Request | p95 (ms) |
|---|---|---|
| 1 (cold) | 1 | 715,8 |
| 2 | 8 | 93,5 |
| 4 | 24 | 26,0 |
| 8 | 48 | 801,6 |

Mẫu rất ngắn và chỉ mock. Không suy ra throughput/SLA production từ các số này. Chỉ chụp tài nguyên trước/sau, không đo peak CPU/RAM. Không có Redis/Sentinel trong topology này.

## Chưa được chứng minh

- Username được đặt bằng UsageContext giả lập; chưa đăng nhập qua router thật hoặc test JWT giả mạo end-to-end.
- Application usage row builder thật, nhưng persistence bị intercept: không chứng minh ghi application DB.
- Chưa ETL vào token_ledger_v2, mapping user/phòng ban hoặc dashboard.
- Chưa chạy pipeline hợp đồng, OCR/Marker/LlamaParse hoặc provider Google thật.
- Không dùng credentials provider; mock config dùng upstream loopback cổng không phục vụ, Proxy chỉ gắn mạng internal. Guard của harness từ chối lời gọi SDK ngoài URL LB và model mock.

## Hai lần thử trước

- `law-lb-2cc1291b619b`: harness không nhận loại InternalServerError do LiteLLM ánh xạ connection refused. Request đã fail closed; sửa nhận diện exception trong test, không sửa app.
- `law-lb-348a49a72977`: assert hai upstream bắt đúng tình trạng Proxy thứ hai còn starting sau fault test. Thêm chờ health từng Proxy và reload LB trước chạy lại; không bỏ assert hai upstream.

## Artifact và chạy lại

- `law-lb-9cc2d0ed8f4f.json`: full per-request results, SpendLogs, trace, metrics.
- `compose.lb.yaml`, `nginx.lb.conf`: extension test, không sửa Compose production hoặc stack smoke cũ.
- `law_lb_test.py`: gọi helper thật và thực hiện fault injection chỉ vào container mock có tên cố định.
- Chạy từ `C:/law_insight`: `.venv-gateway/Scripts/python.exe C:/token-ledger-dashboard/tools/gateway-smoke/law_lb_test.py`.
- Cần stack smoke gốc và hai service bổ sung healthy trước test. Không chạy harness trên production hoặc thay hostname/DB bằng target thật.
