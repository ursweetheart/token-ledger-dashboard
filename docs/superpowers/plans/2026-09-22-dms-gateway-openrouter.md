# DMS → API Gateway → OpenRouter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dùng OpenRouter làm upstream riêng cho DMS qua API Gateway hiện có, giữ attribution/audit/ledger và không làm thay đổi tuyến của agent khác.

**Architecture:** Thêm một alias LiteLLM riêng `dms-openrouter`, giữ nguyên tuyến Google cũ để rollback. DMS tiếp tục sử dụng backend `gateway`, endpoint LB và Virtual Key; OpenRouter API key chỉ tồn tại ở hai Proxy. Không thêm backend OpenRouter, SDK, context manager hay hệ thống accounting mới vào DMS.

**Tech Stack:** LiteLLM fork đã pin trong Compose, Nginx LB, Python/requests/Pydantic/pytest có sẵn trong DMS, PostgreSQL/ETL hiện có. Test cấu hình mới dùng stdlib unittest.

**Spec:** Yêu cầu trong hội thoại này và quyết định người dùng: **DMS → API Gateway hiện tại → OpenRouter**. Hợp đồng tích hợp hiện hành tham khảo `D:/dms-feedback-classification/docs/dms-gateway-fallback/specs/dms-gateway-fallback/spec.md`; phần “Phạm vi đã chốt” bên dưới là specification của thay đổi này. Kế hoạch cũ `.hermes/plans/2026-09-18_135851-dms-public-gateway-test.md` KHÔNG còn là baseline implementation: DMS đã có Gateway.

## Global Constraints

- Chỉ lập kế hoạch trong lượt này. Chưa sửa source/config, chưa đọc secret, chưa chạy test hay generation, chưa deploy.
- Không commit/push/merge nếu chưa được yêu cầu riêng; bước review thay cho auto-commit trong quy trình mặc định của skill.
- Giữ code `dms-feedback`, danh tính actor/JWT, job_id, operation_id, attempt_id và UsageTracker hiện có.
- `FALLBACK_ENABLED=false` cho pilot OpenRouter; không xóa cơ chế fallback Google hiện có. Không tự fallback trực tiếp OpenRouter/Google.
- Bảo toàn `token_ledger`, `token_ledger_v2`, `litellm`, volumes và dữ liệu lịch sử. Không `docker compose down -v`, không recreate Dashboard web/api/pgadmin.
- Synthetic data, no SharePoint/Graph/SMTP/Teams egress khi test; không dump prompt/key/JWT/response headers vào báo cáo.
- Không thêm dependency hoặc generic provider framework.
- Không coi config local, catalog model, status HTML, hay historical reports là bằng chứng live inference.

---

## Phạm vi đã chốt và quyết định còn cần người dùng

### Đã chốt

1. DMS không gọi `openrouter.ai` trực tiếp. Chỉ Gateway gọi OpenRouter qua TLS.
2. Pilot thêm alias `dms-openrouter`, không sửa `gemini-flash-lite`, `gemini-2.5-flash` hoặc route/tag CRM.
3. Key Gateway cho DMS phải có tag duy nhất `dms-feedback` và allowlist alias pilot. Key này khác với OpenRouter provider key.
4. Tái sử dụng Gateway path, actor và audit đã triển khai. Chỉ sửa production Python nếu characterization test chứng minh lỗi tương thích thực tế.
5. Nghiệm thu gồm text extraction và JSON classification qua helper thật, authenticated route và queued worker; accounting có mức bằng chứng riêng.

### Gate cần duyệt trước kích hoạt

