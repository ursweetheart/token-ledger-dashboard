# Law Insight — routing và fallback: nghiệm thu mock 25/09/2026

## Kết luận và phạm vi

**49 stage PASS** qua helper thật của chat, phân tích và OCR PDF scan hai trang/hai
user đồng thời. Topology Docker gồm Nginx LB, hai LiteLLM Proxy và PostgreSQL mock
cô lập. Provider của Gateway là `mock_response`; direct fallback giả lập tại SDK,
không gọi Gemini hay SMTP thật. Không phải nghiệm thu production hoặc capacity.

Evidence canonical: [law-fallback-dd3a479685ff.json](../artifacts/current/law-fallback-dd3a479685ff.json).
Harness: [law_fallback_test.py](../harnesses/law_fallback_test.py).

## Luồng đã kiểm chứng

- Bình thường: helper → HTTP LB `127.0.0.1:4101/v1` → một trong hai Proxy → response
  mock; `X-User` và body `user` từ UsageContext được kiểm tại serialized HTTP send.
- Một Proxy dừng: LB dùng Proxy còn lại, không direct. Trace baseline có hai
  upstream; trace khi một Proxy dừng chỉ có một upstream.
- Cả hai Proxy dừng, LB còn chạy: fallback false truyền lỗi; fallback true thực
  hiện một direct SDK attempt/trang hoặc helper nếu nguyên nhân đủ điều kiện.
- LB dừng hoàn toàn: app không tới được Proxy; false không bypass, true dùng direct
  mock. Direct lỗi thì không có ledger success giả và không retry vòng thứ hai.
- Phục hồi: mỗi request mới thử Gateway trước. Có request recovery và outage lần
  hai cho cả ba modality. Mỗi fault được đọc lại trạng thái stopped, restore được
  kiểm healthy và kiểm bằng request nghiệp vụ tiếp theo.

## Vì sao phải sửa

| Thành phần | Trước → sau | Lý do |
|---|---|---|
| Law Insight `llm.py` | OCR `allow_fallback=False` → `True` | Tái dùng bounded policy của chat/phân tích; flag deployment vẫn opt-in |
| Law Insight `llm_errors.py` | Veto mọi 408 → phân biệt wrapper LiteLLM Timeout không có HTTP response | Fault thật phát hiện SDK tự gán 408 trước nguyên nhân TimeoutError; HTTP 408 thật vẫn bị chặn |
| Tests ứng dụng | Thêm bật/tắt/matrix/concurrency/cancellation và SDK timeout chain | Giữ identity, payload, secret isolation, không bypass auth/quota/TLS |
| `law_fallback_test.py` | Core-only → cả ba modality, hai Proxy down, wire/SpendLogs/cleanup | Không kế thừa fault coverage text cho OCR bằng suy luận |
| `run.py` | State cố định system temp → `SMOKE_STATE_FILE` hoặc scratch | Giữ credential mock ngoài Git và đúng profile scratch |

Không thay model nghiệp vụ/default config, parser/router/schema, không thêm
circuit breaker hoặc dependency. App config handoff tiếng Việt nằm trong repo
Law Insight `backend/GATEWAY.md` và `gateway-fallback.env.example`.

## Kết quả và tầng bằng chứng

| Phép đo | Kết quả |
|---|---:|
| Stage/helper invocation được kiểm | 49 PASS |
| Phân tích / chat / OCR stage | 13 / 13 / 23 |
| Gateway SDK attempts / HTTP send attempts | 68 / 68 |
| Request có LB receipt trace | 44 |
| Direct SDK mock attempts | 24 |
| Ledger rows dựng trong memory | 48 |
| Gateway responses khớp SpendLogs theo ID/user/token/tag | 30 |
| Direct responses thành công, không có SpendLog riêng | 18 |
| Unmatched failed SpendLogs ở lần đọc cuối | 0 |
| SMTP attempts / blocked external-egress attempts | 0 / 0 |
| Focused tests ứng dụng sau sửa classifier | 274 passed, 24 warnings, 17.34s |

Không đồng nhất send với receipt: request lúc LB dừng có thể không đến LB; OCR
cancellation cũng có thể xuất hiện HTTP 499 hoặc outcome chưa rõ. Artifact giữ
`ambiguous_gateway_http` và `lb_unreturned_requests`. Không tuyên bố exactly-once
hoặc không thể tính phí hai lượt khi timeout.

