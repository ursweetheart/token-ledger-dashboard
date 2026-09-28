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

## Chạy tay trên máy dev — 2026-09-28

Đi hết một vòng qua UI trên máy dev (không phải fixture): tạo agent tập `dms-tap` (alias `tap-flash-lite` → `gemini/gemini-3.5-flash-lite`, trần $1) → lưu khoá → xem trước → xử lý drift → áp dụng → cấp key → nối DMS web → Kiểm tra Gateway. Kết quả cuối: Gateway `verified`, usage `verified`. Hai request thử, mỗi cái 6 token / $0.0000062, cả hai vào `fact_call` đúng `dms-tap`. Phần dưới là những gì bộ test cách ly **không** bắt được.

### Lỗi đã sửa (chưa commit)

1. **Regex nhận khoá từ chối khoá Google hợp lệ.** `import_secret` chỉ nhận `[A-Za-z0-9_-]`, còn khoá Google dạng mới bắt đầu bằng `AQ.` (có dấu chấm). Chứng minh khoá `AQ.` dùng được với AI Studio: SpendLogs có 305 lượt `success` tới `generativelanguage.googleapis.com` mang tag `dms-feedback`, lần cuối 20/09. Sửa: thêm `.` vào regex (`connection_worker.py:192`); đổi khoá giả ở `tests/connection_admin_cases.py:68` thành `AQ.dummy-google-provider-key` để test giữ hành vi này. Test chưa chạy lại vì cần fixture Postgres. Giữ regex thay vì bỏ hẳn: khoá đi vào `managed.env` rồi Compose đọc, mà Compose tự thay `$` trong giá trị — không kiểm ở cửa vào thì hỏng âm thầm thành 401 ở provider.

### Phát hiện chưa sửa

2. **Áp dụng xoá toàn bộ chú thích của `config.gateway.yaml`.** Worker ghi lại cả file bằng `yaml.safe_dump` (`connection_worker.py:452`). File có 296 dòng chú thích; sau lần áp dụng đầu tiên chúng mất hết. Không ảnh hưởng runtime, nhưng trên máy chủ thật đây là mất tài liệu vận hành, và file đổi trong git. Không commit bản do worker ghi.
3. **Kiểm tra Gateway gần như luôn ra `inconclusive` giả** — **đã sửa, chưa commit.** Không phải "thỉnh thoảng": 6 lần thử, chỉ 1 lần `verified`; 4 lần `inconclusive` với lý do "Gateway log found; matching ledger usage awaits refresh", 1 lần bị ngắt (`7cb7b29f`). Cả 5 request đều gọi Google thành công và **đều vào `fact_call` đúng `dms-tap`**, chỉ là muộn hơn hạn 60 giây.
   - *Giả thuyết đầu — bị loại:* lượt nạp riêng của worker luôn hỏng (lỗi bị `capture_output` nuốt), chỉ đạt khi `ledger-refresh` 300 giây tình cờ chạy trong 60 giây chờ (≈20%, khớp 1/5). Chạy lại đúng lệnh của worker (cùng Python venv, cùng DSN từ `worker-env.json`): mã thoát 0, 2,1 giây, stderr rỗng, `fact_call gateway 504 → 505 (+1, +6 token)`. Lượt nạp chạy tốt.
   - *Nguyên nhân:* thứ tự. Worker nạp ledger **một lần, ngay vòng lặp đầu** (~2 giây sau request), trong khi LiteLLM ghi SpendLogs **theo lô, vài giây sau** khi trả lời (mục "Hợp đồng image đã đo" đã ghi: log xuất hiện sau flush). Lượt nạp duy nhất chạy khi log chưa có → nạp 0 dòng; `refresh_attempted` chặn nạp lại → hết hạn. Lần `1f49e0d3` đạt vì phải xếp hàng sau `e60a50f5` (worker xử lý từng test một, cũ trước): tới lượt thì log đã ghi từ lâu. Phần "nạp trước khi log được ghi" là suy luận — SpendLogs không lưu giờ ghi dòng — nhưng giải thích đúng cả 6 lần.
   - *Sửa:* trong `drain()` gọi `evidence()` trước; chỉ chạy `refresh_gateway.py` khi đã thấy log (`request_id` có) mà ledger còn `pending`, vẫn đúng một lần. Log chưa có thì chờ vòng sau; không đổi hạn 60 giây, không tăng số lần nạp. Test mới `test_ledger_refresh_waits_for_gateway_log`: chưa có log → không nạp; có log → nạp đúng một lần; vòng sau không nạp lại. `py_compile` đạt; test chưa chạy vì cần fixture Postgres.
