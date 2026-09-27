## 1. Xác minh hợp đồng tích hợp

- [x] 1.1 Kiểm image LiteLLM được pin, API cấp/thu hồi key, budget và log correlation/provider route trên môi trường cách ly; ghi contract và giới hạn bằng chứng.
- [x] 1.2 Xác minh registry transaction/lock, refresh lock và quyền DB; xác định endpoint host/Docker từ deployment.
- [x] 1.3 Tạo fixture Compose với hai Gateway instance, fake provider và PostgreSQL cách ly cho kiểm thử apply/recovery.

## 2. Hồ sơ và quyền quản trị

- [x] 2.1 Thêm migration additive cho profiles, revisions, operations/stages, audit và grants role ghi riêng; kiểm upgrade giữ lịch sử/pricing.
- [x] 2.2 Thêm admin credential riêng, feature flag mặc định tắt, 401/403 và chặn open mode; giữ quyền API đọc hiện có.
- [x] 2.3 Implement schema/profile API với immutable registry fields, explicit unlimited, model/rate validation và legacy read-only.
- [x] 2.4 Implement expected revision, idempotency key, sanitized audit và operation status API.

## 3. Preview, cấu hình và secret

- [x] 3.1 Implement ownership manifest/baseline và renderer giữ unmanaged routes, global settings và registry entries.
- [x] 3.2 Implement preview không mutation, hashes/drift conflict và explicit reconcile preview.
- [x] 3.3 Implement secret reference adapter, atomic secret storage ngoài repo với ACL, generated environment names và redaction.
- [x] 3.4 Implement registry export/apply adapter dùng parser, transaction/lock hiện có; không migrate/rebuild ngầm.

## 4. Worker apply và vòng đời key

- [x] 4.1 Implement host worker nhận operation ID với allowlist, fixed Compose path, deployment lock và checkpoints; không mount Docker socket vào API.
- [x] 4.2 Implement snapshot/candidate writes, rollout lần lượt hai instance và health/revision/routing checks.
- [x] 4.3 Implement operation issuance riêng qua RPC xác thực trả plaintext trực tiếp, unique operation alias, finite/unlimited per-key quota và lost-response reconcile/revoke trước replacement.
- [x] 4.4 Implement explicit rotation/revocation, phân biệt inactive/disconnect và không xóa history.
- [x] 4.5 Implement crash reconciliation, stage compensation, config restore và recovery-required chặn apply tiếp theo.
- [x] 4.6 Schedule refresh bằng khóa hiện có và lưu trạng thái applied riêng reporting.
- [x] 4.7 Implement Compose override/env_file cho hai instance, managed-key preflight/fixtures, secret version recovery và QUOTA_CHAT_TAGS giữ tag unmanaged.
- [x] 4.8 Giữ registry lock xuyên drift DB/apply/export theo thứ tự deployment→registry; không giả ContextVar truyền qua CLI subprocess.
- [x] 4.9 Implement per-key budget/rotation warnings, zero/unlimited metadata merge giữ tags, read-after-write conflict và single-operator constraint với quota UI cũ.

## 5. UI và verification

- [x] 5.1 Tạo danh sách/hồ sơ và wizard tiếng Việt với validation, preview, thao tác apply và trạng thái từng bước.
- [x] 5.2 Tạo key issuance/rotation/revocation UI, chỉ hiển thị plaintext ở issuance response; không lưu admin credential localStorage.
- [x] 5.3 Sinh template host/Docker, model/X-User placeholders, hai networks và hướng dẫn recreate/fallback/retry.
- [x] 5.4 Implement request thử có thao tác rõ báo khả năng có phí, bounded output và correlation ID; không retry quota 429.
- [x] 5.5 Implement đối chiếu tag/provider route/log/ledger, pending timeout, inconclusive và sanitized evidence.
- [x] 5.6 Implement nhập Virtual Key transient cho test, mapping correlation→request_id→call_id, quota chat 200 detection và verification riêng cho request từ external agent.

## 6. Kiểm chứng và vận hành

- [x] 6.1 Test auth, immutable fields, invalid/wildcard routes, secrets không xuất trong responses/log/audit/templates và preview không mutation.
- [x] 6.2 Test stale revision, drift, concurrent apply, worker restart và lost-response issuance không tạo duplicate effects.
- [x] 6.3 Inject failure ở mỗi stage, đặc biệt instance thứ hai và sau registry commit; kiểm rollback/recovery-required giữ history và pricing.
- [x] 6.4 Test end-to-end single/multiple với fake provider, wrong-tag route, shared key notice, quota 429, missing cost/provider evidence và delayed refresh.
- [x] 6.5 Kiểm UI trong browser: keyboard/form errors, trạng thái chưa có traffic, preview/apply polling, template, key lifecycle và verified/inconclusive.
- [x] 6.6 Viết runbook bootstrap ownership, admin/secret/worker setup, reconcile drift, lost key response, phục hồi và rollback feature.
- [x] 6.7 Chạy checks liên quan của repo và ghi evidence môi trường cách ly; rollout production chỉ khi có chỉ dẫn triển khai riêng.
- [x] 6.8 Test origin đổi không chuyển admin credential, feature thiếu config fail closed, secret delivery cả hai instance, CLI DB drift và registry lock/export race.
- [x] 6.9 Test quota 50/spend 40 rotation không tự reset/copy budget, unlimited giữ metadata, chat 200 không báo success và master key không dùng thay Virtual Key trong test.