- **Model chưa được người dùng chọn.** Ứng viên duy nhất đề xuất trong plan: `google/gemini-2.5-flash-lite`; LiteLLM model string là `openrouter/google/gemini-2.5-flash-lite`. Catalog công khai đã xác nhận ID và hỗ trợ `response_format`, `structured_outputs`, `max_tokens`. Đây không phải xác nhận quyền gọi, chất lượng hay phê duyệt model. Task 1–2 có thể test offline bằng ứng viên; không triển khai live nếu chưa được duyệt.
- Đường dẫn file local chứa OpenRouter key được phép đọc; Virtual Key pilot và user test mapping. Không gửi key qua chat.
- Budget USD và quyền chạy paid smoke. Đề xuất maximum 12 model attempts, deadline 300s, max_tokens 4096/call, concurrency 1; ngưỡng này là đề xuất, không phải quyền tiêu tiền đã cấp.
- TLS endpoint public: tài liệu DMS mới ghi `https://apigateway.rangdong.com.vn:50888/v1/chat/completions`; chưa probe TLS/live ở lượt này. Không dùng lại HTTP của kế hoạch cũ; không bỏ xác minh chứng chỉ.
- Quyền đọc SpendLogs/ledger và cửa sổ rollout; fault injection trên public production cần duyệt riêng.

## Bằng chứng code hiện tại — 2026-09-22

| Repo | Baseline đã kiểm tra | Kết luận |
|---|---|---|
| DMS `D:/dms-feedback-classification` | `ChiThanh`, HEAD `8847ddf71aad85b6254390a82c9b9987024ce3cd`, Git clean | Gateway đã có, khác hoàn toàn baseline của plan trước |
| Gateway `D:/token-ledger-dashboard` | `ChiThanh`, HEAD `cc109c4e0bde2f5c2e10622a46a9cba82d33a514`, có WIP | Không ghi đè WIP Compose/alerts/status UI hoặc directories untracked |

- DMS `service/src/dms/gemini_client.py:103,137`: dispatch Gateway đã tồn tại; `_gateway_request:446` gửi model, user, X-User, timeout, không redirect/adapter retries.
- `GeminiResponse:29` đã có route/response_id/model_actual; client đã ghi attempt audit.
- `service/src/dms/settings.py:43-50`: đã có `GATEWAY_CHAT_COMPLETIONS_URL`, `GATEWAY_API_KEY`, `GATEWAY_MODEL`, `GATEWAY_ALLOW_INSECURE_HTTP`, `GATEWAY_SYSTEM_USER`, `FALLBACK_ENABLED`.
- `classification_worker.py:211-224`: owner_username đã đi vào pipeline khi gateway mode. Không thêm ContextVar hay identity layer lần nữa.
- `service/tests/test_gateway.py`, `test_gateway_pipeline.py`, `test_gateway_usage.py`, `test_gateway_fallback.py` đã tồn tại; `service/tests/offline_runner.py` chặn dotenv/credential và external DNS/network. Tái sử dụng.
- `gemini_client.py:455` gửi `response_format={type: json_object}`; classifier cần array. Đây là **compatibility gate**, chưa kết luận bug đối với OpenRouter khi chưa thử đúng model/Proxy.
- Gateway `docker/gateway/config.gateway.yaml`: DMS hiện có route `gemini-flash-lite` tới Google trực tiếp. Thêm alias mới, không thay route cũ ngay.
- `docker-compose.yml:104` pin image `ghcr.io/ursweetheart/litellm_rang_dong:b7657e95b1650f75551404f62e134ae54dfc5740`. Docs mới không đảm bảo fork này hỗ trợ mọi tham số; kiểm tra wire bằng image này trước.
- CI `.github/workflows/ci.yml:153-185` bắt provider key phải xuất hiện đồng bộ config, entrypoint, Compose và bench. Thiếu một chỗ làm CI/boot hỏng.
- `db/load_gateway.py:258-317` đã tự đăng ký model mới. Không thêm migration/catalog layer chỉ vì có prefix OpenRouter. Cost lấy từ SpendLogs `metadata.cost_breakdown.total_cost`, không mặc định tương đương hóa đơn OpenRouter.
- Tài liệu DMS đang còn các mô tả Vertex fallback/model CRM/HTTP opt-in cũ; không sao chép chúng làm cấu hình pilot.

## File map

