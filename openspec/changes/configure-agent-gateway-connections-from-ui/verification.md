# Tự soát artifacts — 2026-09-26

Áp dụng `.claude/skills/tu-soat/SKILL.md`: đọc lại toàn bộ artifacts, chạy validator lát mỏng, phân loại phát hiện, sửa và đọc lại, chạy kiểm tra trên toàn bộ change. Đây là soát proposal/design/specs/tasks; chưa có implementation để kiểm runtime. Không gọi provider, migrate, refresh hay thay đổi Gateway đang chạy.

## Phát hiện và sửa

1. **Quota tính theo key, không cộng gộp agent.** `backend/gateway.py:quota_of/spend_of` và `docker/gateway/quota_hook.py:decide_action` đọc metadata/spend của từng key. Sửa nhãn quota, ngân sách replacement rõ ràng; ví dụ quota 50/spend 40 không tự cấp lại 50 khi rotate.
2. **Unlimited không được adapter số hiện tại hỗ trợ.** `set_quota` nhận số, `_merge` giữ metadata. Bổ sung adapter gỡ quota_usd giữ tags, audit; chấp nhận zero theo parse_amount hiện có.
3. **Apply async chưa có đường trả plaintext key.** Tách issuance live response qua worker RPC khỏi apply polling; bổ sung reconcile alias theo operation và revoke trước replacement khi mất response/crash.
4. **Secret chưa đến environment container chỉ bằng lưu file.** Compose liệt kê KEY_GOOGLE_AI_STU/KEY_CRM_FEEDBACK; entrypoint có danh sách biến bắt buộc cố định. Bổ sung override/env_file/preflight/dummy fixtures cho cả hai instance và rollback secret version. Đối chiếu tên service thật là litellm-1/litellm-2.
5. **Drift registry và khóa export chưa đủ rõ.** `operation_lock` là advisory lock theo session, ContextVar chỉ trong process. Bổ sung giữ lock xuyên re-read/apply/export, kiểm DB drift, thứ tự khóa và không dựa vào subprocess thừa kế ContextVar.
6. **Test từ worker chưa chứng minh external agent hoạt động.** Tách Gateway verified và External agent verified; external cần traffic từ ứng dụng đó. Bổ sung Virtual Key transient thực, không test bằng master key.
7. **Correlation không tự ánh xạ thành request_id.** `db/load_gateway.py` lấy request_id và ghi fact_call.call_id; query hiện không cung cấp bằng chứng provider route. Bổ sung yêu cầu chứng minh mapping và inconclusive nếu thiếu trường route.
8. **Quota chat có thể trả HTTP 200.** Hook có BLOCK_CHAT/BLOCK_BATCH; Compose có QUOTA_CHAT_TAGS. Bổ sung quota_response_mode độc lập identity mode, render danh sách chat tags và không coi quota message 200 là AI success.
9. **Admin origin/fail-closed và race metadata chưa có hợp đồng rõ.** Main/API-access-control có Bearer/compare_digest, giới hạn backend origin; set_quota nêu read-modify-write race. Bổ sung origin binding, feature config fail closed, metadata baseline/read-back và giới hạn single operator; không tuyên bố CAS chưa tồn tại.

Các mục trên là lỗi/thiếu sót artifacts, đã sửa trong proposal/design/specs/tasks. Không hạ requirement verified để log thiếu vẫn thành công.

## Kiểm chứng

- Đọc lại 6 artifacts chính: proposal, design, tasks và 3 specs, cùng các đoạn source liên quan.
- `openspec validate configure-agent-gateway-connections-from-ui --strict`: đạt trước và sau sửa; lần trước đạt nhưng không phát hiện các thiếu sót ngữ nghĩa trên.
- `openspec status --change configure-agent-gateway-connections-from-ui`: 4/4 artifacts complete; đây là ready về artifacts, không phải implementation complete.
- Soát toàn bộ change bằng kiểm tra cấu trúc riêng: 7 file Markdown, 3 specs, 16 requirements có SHALL/MUST và scenario, 33 scenarios, 35 tasks chưa triển khai; không có trailing whitespace trong change.
- `git diff --check` toàn workspace phát hiện 14 dòng trailing whitespace có sẵn trong thay đổi của `gateway-connection-simple-english.md`, ngoài change này. Giữ nguyên, không sửa ngoài phạm vi. Change mới đang untracked nên diff check không bao phủ nó; kiểm whitespace trực tiếp tất cả file markdown của change.

## Chưa chứng minh

- API key issuance/revocation, correlation fields và provider route evidence của image LiteLLM pin cần kiểm runtime trên fixture cách ly ở tasks 1.1–1.3.
- Environment override, recovery, key delivery và metadata read-back là thiết kế cần implementation và fault tests, không phải khả năng đã chạy.
- External traffic có correlation là bằng chứng tích hợp vận hành; không thay xác thực danh tính người thật. Quota vẫn có cache lag theo hook hiện tại.
- Không kiểm trạng thái database/Gateway live. Kết luận: artifacts nhất quán hơn với source đã đọc và đạt kiểm cấu trúc; không chứng nhận toàn bộ tính năng hoạt động trước khi implement/test.

