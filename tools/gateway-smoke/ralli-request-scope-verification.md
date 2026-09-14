# Ralli request-scope verification

## Scope

Branch: `api_gateway` (restored to the original name at the user's correction). Changes remain uncommitted in this branch's working tree. This change applies TLA-HD-style usage context at backend router boundaries. It does not deploy a Gateway, change authentication policy, or migrate remaining direct-provider paths.

## Lý do thay đổi và đối chiếu code cũ–mới

Code cũ gọi Gemini trực tiếp và dùng setter để gán principal. Setter dùng ContextVar nhưng chưa tạo active call scope có vòng đời; vì vậy đường router cũ bị identity guard của Gateway chặn trước khi gửi HTTP. Cần nối danh tính do backend xác thực vào toàn bộ chuỗi gọi AI, đồng thời reset khi request kết thúc để không giữ nhầm context.

| File/nhóm | Trước thay đổi | Thay đổi trong commit và mục đích |
|---|---|---|
| `main.py` | `/ask` gọi `set_current_user` rồi xử lý nghiệp vụ | Bọc handler bằng `request_token_usage_context`, chuyển thân xử lý sang `_process_query_scoped`; giữ dispatch cũ nhưng quản lý vòng đời scope |
| `src/routers/assistant.py` | `_set_token_user` không tạo active scope; nuốt lỗi setter | Bỏ helper setter, bọc ask, ask-file và reindex bằng scope của user do guard trả về |
| `src/routers/ctda.py` | Các endpoint AI/admin chưa tạo scope Gateway | Bọc analyze v1/v2, NLP tagging và refresh-data; giữ tham số, quyền và thứ tự xử lý |
| `src/core/token_principal.py` | Có principal ContextVar, chưa đủ correlation/lifecycle Gateway | Thêm ModelCallContext, operation/conversation metadata và context manager reset tokens trong finally |
| `src/core/token_logger.py` (mới) | Chưa có module context/accounting này | Thêm usage context, adapter từ resolved user, normalization và row builder; company/unit/department không trộn lẫn. Row builder không đồng nghĩa persistence đã hoàn thiện |
| `src/core/gemini_client.py` | Shared helper đi SDK Gemini trực tiếp | Thêm façade chọn Gateway/direct, provider dùng scope hiện tại, phân loại lỗi và direct fallback có cấu hình; giữ các entrypoint helper cho caller cũ |
| `src/core/llm_provider.py` (mới) | Chưa có transport OpenAI-compatible | Thêm GatewayProvider, validate cấu hình/identity, gửi X-User và body user theo principal mỗi call; hỗ trợ text/JSON/structured/vision ở tầng provider |
| `src/core/gateway_settings.py`, `llm_errors.py`, `email_alerts.py` (mới) | Chưa có cấu hình/policy Gateway tương ứng | Thêm settings, phân loại lỗi transport đã sanitize và cơ chế cảnh báo có cooldown. SMTP thật chưa được kiểm thử |
| `src/core/llm.py` (mới) | Chưa có helper policy này | Thêm helper/policy dùng trong smoke; không coi kết quả helper này là bằng chứng mọi caller sản phẩm đã migrate |
| `src/core/token_tracker.py` | Mongo sync dùng timeout mặc định; schema usage cũ | Thêm timeout cấu hình, route/agent/fallback/operation/response ID. Có catch rộng cho Mongo và budget trong WIP, cần harden trước production |
| `tests/` | Chưa bao phủ Gateway scope và authenticated route mới | Thêm provider/error/principal/scope/router/ASGI tests; cập nhật fixture có user ID và test AST theo wrapper mới; thêm runner offline chặn dotenv và external egress |

Giữ nguyên auth/RBAC/guest policy, response contract và nghiệp vụ của các router đã bọc. Không có thay đổi triển khai hạ tầng hoặc credential trong commit. Các thay đổi Gateway lõi từ giai đoạn trước được commit cùng phần router theo yêu cầu lưu toàn bộ code; review PASS cuối chỉ bao phủ scope/router, không phải toàn bộ WIP.

**Rủi ro còn mở:** budget đang có catch rộng có thể fail-open; lỗi ghi Mongo có thể bị nuốt; correlation/metadata chưa được chứng minh persist đầy đủ; còn direct SDK bypass và worker chưa migrate. Cần rà lại default model và việc lookup credential chéo repository trong façade cũ trước triển khai. Không dùng commit này như chứng nhận production readiness.

## Full offline suite — known missing-fixture failures

Command: `.venv-gateway-test/Scripts/python.exe tests/run_scope_tests_offline.py -q tests`

Result: **827 passed, 2 failed, 17 warnings in 57.49s**. Missing test-environment packages matplotlib, nbformat and the APScheduler-compatible setuptools were installed in `.venv-gateway-test` before this run; no application dependency manifest was changed.

Both failures are in `tests/test_cnnv_ctda_case_study_snapshot.py`: `test_manifest_keeps_real_links_snapshot_ids_and_verified_numbers` and `test_figures_are_generated_from_the_manifest`. They require the absent source artifact `outputs/ctda-standard-prod-final-20260607-portable-folder/STD-005-so-luong-cong-trinh-dien-ap-mai-thang-5-2026/observation.json`. A repository filename search found no `observation.json`. No replacement data was fabricated, and the tests were not skipped or weakened. Commit remains pending because the user requested completion of testing first.

## Kết quả test — tóm tắt tiếng Việt

**Đã hoàn tất phần bọc request scope giống TLA-HĐ; chưa hoàn tất toàn bộ tích hợp Gateway của Ralli.**

| Hạng mục | Kết quả |
|---|---|
| Bộ test scope, Gateway provider, assistant và CTDA được chọn | 607 passed; một cảnh báo Pydantic cũ |
| HTTP ASGI → JWT/RBAC → router → helper Ralli → Gateway MockTransport | PASS |
| Hai user đồng thời, operation ID riêng, chống giả mạo identity từ client | PASS |
| Reset context khi thành công, exception, cancellation; nested scope và thread inheritance | PASS |
| Hồi quy response contract, upload validation và routing trong bộ test đã chạy | PASS |
| Review độc lập phần scope/router | PASS — không phát hiện lỗi correctness/security mới |
| `git diff --check` | PASS |

Các kết quả trên không chứng minh E2E giao diện, LB/Google thật sau thay đổi router, hoặc ghi usage vào MongoDB thật. Không gộp kết quả smoke Google thật trước đây vào lượt kiểm thử này. Còn các đường Gemini bypass, worker scope và accounting cần hoàn thiện riêng. Chưa commit/push; chưa đổi cấu hình hoặc triển khai hạ tầng.

- `main.py`: `/ask` wraps the awaited legacy handler, including classifier and assistant dispatch.
- `src/routers/assistant.py`: ask, ask-file, and CNNV reindex wrap their awaited business calls.
- `src/routers/ctda.py`: analyze v1/v2, admin NLP tagging, and refresh wrap their awaited work.
- `src/core/token_logger.py`: request context takes the guard-resolved user, keeps company/unit/department separate, creates a per-operation UUID, and restores previous contexts in finally blocks.
- No global activation of `scope_active`; Gateway identity checks remain unchanged.
- Guest/dev access remains subject to existing guards. Those identities are not claimed to be JWT-authenticated humans.

## Verified

Run from the repository root using the existing gateway-test virtual environment:

```bash
.venv-gateway-test/Scripts/python.exe tests/run_scope_tests_offline.py -q tests/test_request_token_context.py tests/test_legacy_request_scope.py tests/test_gateway_authenticated_routes.py tests/test_router_token_scopes.py tests/test_llm_errors.py tests/test_llm_gateway_provider.py tests/test_token_usage_principal.py tests/test_assistant_*.py tests/test_ctda_*.py
```

Latest execution: **607 passed, 1 warning in 19.30s**. Warning: existing Pydantic class-based Config deprecation. `git diff --check` passed.

Coverage includes nested restoration, exceptions, task cancellation, concurrent users, thread inheritance, router metadata, unchanged response contracts, and malformed uploads.

The authenticated ASGI test executes real JWT validation and RBAC guards for `/api/assistant/ask`, with mocked user lookup and permission storage. Its orchestration stub calls the actual AssistantLLMProvider, Gemini helper, and GatewayProvider with an HTTP MockTransport. It verifies `X-User` and body `user`, client identity spoofing resistance, operation isolation, exact `chat:ask` permission, and rejection of expired/malformed/missing credentials or denied roles.

## Boundaries not verified by this change

- No real LB/Proxy/Google calls in this run; no container or credential changes.
- No browser UI or full application startup E2E. Legacy tests execute AST-extracted handler functions to avoid startup schedulers.
- Router service stubs establish scope coverage, not full business execution of every CTDA/upload/reindex path.
- Application usage rows are intercepted in memory, not persisted to real MongoDB. Scope metadata is not proof of durable accounting integration. No new SpendLogs/ETL/dashboard reconciliation.
- Existing direct Gemini bypasses and budget-exception suppression remain separate WIP issues; the full Gateway migration is not production-ready on the strength of these tests.
- No assistant `/stream` endpoint was present in the inspected router. Detached scheduled workers still require explicit worker-lifetime principal scopes.

Independent static review: **PASS**, with no new correctness or security defects found in the scoped router/context changes. The reviewer inspected the tests and passed the scoped diff check; the 607-test execution above was performed by the implementation session, not rerun by this final reviewer. Older Gateway WIP was outside that review.

Người dùng đã đồng ý commit code và báo cáo dù hai test snapshot còn thiếu dữ liệu. Commit vào `api_gateway`, không push; không gắn nhãn toàn bộ test PASS. Các ghi chú “chưa commit” ở phần kết quả phía trên mô tả thời điểm chạy test, không phải yêu cầu trì hoãn commit sau khi được chấp thuận.