4. **`reason` cũ còn lại sau khi đã `verified`** — **đã sửa, chưa commit.** Nhánh `verified` dựng từ `{**result, ...}` mà không ghi đè `reason`, nên câu "Correlated log not uniquely available; waiting for evidence" từ lúc `pending` nằm mãi trong kết quả và trên UI. Thao tác đã kết thúc nên không bao giờ được cập nhật lại. Sửa: nhánh `verified` ghi đè `reason` = "Gateway log and ledger usage match"; `test_live_verified_usage_after_refresh` (đi qua `pending` rồi mới `verified`) thêm phép kiểm `reason` không còn chữ `waiting`/`awaits`. Test chưa chạy lại vì cần fixture Postgres. Thao tác `1f49e0d3` đã lưu trong DB vẫn giữ câu cũ — bản sửa chỉ áp cho lần kiểm sau.
5. **UI im lặng khi Xem thay đổi bị 409.** Bấm "4. Xem thay đổi" khi có drift: API trả 409, UI không hiện gì rõ ràng; người dùng tưởng nút không hoạt động.
6. **Chấp nhận baseline dễ bị bỏ sót / hết hạn.** `review_hash` tính trên cả bản nháp (dòng 342–344): lưu nháp giữa "Xem thay đổi ngoài UI" và "Chấp nhận baseline" làm review hết hạn. Trong lần chạy này hai lần review đều không được chấp nhận (không có dòng `reconcile` trong audit) cho tới khi làm liền hai bước.
7. **Key do UI cấp chỉ được gọi alias của agent** (`models: ['tap-flash-lite']`). Khác quy ước vận hành hiện tại là cấp `models: ["*"]` và dựa vào tag để tách tiền. Form không có lựa chọn; cần chốt quy ước nào đúng.

### Thêm theo yêu cầu người dùng (chưa commit)

- **Biểu tượng từng dòng và dòng tổng kết** trong khung kết quả (`web/js/gateway-connections.js`, hàm `mark`/`summary`). ✅ verified/applied/issued/refresh-complete, ❌ failed/mismatch/recovery-required, ⚠️ inconclusive, ➖ `awaiting-agent-request` (kèm lời nhắc "không tự đổi — cần Request ID từ app"; bản đầu gắn ⏳ khiến người dùng tưởng đang xử lý và ngồi chờ), ⏳ còn lại. Tổng kết chỉ cho thao tác `verify` và chỉ tính Gateway + Usage dashboard — dòng "Ứng dụng agent" bị loại vì image pin không bao giờ cho nó đạt. Chữ cũ giữ nguyên (chỉ thêm tiền tố) nên `browser_check.py` vẫn khớp `Trạng thái: …`. Kiểm: `node --check` đạt; 12/12 trường hợp `mark`/`summary` đạt bằng script tạm; bộ JS sẵn có 117/117 đạt (bộ này không phủ tab kết nối). `browser_check.py` chưa chạy lại.

### Drift khi bắt đầu

Baseline ghi lúc 01:56 (audit `reconcile-env-fingerprint`), trước commit tính năng 02:00. Đối chiếu sha256:

| File | Baseline | Khớp | Hiện tại | Khớp |
|---|---|---|---|---|
| `config.gateway.yaml` | `cd246a` | `539d106` (LF) | `d11e88` | `e66df24` (LF) |
| `entrypoint.sh` | `7a69f1` | `539d106` (LF) | `b77bd9` | `e66df24` (LF) |
| `docker-compose.yml` | `419c66` | không commit nào (LF lẫn CRLF) | `a2baa1` | `e66df24` (CRLF) |

Hai file đầu: chứng minh được — drift do merge `e66df24`. Compose: suy luận — baseline ghi từ bản đang sửa dở chưa commit; bản đó không còn để so. `.env` đổi do thêm `KEY_RALLI`/`KEY_TLA_HD` giả trên máy dev (đã biết, không so được hash vì `deployment_env_digest` bỏ qua một số khoá).