| Repo | File | Thay đổi tối thiểu |
|---|---|---|
| Gateway | `docker/gateway/config.gateway.yaml` | Thêm alias pilot riêng, OpenRouter model/key/tag/output cap |
| Gateway | `docker-compose.yml` | Truyền `KEY_DMS_OPENROUTER` trong shared LiteLLM environment |
| Gateway | `docker/gateway/entrypoint.sh` | Thêm key vào startup guard khi route được đưa vào active config |
| Gateway | `docker-compose.bench.yml` | Dummy key cho bench; không inference thật |
| Gateway | `.env.example` | Chỉ blank placeholder sau khi xác nhận template không chứa secret; không đọc/in giá trị có sẵn |
| Gateway | `tests/test_dms_openrouter_config.py` (new) | Guard đồng bộ, route isolation |
| Gateway | `docs/reference/dms-openrouter-pilot.md` (new) | Runbook, security gates, rollback, evidence |
| DMS | `service/tests/test_gateway.py` | Thêm characterize alias/accounting/error contracts và truncated response guard |
| DMS | `service/src/dms/gemini_client.py` | Chỉ sửa finish_reason guard được test đỏ; không rewrite adapter |
| DMS | `docs/dms-gateway-fallback/HUONG-DAN-SU-DUNG.md` | Thêm cấu hình OpenRouter-via-Gateway, sửa ghi chú lỗi thời trong phạm vi này |

Không tạo mới usage_tracker, schema DB, SDK client, provider enum, UI hoặc mail alerts. JSON contract không tương thích thì dừng pilot và lập patch nhỏ riêng có characterization, không đoán schema rồi sửa classifier toàn cục.

## Task 1 — Alias OpenRouter và guard đồng bộ (offline)

**Files:** các file Gateway trong file map, ngoại trừ runbook thuộc Task 4.

**Interfaces:**
- Consumes: `model_list` LiteLLM, shared Compose env, entrypoint required-vars, bench mock env hiện có.
- Produces: alias `dms-openrouter`; provider secret `KEY_DMS_OPENROUTER`; chỉ một identity tag `dms-feedback`.

- [ ] **Step 1: Recheck baseline và đọc đủ các vùng sẽ sửa.** `git status --short`, `git diff -- docker-compose.yml`; đọc `docker-compose.bench.yml` và guidance repo hiện có. Không in diff `.env*`. Read template phải được người dùng cho phép, nếu không thì hoãn riêng việc template và ghi rõ chứ không sửa mù.
- [ ] **Step 2: Tạo test cấu hình bằng stdlib.** Nội dung test khởi đầu:

```python
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DmsOpenRouterConfigTest(unittest.TestCase):
    def test_isolated_route_and_secret_wiring(self):
        config = (ROOT / 'docker/gateway/config.gateway.yaml').read_text(encoding='utf-8')
        routes = re.split(r'(?m)^  - model_name: ', config)[1:]
        selected = [r for r in routes if r.splitlines()[0].strip() == 'dms-openrouter']
        self.assertEqual(len(selected), 1)
        route = selected[0].split('\ngeneral_settings:', 1)[0]
        self.assertIn('model: openrouter/google/gemini-2.5-flash-lite', route)
        self.assertIn('api_key: os.environ/KEY_DMS_OPENROUTER', route)
        self.assertIn('tags: ["dms-feedback"]', route)
        self.assertNotIn('crm-feedback', route)
        self.assertIn('max_tokens: 4096', route)
        for path in ('docker-compose.yml', 'docker-compose.bench.yml', 'docker/gateway/entrypoint.sh'):
            text = (ROOT / path).read_text(encoding='utf-8')
            self.assertIn('KEY_DMS_OPENROUTER', text, path)
        self.assertIn('enable_tag_filtering: true', config)
        self.assertIn('forward_client_headers_to_llm_api: false', config)

if __name__ == '__main__':
    unittest.main()
```

Test text guard không chứng minh YAML runtime; Task 3 kiểm tra image thực. Model assertion thay đúng một lần nếu người dùng duyệt model khác trước implementation.

- [ ] **Step 3: RED.** Từ Gateway root: `python -m unittest discover -s tests -p test_dms_openrouter_config.py -v`. Kỳ vọng fail vì alias chưa tồn tại, không phải lỗi import.
- [ ] **Step 4: Thêm route, giữ nguyên routes khác.** Chèn trong `model_list`, không bên trong `router_settings`:

```yaml
  - model_name: dms-openrouter
    litellm_params:
      model: openrouter/google/gemini-2.5-flash-lite
      api_key: os.environ/KEY_DMS_OPENROUTER
      api_base: https://openrouter.ai/api/v1
      max_tokens: 4096
      tags: ["dms-feedback"]
```

Shared Compose env thêm `KEY_DMS_OPENROUTER: ${KEY_DMS_OPENROUTER:-}`; entrypoint thêm `KEY_DMS_OPENROUTER` vào vòng `for v`; bench thêm `KEY_DMS_OPENROUTER: bench-openrouter-not-a-real-key` tại cùng env anchor với provider keys cũ. Template chỉ `KEY_DMS_OPENROUTER=`. Không thêm `${VAR:?}` vì Compose interpolate cả Dashboard.

Không ghép route OpenRouter vào cùng alias Google cũ: làm vậy routing có thể chọn upstream ngẫu nhiên và che mất phép test. Không bật cross-model fallback.

- [ ] **Step 5: GREEN + review.** Chạy lại test; `git diff --check`; chạy existing CI provider-key guard theo script đã có, không viết guard khác thay thế. Xem diff chỉ rõ alias mới và không đổi CRM routes. Không commit.

**Deploy warning:** Guard mới khiến cả Proxy không khởi động được nếu thiếu OpenRouter key. Chỉ đưa active config vào runtime sau khi secret đã có ở cả hai instances. Không copy active config lên server trước secret provisioning.

## Task 2 — Reuse DMS, khóa response/error contract

**Files:** `D:/dms-feedback-classification/service/tests/test_gateway.py`; `service/src/dms/gemini_client.py`.

**Interfaces:**
- Consumes: `gateway_settings(tmp_path, url, **overrides)`, `endpoint(responses)`, `completion(text)`, `Audit` đã có trong test_gateway.py.
- Produces: unchanged `GeminiClient.generate/generate_json(..., actor, job_id, operation) -> GeminiResponse`; incomplete completions raise existing `GatewayError('response', outcome_unknown=True)` và giữ usage/correlation.

- [ ] **Step 1: Thêm characterization route/usage, không sửa client nếu xanh.**

```python
def test_openrouter_alias_stays_behind_gateway(tmp_path):
    audit = Audit()
    payload = completion('1. NONE')
    payload['model'] = 'google/gemini-2.5-flash-lite'
    with endpoint([(200, payload, {})]) as (url, seen):
        client = GeminiClient(
            gateway_settings(tmp_path, url, gateway_model='dms-openrouter', fallback_enabled=False),
            usage_tracker=audit,
        )
        result = client.generate('synthetic feedback', actor='alice', job_id='job-or')
    assert len(seen) == 1
    assert seen[0][2]['model'] == 'dms-openrouter'
    assert seen[0][1]['X-User'] == seen[0][2]['user'] == 'alice'
    assert result.route == 'gateway'
    assert result.model_actual == payload['model']
    assert result.usage == payload['usage']
    assert audit.events[-1]['response_id'] == payload['id']
```

- [ ] **Step 2: Thêm test đỏ chống kết quả bị cắt nhưng báo success.**

```python
@pytest.mark.parametrize('reason', ['length', 'content_filter', 'tool_calls'])
def test_incomplete_openrouter_completion_is_not_success(tmp_path, reason):
    from dms.exceptions import GatewayError
    audit = Audit()
    payload = completion('[{"row_index":0}]')
    payload['choices'][0]['finish_reason'] = reason
    with endpoint([(200, payload, {})]) as (url, seen):
        client = GeminiClient(gateway_settings(tmp_path, url), usage_tracker=audit)
        with pytest.raises(GatewayError) as caught:
            client.generate_json('synthetic JSON classification', actor='alice')
    assert len(seen) == 1
    assert caught.value.category == 'response'
    assert caught.value.usage == payload['usage']
    assert caught.value.response_id == payload['id']
```