## Implementation audit — 2026-09-26

Phần dưới cập nhật kết luận sau apply; mục “Chưa chứng minh” phía trên ghi trạng thái tại thời điểm proposal. Áp dụng tiếp skill tu-soat: đọc code, chạy lát mỏng, sửa nguyên nhân đã chứng minh rồi chạy suite đầy đủ. Không triển khai production.

### Lỗi implementation đã phát hiện và sửa

- Bảng quản trị mới cần được bảo vệ khỏi legacy rebuild; guard chặn ngay khi có draft profile. Giữ nguyên các kiểm tra truncate/order cũ và cập nhật kỳ vọng cho preflight mới.
- ACL Windows có OWNER RIGHTS SID; chỉ chấp nhận SID này khi owner chính là tài khoản worker. Không bỏ kiểm ACL hoặc cho phép Everyone.
- API pinned giới hạn key-list size 100; lookup dùng exact alias filter thay vì yêu cầu size vượt hợp đồng.
- Call cost dùng NUMERIC không giới hạn scale, khác daily rollup NUMERIC(14,6). Bỏ phép làm tròn sai ở verifier; so sánh Decimal với giá trị thực ghi trong fact_call. Fixture chứng minh 4 tokens và cost 0.0000049999999999999996 khớp log/ledger.
- Applied profile, baseline và terminal operation checkpoint được commit cùng transaction. Restart trước checkpoint phục hồi snapshot, cập nhật baseline với registry đã commit và không replay rollout mù.
- Secret import từ chối external file drift; không tự chấp nhận baseline sau khi file bị sửa ngoài worker. Budget crash marker cũng kiểm quota hiện tại trước khi kết luận operation hoàn tất.
- Browser: sửa layout thừa cột, trạng thái profile quá dài, model fields trùng tên và lựa chọn key làm mất plaintext response. Credential và transient test key không lưu localStorage.
- Fixture sau force-recreate phải chờ cả hai Gateway healthy trước test live. Lỗi issuance lúc container chưa ready được phân loại là readiness của fixture; thêm health gate, không retry issuance/billable request.

### Bằng chứng đã chạy

- Full stdlib repository suite: **197 tests passed**.
- Targeted existing Node suites: **19 tests passed**; JS syntax và Python compile checks đạt.
- New full suite: **39 tests + 5 subtests passed**, gồm schema/auth, disposable PostgreSQL, real pinned key APIs, single/multiple usage→refresh→ledger, quota chat, restart/lost response, drift, recovery và additive migration. Sau đó bổ sung **3 fault tests passed** cho render/override/registry transaction; export-after-commit test kiểm registry lock còn giữ xuyên export.
- Migration fixture tạo database tên UUID riêng, seed usage/pricing trước upgrade 014→015, so sánh đầy đủ rows sau upgrade và kiểm role quản trị không ghi facts. Database này được xóa sau kiểm tra; không rebuild ledger hiện có.
- Hai instance LiteLLM thực được force-recreate trong project `gateway-connections-test`; worker kiểm health, mounted config bytes, loaded managed model IDs và secret env của cả hai. Chỉ dùng fake provider và dummy keys, không gọi Google.
- Quota batch 0 trả 429; chat 0 trả 200 nhưng không có provider/call headers và được báo quota-blocked. Quota 50/spend 40 giữ nguyên khi replacement được cấp ngân sách explicit 10; unlimited giữ routing metadata; restart budget không gửi update lần hai.
- Real Chromium UI check với HTTP fixtures đạt: keyboard login, native invalid form, multi-model draft, preview invalidation, apply polling, key copy/clear/revoke, template, verified/inconclusive display, origin change và credential isolation. Browser fixtures không được coi là live API end-to-end; backend/live Gateway kiểm riêng ở integration suite. Screenshot được xem trực tiếp.
- OpenSpec strict validation đạt; scoped diff whitespace check đạt. Thay đổi ngoài phạm vi của người dùng được giữ nguyên.

### Giới hạn và vận hành

- Feature mặc định tắt. Production còn cần migration 015, credential/role riêng, restricted secret directory, explicit host worker config và bootstrap theo `docs/reference/gateway-connection-management.md`. Không tự chạy những bước này trên production.
- Image pin không lưu bằng chứng đáng tin cậy về provider route/origin cho external traffic: external verifier trả inconclusive sau khi kiểm tag/identity; request do worker tạo bị từ chối làm bằng chứng external. Không nới tiêu chí verified.
- Không có CAS cho quota API cũ; yêu cầu một operator, read-before/read-after kiểm xung đột có thể quan sát. Cache lag quota vẫn theo hook hiện có.
- Suite có một deprecation warning từ Starlette/httpx, không có failure. Disposable fixture được shutdown sau kiểm chứng; không lưu plaintext key trong artifacts.