**Lưu dữ liệu:** 30 Gateway SpendLogs được persist ở DB mock `litellm_smoke` và
đối soát bằng response ID, username, prompt/completion/total tokens, tag `tla-hd`.
48 app rows chỉ dựng bằng builder thật trong memory, không persist DB Law Insight.
Direct mock không tạo SpendLog Gateway riêng; trong thực tế Gateway attempt trước
fallback vẫn có thể đã xử lý. ETL, `token_ledger_v2`, Dashboard và cloud billing
không được kiểm chứng bởi kết quả này.

## Môi trường và cleanup

- App base commit: `39b9a719e614a8e8702282932282ff24aab25091`, cộng local diff.
- Gateway base commit: `e4faf22f75f95b094f322beb3bb2508851f980c2`, cộng local harness diff.
- Docker Desktop local; image `tla-gateway-smoke:py313`, `nginx:alpine`,
  `postgres:16-alpine`; network mock `internal=true`, chỉ LB publish loopback 4101.
- Khôi phục stack cũ sau khi network mất/bind mounts lỗi thời; chỉ recreate
  service mock, giữ volume `tla-gateway-smoke_smoke_pg` và credential tương ứng.
  Không chạy Compose root hoặc đụng các DB/ứng dụng đang chạy khác.
- Key test tạo với alias/run ID, tag và model allowlist được đọc lại; thu hồi
  trả **200**, đọc key sau thu hồi **404**.
- Kết thúc: LB, hai Proxy, DB mock **healthy**, cleanup errors rỗng. Không commit,
  push, thay `.env` ứng dụng hoặc deploy server.

Các run FAIL trước đó được giữ làm debug, không thay evidence PASS: guard Windows
cần chấp nhận audit executable `None` nhưng vẫn kiểm exact Docker command; fault
hai Proxy phát hiện lỗi synthetic 408 đã nêu. Không đổi expected failure để ép xanh.

## Tái chạy an toàn

Chỉ dùng sau khi inspect đúng stack/volume/network mock và có state khớp; không
chạy cùng fault harness khác. Dùng venv Law Insight và scratch được chỉ định:

```bash
D:/law_insight/.venv-gateway/Scripts/python.exe -B D:/token-ledger-dashboard/tools/gateway-smoke/harnesses/law_fallback_test.py --self-check
TMPDIR='D:/Hermes/profiles/api-gateway/cache/scratch' SMOKE_STATE_FILE='D:/Hermes/profiles/api-gateway/cache/scratch/tla-gateway-smoke-state.json' D:/law_insight/.venv-gateway/Scripts/python.exe -B D:/token-ledger-dashboard/tools/gateway-smoke/harnesses/law_fallback_test.py
```

State là credential mock local, không đưa vào artifact/Git. Không chạy harness OCR
cũ `law_ocr_lb_test.py` để thay bằng chứng mới: nó còn unsafe imports và assertion
outage nằm trong broad catch; matrix mới không dùng harness này.

## Review cuối

Review độc lập classifier, regression tests, guard/fault harness, cleanup và
artifact không phát hiện vấn đề correctness/security blocking. Reviewer đọc và
đối soát artifact; không chạy lại runtime. Parent đã chạy tests và fault riêng.

## Chưa nghiệm thu

- Direct HTTP attempt count/payload tại provider thật: **NOT MEASURED**, SDK mock.
- Provider-real text/JSON/vision, endpoint/TLS/key/alias server: **NOT RUN**.
- Full backend suite: lượt trước **11 collection errors** do dependency/test stubs;
  không gọi focused PASS là full PASS; chưa sửa ngoài scope.
- KB worker short-output dưới 50 ký tự còn rơi sang local extractors; gap sẵn có,
  không sửa router trong scope này. Parser riêng có kiểm short-output fail-closed.
- Authenticated full-app/UI E2E, persistence app, ETL/dashboard và billing: **NOT RUN**.
- Kết quả JSON mode trong mock chứng minh options/payload, không chứng minh chất
  lượng JSON nghiệp vụ từ model thật.