- [ ] **Step 3: RED.** Từ DMS root: `service/.venv/Scripts/python.exe service/tests/offline_runner.py service/tests/test_gateway.py -q`. Existing alias test có thể xanh; test finish_reason kỳ vọng fail vì hiện tại chưa kiểm tra reason.
- [ ] **Step 4: Patch nhỏ trong existing response parsing try.** Sau khi `_gateway_usage` được validate, trước khi return response:

```python
choice = payload['choices'][0]
if choice.get('finish_reason') not in (None, 'stop'):
    raise ValueError
text = choice['message']['content']
```

Dùng existing except để giữ usage/response_id/model_actual, không tự gọi thêm model, không thêm catch rộng. Cho phép `None` để giữ hợp đồng legacy hiện có; live gate vẫn kiểm tra reason thực nhận. Characterize 402 (insufficient credits), 404, 422, 429, 503 và HTTP 200 error envelope bằng bổ sung rows vào existing parametrized tests: 402/404/422 là `request`, không retry; 429 bounded theo code hiện có; 503/outcome_unknown không replay. Không đổi policy Google fallback toàn cục.

- [ ] **Step 5: GREEN + toàn bộ Gateway regression.**

```bash
service/.venv/Scripts/python.exe service/tests/offline_runner.py service/tests/test_gateway.py service/tests/test_gateway_pipeline.py service/tests/test_gateway_usage.py service/tests/test_gateway_fallback.py service/tests/test_gateway_settings.py service/tests/test_gateway_settings_api.py service/tests/test_gateway_logging.py -q
```

Sau đó full suite qua offline_runner, Ruff/Mypy hiện có; phân biệt baseline failures với regression. Không auto-fix file ngoài phạm vi.

## Task 3 — Compatibility test với pinned LiteLLM và fault matrix riêng

**Files:** reuse `tools/gateway-smoke/runtime/compose.lb.yaml`, `runtime/config.yaml`, `harnesses/lb_handoff_test.py` và tests DMS; không copy mock routes vào production config. Artifact mới chỉ trong test output path riêng do harness hiện có sử dụng; đọc harness CLI trước thực thi, không tự đoán flags.

**Interfaces:**
- Consumes: alias/key contract Task 1, DMS client Task 2, exact pinned Proxy image.
- Produces: wire evidence cho Gateway→OpenRouter-compatible mock; PASS/FAIL/BLOCKED cho từng case.

- [ ] **Step 1: Đọc harness/runtime để tái sử dụng startup, temporary Virtual Key, cleanup và SpendLogs queries.** Scope network/ports/volumes test riêng, local-only, không production DB. Không chạy một harness cho agent khác rồi gọi đó là test DMS.
- [ ] **Step 2: Dùng OpenRouter-compatible mock ở test config, key dummy, actual pinned LiteLLM.** Chạy real DMS text/JSON helper. Capture sanitized wire: model `google/gemini-2.5-flash-lite`, output cap, format và Authorization thuộc provider key test chứ không phải Gateway key. Không suy ra header isolation từ kwargs.
- [ ] **Step 3: Characterize JSON trước khi sửa.** Thử actual classifier prompt với array response; xác minh parser trả đúng số hàng và row_index. `json_object` phải được upstream hỗ trợ thực sự, không bị `drop_params: true` bỏ im lặng. Nếu array contract không chạy: đánh FAIL, không thêm json_schema/response-healing/JSON repair library theo phỏng đoán. Xin duyệt patch format nhỏ dựa trên wire/model đã xác nhận.
- [ ] **Step 4: Chạy tuần tự trên stack test cho cả extraction và classification:** baseline → một Proxy stopped → tất cả Proxy stopped → LB stopped → restore trong finally → recovery cùng helper. Xác minh stop state trước probe; không restart song song. FALLBACK_ENABLED=false; không `direct_ai_studio` thành công khi outage. Không replay POST outcome unknown.
- [ ] **Step 5: Assert routes agent khác không đổi, auth/model allowlist và quota còn hoạt động.** Không tạo inference ngoài budget; phase này chỉ mock. Gate phải phân biệt provider selection trong OpenRouter với failover của LiteLLM/Nginx; đây là hai tầng khác nhau.

Không thêm provider-order hoặc routing options chưa kiểm tra tương thích fork. Pilot dùng chính sách OpenRouter mặc định, ghi rõ upstream provider selection chưa pinned; nếu doanh nghiệp yêu cầu provider cụ thể/ZDR thì chưa được phép dữ liệu thật cho đến khi policy đó được duyệt và wire-test.

## Task 4 — Runbook DMS và rollout có kiểm soát

**Files:** Gateway `docs/reference/dms-openrouter-pilot.md`; DMS `docs/dms-gateway-fallback/HUONG-DAN-SU-DUNG.md`.

**Interfaces:**
- Consumes: alias Task 1, compatibility PASS Task 3, phê duyệt model/key/budget/TLS.
- Produces: process-local pilot settings và rollback instructions; không thay production `.env` tự động.

- [ ] **Step 1: Ghi cấu hình không secret vào tài liệu.**

```dotenv
GEMINI_BACKEND=gateway
GATEWAY_CHAT_COMPLETIONS_URL=https://apigateway.rangdong.com.vn:50888/v1/chat/completions
GATEWAY_MODEL=dms-openrouter
GATEWAY_ALLOW_INSECURE_HTTP=false
FALLBACK_ENABLED=false
MAX_RETRY=1
```

`GATEWAY_API_KEY` do local secret source cấp; `KEY_DMS_OPENROUTER` chỉ trên Gateway. Không sao chép OpenRouter key vào DMS. Endpoint là candidate từ docs hiện tại, phải kiểm tra TLS/live trước secret-bearing request. Watcher pilot tắt; manual queued worker dùng owner đã persist. Không gán mọi request vào system user.

- [ ] **Step 2: Sửa lời hướng dẫn dễ gây sai:** không dùng `gemini-2.5-flash` route CRM cho DMS; bỏ HTTP opt-in trong ví dụ TLS; kiểm tra actual fallback implementation trước sửa mô tả Vertex sang AI Studio. Không sửa `.env` hoặc backend mặc định.
- [ ] **Step 3: Trước rollout, operator provisioning key ở cả hai Proxy và Virtual Key pilot model-restricted/tagged/budgeted; kiểm tra image/config/service ownership và TLS từ máy DMS.** Không in resolved Compose environment; `docker compose config --quiet` chỉ syntax. Không tiếp tục nếu key/model chưa được duyệt.
- [ ] **Step 4: Chỉ sau deploy approval, rolling recreate từng Proxy, xác minh readiness rồi generation nhỏ đúng alias trước Proxy tiếp theo.** Không đoán service name từ tên container; lấy tên và ownership từ runtime. Không recreate Dashboard, Redis/Postgres hoặc cả Compose project. Liveness không thay provider test.
- [ ] **Step 5: Paid smoke từ repo DMS:** text route dưới JWT test và file synthetic tối đa 3 rows qua persisted worker; temp DB/input/output/users, disable SharePoint startup restore/sync/output uploads tại harness boundaries. Tổng 12 model attempts và 300s maximum như đề xuất; dừng 401/402/403/model denied thay vì quét model khác. Không bắt buộc hoàn tất ma trận nếu budget hết.

Những bước deployment và paid smoke chưa được người dùng cấp quyền trong yêu cầu lập kế hoạch. Thiếu gate → BLOCKED, không chạy ngầm.

## Task 5 — Đối soát và kết luận pilot

**Files:** cập nhật `docs/reference/dms-openrouter-pilot.md` bằng evidence thực; không sửa DB schema hoặc ETL production mặc định.

**Interfaces:**
- Consumes: DMS audit response IDs/usage, SpendLogs, ETL facts, OpenRouter cost evidence khi được phép.
- Produces: báo cáo tách lớp bằng chứng, không gộp tổng mock và provider-real.

- [ ] **Step 1: Đối soát theo response_id, không theo tổng dashboard.** Poll SpendLogs có deadline; xác nhận tag dms-feedback, end_user, alias/actual model, token details, cache/reasoning, duration và outcome. OpenRouter generation ID có thể khác LiteLLM response ID: kiểm tra mapping thực, không assume hai ID bằng nhau.
- [ ] **Step 2: Kiểm tra provenance/cost.** SQLite DMS là local audit; SpendLogs là Gateway transaction; OpenRouter charged cost là provider evidence riêng. Existing ETL dùng cost_breakdown: phải đo trường này có populated/đúng đơn vị trong pinned fork. Null ≠ zero; không dùng giá Google trực tiếp cho OpenRouter, không sửa historical rows để ép khớp.
- [ ] **Step 3: Xác minh `auto_register_models` với raw OpenRouter model.** Cho phép label provider `openrouter` như source hiện có; phân biệt model vendor và router. Không thêm catalog migration nếu record đã được ingest đúng. ETL rerun idempotency chỉ DB test hoặc lịch được operator duyệt, không tự kích hoạt production ETL.
- [ ] **Step 4: Report:** PASS/FAIL/BLOCKED/NOT RUN theo config, offline tests, pinned Proxy wire, real helper, authenticated app, worker, fault, SpendLogs, ledger, OpenRouter billing. Chưa có billing export thì không gọi đó là full billing reconciliation.
- [ ] **Step 5: Rollback pilot nếu gate lỗi:** ngừng pilot process, khôi phục GATEWAY_MODEL trước đó từ snapshot không secret (không đoán alias); không enable direct fallback. Alias Google cũ còn nguyên. Nếu rollback deployment thì revert đúng phần route/key guard đã thêm theo operator approval, không git reset worktree WIP. Thu hồi key test theo quyền đã cấp và đọc lại trạng thái; giữ evidence, không xóa production SpendLogs.

## Acceptance checklist

- [ ] DMS chỉ gửi đến public Gateway; không mang OpenRouter provider key.
- [ ] Alias mới không đổi routing/quota/identity của CRM và agent khác.
- [ ] RAG text và classifier JSON chạy đúng nghiệp vụ, đủ hàng, không thành công giả khi truncation/outage.
- [ ] JWT/user/job isolation và attempt audit giữ nguyên; không duplicate accounting.
- [ ] Offline + full DMS regression có output thật; pinned LiteLLM/OpenRouter format compatibility có wire evidence.
- [ ] Proxy/LB fault/recovery có evidence trên isolated stack; public fault ghi NOT RUN nếu chưa có maintenance approval.
- [ ] Public pilot bounded và model được người dùng duyệt, TLS verified, no secret leakage.
- [ ] SpendLogs/ledger/cost được đối soát ở mức quyền truy cập thực có; không tự nhận OpenRouter billing đã verified.
- [ ] Không code/config rollout/paid request/commit/push ngoài phạm vi được duyệt.

## Tài liệu tham chiếu và giới hạn retrieval

- https://docs.litellm.ai/docs/providers/openrouter — đọc trực tiếp bằng HTTP thành công: LiteLLM dùng prefix `openrouter/`, upstream mặc định `https://openrouter.ai/api/v1`.
- https://openrouter.ai/api/v1/models — catalog live ngày 2026-09-22 xác nhận `google/gemini-2.5-flash-lite` và supported_parameters; không chứng minh generation account access.
- https://openrouter.ai/docs/guides/features/structured-outputs — retrieval trả 403; không dùng nội dung chưa đọc làm bằng chứng schema hỗ trợ. JSON compatibility phải kiểm ở Task 3.

## Self-review

- Scope người dùng đã chọn được giữ nguyên: DMS → Gateway → OpenRouter, không direct OpenRouter.
- Source được recheck tại HEAD hiện tại; không triển khai lại Gateway adapter/identity/usage đã có.
- Code snippets dùng helper đã đọc hoặc test mới có định nghĩa; chưa giả định SDK/schema API không tồn tại.
- Model chưa được chọn được xử lý bằng gate trước activation, không coi ứng viên là phê duyệt.
- Guard cả hai Proxy và bench được đưa vào cùng task; no secret reads trong planning.
- Các bước có side effect được tách khỏi planning và có approval gate; không có commit/deploy tự động.
