# Periodic Model Catalog Sync & Manual Pricing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quét định kỳ toàn catalog model/giá OpenRouter cho mọi agent, có màn hình sửa đơn giá theo provider/model, bảo vệ giá nhập tay và tính lại phần cost ước tính theo ngày áp dụng.

**Architecture:** Catalog đồng bộ và manual overrides là hai lớp dữ liệu riêng. Scheduler dùng vòng refresh hiện có, một selector giá dùng chung ở backend; không để UI tự tính theo giá latest. Giá manual thắng giá tự động trong khoảng ngày được chọn, đồng bộ không sửa override; cost gốc không bị ghi đè.

**Tech Stack:** Python stdlib urllib/json/decimal, PostgreSQL, Alembic, FastAPI, JavaScript và test runners hiện có. Không SDK, queue, scheduler service hoặc framework mới.

**Spec:** Mục 1 của tài liệu này là spec theo yêu cầu người dùng vừa xác nhận: quét model/giá định kỳ và vẫn chỉnh được giá thủ công. Thay thế cả `2026-09-22-openrouter-model-pricing-discovery.md` và `2026-09-22-dms-gateway-openrouter.md`; không thực hiện hai kế hoạch cũ.

## Global Constraints

- Lượt hiện tại chỉ viết/rà soát kế hoạch; việc triển khai chờ người dùng duyệt.
- Không đổi inference route, không sửa repo DMS hoặc agent khác; không thêm OpenRouter key vào Gateway.
- Đồng bộ toàn catalog, kể cả model chưa có usage; catalog availability không tự cấp quyền gọi hoặc bật route Gateway.
- Giữ `token_ledger`, `token_ledger_v2`, `litellm`, dữ liệu lịch sử, volumes và WIP. Không drop/rebuild DB, không tác động Dashboard/Gateway runtime khi chưa được duyệt.
- Manual price là đơn giá USD/triệu token, không phải thao tác sửa hóa đơn hay số token.
- Không tự commit/push/deploy; migration production và scheduler activation cần duyệt riêng.
- Mọi source mới phải có provenance, timestamp, unknown/stale status; không đổi null thành zero.

---

## 1. Phạm vi và hành vi để phê duyệt

### 1.1 Đồng bộ tự động

- Default đề xuất **24 giờ**, chỉnh trong Settings, giới hạn **1–168 giờ**; nút “Đồng bộ ngay”.
- Fetch duy nhất `https://openrouter.ai/api/v1/models`, fixed HTTPS, không auth, không inference. Một request catalog cho tất cả agent, không một request mỗi agent/model.
- Thêm model mới, cập nhật metadata/giá tự động, lưu lịch sử giá thay đổi. Model biến mất được marked unavailable, không xóa lịch sử/usage/manual price.
- Model hiển thị theo publisher/vendor namespace của catalog ID; không tuyên bố đây là danh sách hosting provider endpoints của OpenRouter. Giá endpoint-specific không được suy ra từ giá catalog chung.
- Catalog external riêng, không đổ tất cả model OpenRouter vào dim_model và làm bẩn dropdown usage. Link với dim_model khi model thực sự có usage hoặc khi operator xác nhận mapping.
- Giá lỗi/missing: vẫn lưu model, trạng thái missing/unsupported; không coi là free. Model không có trên OpenRouter vẫn hiển thị nếu đã có trong local dim_model và vẫn được nhập giá tay.
- Scheduler không chạy trong mỗi FastAPI worker; reuse `scripts/refresh_gateway.py` heartbeat loop. Check due độc lập với bước load SpendLogs: ingest lỗi không chặn catalog sync và ngược lại.

### 1.2 Hai lớp giá, không ghi đè lẫn nhau

Trong màn hình quản lý giá hiển thị:

`Provider | Exact model ID | Giá tự động | Giá chỉnh tay | Giá đang áp dụng | Nguồn | Ngày áp dụng | Lần sync | Trạng thái`

Thứ tự **estimate**:

1. Manual override có hiệu lực.
2. Giá chính chủ legacy phù hợp ngày nếu có.
3. Snapshot OpenRouter phù hợp ngày nếu có.
4. Unknown nếu không có giá đủ điều kiện.

Cost đã ghi nhận được giữ riêng và hiển thị ưu tiên theo contract nguồn hiện tại; manual/OpenRouter không viết đè `fact_call.cost_usd`, SpendLogs, hóa đơn hoặc Gateway quota spend.

- Manual nhập input/output bắt buộc, cache-read optional; phần chưa hỗ trợ như cache-write/tier/audio/search không được ngầm miễn phí.
- Save full override, không tự merge từng field với catalog mới. Nhờ vậy sync không thay đổi ngầm một phần giá manual.
- “Dùng lại giá tự động” tạo một phiên bản trạng thái auto có hiệu lực từ ngày chọn, không xóa override lịch sử.
- Sync vẫn cập nhật giá tự động trong khi manual đang có hiệu lực để người dùng thấy chênh lệch.

### 1.3 Ngày áp dụng và tính lại

- Bản đầu dùng **ngày nghiệp vụ Asia/Ho_Chi_Minh**, khoảng `[from_day, to_day)`; UI nhãn ngày kết thúc bao gồm ngày đó, API chuyển thành exclusive end nhất quán. Không hứa hỗ trợ đổi giá giữa giờ khi usage hiện theo ngày.
- Manual mặc định từ hôm nay, UI nói rõ áp dụng toàn bộ ngày. Có thể chọn khoảng quá khứ, bắt buộc preview tác động và xác nhận.
- Auto snapshot mới có hiệu lực từ đầu ngày nghiệp vụ kế tiếp ngày quan sát; không giả rằng giá mới đã tồn tại trước lúc fetch. Ngày hiện tại có snapshot cũ thì dùng snapshot đó; không có thì unknown.
- Manual save thành công → invalidate response cache nếu có → fetch lại usage trong range đang chọn → estimate được tính lại khi đọc. Không chạy ETL rewrite token/facts và không job recompute toàn database.
- Preview trả số rows affected, old/new known subtotal và unknown counts; không ép tổng incomplete thành số đầy đủ. Ngày không có usage vẫn lưu schedule, ảnh hưởng rows=0.
- Lịch sử cost ước tính có thể thay đổi đúng khoảng override đã xác nhận; giá auto mới không tự định giá lại quá khứ.

### 1.4 Quyền sửa — giới hạn xác thực hiện có

`backend/main.py:54-74` hiện dùng một Dashboard key chung, không có Admin/User. Không gọi màn hình này “admin-only” khi chưa có RBAC.

Đề xuất tối thiểu: reuse `caller`, mutation pricing chỉ khi `PRICING_WRITE_ENABLED=1` và `Principal.kind != open_mode`. Default tắt. Khi bật, **mọi người giữ Dashboard key đều có quyền sửa giá**. Audit ghi principal shared_key chứ không bịa danh tính cá nhân. Người dùng cần chấp thuận giới hạn này; nếu yêu cầu quyền riêng từng người thì tách auth/RBAC thành scope khác, không lén thêm vào dự án pricing.

## 2. Baseline và những gì tái sử dụng

Repo `D:/token-ledger-dashboard`; HEAD `cc109c4e0bde2f5c2e10622a46a9cba82d33a514`, branch ChiThanh, có WIP đã tồn tại. Không đọc secrets. Chưa xác minh schema/runtime live.

- `db/load_gateway.py:258`: auto_register_models đã tồn tại.
- `db/migrations/sql/001_baseline.sql:586`: ref_price legacy USD/1M, PK model/day, không chứa raw catalog hoặc override audit.
- `backend/store.py:121`: catalog hiện trả giá latest; không dùng lại cách này để định giá lịch sử.
- `backend/main.py:219,498`: caller và write endpoint quota đã có; reuse auth pattern, không reuse Gateway master key cho pricing.
- `scripts/refresh_gateway.py`: vòng loop có sẵn, không thêm scheduler độc lập.
- `web/js/app.js:4411`: đã có renderPricing/input handlers, nhưng đây là state local, chưa chứng minh lưu DB; nối UI hiện có với API, không coi localStorage/state là persistence.
- `web/js/app.js:735,443`: tổng quan và account có công thức riêng; phải quy về backend estimate contract.
- `web/js/api.js:378`: null rate đang đổi thành zero; không giữ hành vi này cho contract mới.
- Migration head source: `012_nhip_tim_lam_moi`; recheck trước chọn số 013.

## 3. Data model và API contract tối thiểu

### 3.1 Ba bảng mới, giữ ref_price legacy

1. `ref_model_catalog`: catalog_key PK, nullable local_model_id FK, openrouter_id unique nullable, provider, display_name, available, first_seen_at, last_seen_at, metadata JSONB, revision bigint. External key `or:<exact-id>`, local-only `local:<model_id>`; link external↔local phải unique rõ ràng, không auto merge tên giống nhau.
2. `ref_model_price_version`: id, catalog_key FK, source (`openrouter`/`manual`), mode (`price`/`auto`), valid_from DATE, valid_to DATE nullable, observed_at, pricing JSONB, pricing_hash, principal, reason. Append-only. Manual version ID lớn hơn thắng trong interval overlap; UI preview phải giải thích thay override cũ. Auto selector bỏ mọi manual khi gặp bản manual mode=auto có ưu tiên cao nhất. Không delete lịch sử.
3. `ref_price_sync_state`: singleton, enabled default false, interval_hours default 24, last_attempt/success, next_due, lease_token/lease_until, status, last_error_class, catalog_generation/revision. Dùng lease DB để tránh hai process fetch cùng lúc, không giữ transaction trong lúc network.

Một model chung dùng chung giá cho tất cả agent. Rate override theo route/agent chưa nằm trong scope; UI phải cảnh báo sửa model ảnh hưởng mọi agent dùng model đó. Không import catalog thành enabled Gateway deployments.

### 3.2 Endpoints mới (proposal, chưa tồn tại)

- `GET /api/pricing/models?provider=&q=&offset=0&limit=50`: paginated catalog, source/current rates/local linkage/status; max limit 200.
- `GET /api/pricing/history?catalog_key=...`: history paginated.
- `POST /api/pricing/preview?catalog_key=...`: validate proposed price/auto mode, return impact + model revision. Read operation vẫn auth; không tạo state.
- `POST /api/pricing/versions?catalog_key=...`: same payload + expected_revision + `confirm_retroactive`; optimistic lock, append, commit, read exact saved version back. Stale →409, no lost edits.
- `GET /api/pricing/sync`: state/interval; `PUT /api/pricing/sync`: enabled/interval validation.
- `POST /api/pricing/sync`: marks due, returns 202; worker thực hiện, không fetch catalog trong request UI. Return worker heartbeat để không hứa chạy ngay khi worker offline.

Payload giá mới:

```json
{"mode":"price","input_per_million":"0.10","output_per_million":"0.40","cache_read_per_million":null,"from_day":"2026-09-22","to_day":null,"reason":"Giá theo hợp đồng","expected_revision":3,"confirm_retroactive":false}
```

Manual mode auto không mang rates. Amounts decimal strings, reject bool/negative/NaN/Infinity/scientific extremes; finite precision/size cap. Không route API chứa URL fetch do client cung cấp (SSRF). catalog_key truyền qua URLSearchParams, không qua path segment; test HTTP thực giữ nguyên `/`, `:` và ký tự cần encode.

## 4. File map

| File | Thay đổi |
|---|---|
| New `db/model_pricing.py` | Parse/match/select/estimate pure functions và DB price access, không generic provider framework |
| New migration SQL/Python `013_model_catalog_pricing` | Ba bảng + indexes/checks, forward-only |
| New `scripts/sync_model_catalog.py` | Fixed-URL bounded fetch, sync lease/snapshots, CLI dry-run/apply |
| `scripts/refresh_gateway.py` | Due-check độc lập ingest, scheduler heartbeat |
| New `backend/pricing.py` | Router validation, preview/save/history/sync dùng caller wiring |
| `backend/main.py` | Include router và inject caller, write feature flag |
| `backend/store.py` | Row estimate/source/coverage, batch price fetch |
| `web/js/api.js`, `web/js/app.js`, `web/index.html` (nếu cần container) | Extend existing price UI, API calls, dirty/loading/conflict/preview states |
| `scripts/audit_db.py` | Coverage/freshness/matching warnings |
| New `tests/test_model_pricing.py`, `tests/test_pricing_api.py`, `tests/model-pricing.test.js` | Core, DB/API, frontend contracts |
| New `docs/reference/model-pricing.md` | Setup quyền/schedule/price precedence/rollback |

Không sửa Compose/inference/provider configs mặc định. Nếu scheduler deployment chưa chạy hoặc API DB user chỉ có SELECT thì đây là rollout prerequisite: grant chỉ các bảng pricing cho credential phù hợp, không cấp quyền ghi fact/ledger; không tự đọc/change credential trong planning.

## Task 1 — Selector và công thức tiền được kiểm chứng

**Interfaces:** `parse_rate(value) -> Decimal|None`; `match_model(raw, ids, aliases) -> str|None`; `select_price(versions, day) -> dict|None`; `estimate_text(usage, price) -> (Decimal|None, status)` trong `db/model_pricing.py`.

- [ ] Viết unittest RED cho precedence, reset auto, overlap, ngày ngoài range, null/zero, matching exact. Sample runnable contract:

```python
import unittest
from decimal import Decimal
from datetime import date
from db.model_pricing import select_price, estimate_text

class PricingTests(unittest.TestCase):
    def test_manual_survives_sync_and_auto_reset(self):
        day = date(2026, 9, 22)
        auto = dict(id=1, source='openrouter', mode='price',
                    valid_from=day, valid_to=None, rates={'input':'1','output':'2'})
        manual = dict(auto, id=2, source='manual', rates={'input':'3','output':'4'})
        refreshed = dict(auto, id=3, rates={'input':'5','output':'6'})
        self.assertEqual(select_price([auto, manual, refreshed], day)['id'], 2)
        reset = dict(manual, id=4, mode='auto')
        self.assertEqual(select_price([auto, manual, refreshed, reset], day)['id'], 3)

    def test_estimate_not_invoice(self):
        usage = {'input':1000000, 'output':0, 'cache_read':0,
                 'cache_write':0, 'modality':'text', 'extra_billable':False}
        self.assertEqual(estimate_text(usage, {'input':'1','output':'2'}),
                         (Decimal('1'), 'estimated'))
        self.assertEqual(estimate_text(usage, {'input':None,'output':'2'}),
                         (None, 'missing_rate'))
```

- [ ] Run `python -m unittest discover -s tests -p test_model_pricing.py -v`, fail vì module/functions absent.
- [ ] Implement selector logic:

```python
def select_price(versions, day):
    active = [v for v in versions if v['valid_from'] <= day
              and (v['valid_to'] is None or day < v['valid_to'])]
    manual = sorted((v for v in active if v['source'] == 'manual'),
                    key=lambda v: v['id'], reverse=True)
    if manual and manual[0]['mode'] == 'price':
        return manual[0]
    official = [v for v in active if v['source'] == 'official']
    candidates = official or [v for v in active if v['source'] == 'openrouter']
    return max(candidates, key=lambda v: (v['valid_from'], v['id']), default=None)
```

Freshness/eligibility validation thực hiện trước estimate, không tự fallback giá thấp hơn nếu manual thiếu một dimension cần thiết. Manual rates input/output USD/1M; OpenRouter per-token được normalize bằng Decimal, raw pricing vẫn giữ.

- [ ] Formula eligible text: `(input-cache_read)*input_rate/1e6 + cache_read*cache_rate/1e6 + output*output_rate/1e6`; chỉ dùng nếu usage contract xác nhận input bao gồm cached read. Nếu input semantics chưa biết hoặc cache unknown thì unknown, không subtract bừa. Cache-write, modality/tool unknown, tiers chưa đủ per-call context → unsupported. Reasoning không cộng lần hai vào completion.
- [ ] GREEN với finite/bounds/counts validation, :free/date suffix preserved, no fuzzy matching, cache<=input, no extra paid dimensions. Không migration để ép unknown thành zero.

## Task 2 — Persistence/sync toàn catalog

**Interfaces:** `sync_catalog(cn, payload, observed_at, apply=False) -> counters`; `fetch_catalog() -> dict`; `run_if_due(cn, now) -> status`. CLI `python scripts/sync_model_catalog.py` default dry-run, `--apply` ghi.

- [ ] RED integration fixtures: catalog A/B chưa có usage vẫn xuất hiện; idempotent repeat; price change append; unavailable not delete; malformed/incomplete response không mark hàng loạt unavailable; DB rollback không partial snapshots; override unchanged.
- [ ] Migration theo pattern revision 012, kiểm tra lại head; timestamps TIMESTAMPTZ, valid interval CHECK, source/mode CHECK, unique openrouter_id, indexes `(catalog_key,valid_from,id)`; JSONB raw rates, NUMERIC không float. Revision columns protect concurrent writes. Không insert toàn catalog vào dim_model.
- [ ] Network fixed HTTPS with verify, no redirects, 10s timeout, 30s total deadline, 16MiB response cap; validate unique IDs/data array. Dùng stdlib, fake transport cho 429/503/redirect/slow/oversized/schema failure. Retry về vòng scheduler, backoff 15m–24h, no per-model HTTP. Missing pricing không reject model metadata; duplicate catalog IDs reject snapshot.
- [ ] Lease acquisition transaction + token, release/update chỉ khi token còn khớp; expired worker không overwrite worker mới. Preserve cached snapshot khi API lỗi. Provider namespace giữ exact IDs; mapping exact/raw alias only, collisions unresolved.
- [ ] Auto valid_from business-day+1, last_seen riêng không rewrite history. Unchanged rates không tạo version mới; return changed/new/unavailable/unmapped counts từ parse, không count bằng tay.
- [ ] GREEN PostgreSQL isolated, unit tests; safe dry-run no DB writes kể cả lease/sync state. Public GET live verification chỉ catalog, không inference.

## Task 3 — API chỉnh tay và preview có bảo vệ

**Interfaces:** endpoints mục 3.2, immutable version + optimistic revision theo model. `preview_price(cn,key,payload)` và `save_price(cn,key,payload,principal)` ở `backend/pricing.py` dùng selector Task 1.

- [ ] RED: unauth→401; open_mode→403 mutation; writes disabled→403; malformed rate→422; local-only model editable; catalog-only model editable without usage; version conflict→409; retroactive unconfirmed→409; negative/missing intervals rejected.
- [ ] Save transaction: SELECT canonical catalog row FOR UPDATE, compare model revision, validate interval, verify retroactive confirm, INSERT version, increment revision, commit/read back by version ID. Revision tăng khi bất kỳ đầu vào giá/mapping của model thay đổi. Global generation chỉ invalidate cache nếu có, không làm save model khác bị conflict. Browser-supplied actor ignored; use caller Principal. No arbitrary SQL/model ID creation from price payload.
- [ ] Preview snapshot revision: if model price changes before save, 409 and re-preview. Usage may grow meanwhile: preview is point-in-time estimate, response shows as_of; no claim frozen invoice impact. Save bounded; bulk estimate large ranges query aggregate batches, no provider calls.
- [ ] Nút reset tạo mode auto version, không delete; override cũ có thể còn áp dụng trước interval reset. Rate nguồn auto cập nhật độc lập. Audit stores old/new version refs, reason/principal/time, no secret.
- [ ] Shared-key auth disclosed in docs/UI; add separate auth scope only nếu người dùng yêu cầu. Grant write privilege pricing tables prerequisite verified in integration environment.
- [ ] GREEN with read-back verification and same-day price races. Không chỉ test helper bypassing actual FastAPI caller.

## Task 4 — Schedule dùng vòng lặp hiện có

**Files:** refresh_gateway.py, sync script, tests.

- [ ] RED: fake clock kiểm tra interval 24h default, change interval tính next_due, disabled no fetch, manual sync queues one run, two workers one lease, offline worker visible.
- [ ] Existing refresh main loop gọi pricing due-check trong independent try/except trước/ngoài ingest run_once; load failure không suppress sync; sync failure không suppress rollups. No FastAPI background daemon/multiple-worker scheduler.
- [ ] `POST sync` chỉ enqueue bằng next_due, 202 kèm last_worker_seen; UI poll state với deadline, queued ≠ success. Interval PUT revision-guarded, audit shared principal; 1–168h range. Sync state persisted survives restart.
- [ ] Freshness theo lần xác minh giá từng model, không theo last_success toàn catalog. Ngưỡng stale = hai lần interval đã cấu hình; stale subtotal có nhãn, không gọi verified. Freshness hiện tại không làm mất estimate lịch sử. unavailable metadata không có nghĩa provider đã retired model toàn cầu. Chính sách chi tiết ở mục 8.
- [ ] GREEN full refresh regression và read-only status. Deployment activation only after approval; không tự start/recreate services.

## Task 5 — Màn hình Provider/Model/Pricing thật sự lưu DB

**Files:** existing renderPricing/app/api, HTML only if actual container missing. Đọc binding `price-grid`/save handlers và tests trước edit; xóa/disable local-only save path trong backend mode, không giữ hai nguồn truth.

- [ ] RED frontend tests với actual functions/test harness: save gọi endpoint đúng, body decimal strings và revisions; network fail không báo saved; conflict giữ draft; sync không ghi đè draft; refresh read-back rates; unavailable/local-only models vẫn có thể xem/sửa.
- [ ] Native select provider, search model, table pagination 50; model name dùng textContent (untrusted external data). Hiển thị auto/manual/applied/source/dates và lịch sử. Sửa input/output/cache-read với step phù hợp và không parse empty thành 0.
- [ ] Save flow: draft → Preview → hiện số dòng/agent/time affected + known subtotal/unknown → Confirm → mutation → GET exact history/current → refresh current usage. Retroactive explicit checkbox. Không persist trước confirm.
- [ ] Reset flow same preview/confirm; label “Dùng lại giá tự động”. Đồng bộ ngay + interval + enable control riêng, loading/error/last success; button keyboard accessible, labels và screen-reader status.
- [ ] Browser verification thực (không fixture-only), responsive table/focus/error states; nếu browser unavailable ghi BLOCKED, không nói visual PASS.

## Task 6 — Estimate đồng nhất và hồi quy

**Files:** backend/store.py, pricing module, app/api.js, audit_db.py, tests, docs.

- [ ] RED: ngày trước/giữa/sau override; scope mọi agent dùng model; subset range; account estimates không allocation invoice; cached unknown; partial coverage; currency/source CSV; recorded cost/zero unchanged.
- [ ] Backend add `estimated_cost_usd`, `estimate_source`, `estimate_status`, `price_version_id`, `priced_rows`, `unpriced_rows`; preserve `cost_usd` and invoice/source contract. Batch prefetch price versions for range/model IDs, avoid N+1. Catalog toàn bộ không load vào mỗi usage response.
- [ ] Price correction được tính on-read cho range, không update stored facts; remove latest-price formula for rows with new contract in costOrNull/account path. Cache invalidation dựa pricing generation sau save; stale responses không overwrite new saved version. Other browser tabs thấy sau refresh, không hứa realtime websocket.
- [ ] Legacy ref_price đọc theo effective date, không latest for past; explain any historical change from correcting old estimator separately. Auto unknown modality giữ unknown; manual override text rate không tự làm unsupported modality thành supported.
- [ ] Aggregate known subtotal + unknown count; không sum null thành full cost. Display recorded and estimate separately, total mixed phải có label. CSV bao gồm source/coverage/date/version. Quota display và enforcement không đổi theo estimate override.
- [ ] Audit coverage unresolved/stale/unsupported separately; OpenRouter estimate khác invoice không mặc định là lỗi reconciliation. Provider price source so với model vendor rõ ràng.
- [ ] Full suite, temp PostgreSQL migrations + real API, performance sample với catalog lớn/usage range, deterministic fake clock. Verify unchanged usage row counts/token/recorded totals bằng code. Lệnh dự kiến:

```bash
python -m unittest discover -s tests -p 'test_model_pricing.py' -v
python -m unittest discover -s tests -p 'test_pricing_api.py' -v
node --test tests/model-pricing.test.js
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.js
git diff --check
```

Không khẳng định suite dependency-ready trước kiểm tra environment. CI fixed test count chỉ cập nhật từ actual output.

## 5. Phê duyệt kỹ thuật và rollout

### Đánh giá cách làm (review kế hoạch, không phải chứng nhận code)

**Đề xuất thông qua về hướng thiết kế**, với gates sau:

- Đúng scope: full catalog/schedule/manual edit/mọi agent — không thay inference.
- YAGNI: reuse UI/scheduler/auth, no SDK/new service. Ba bảng tách external catalog, price history, scheduling là cần thiết để manual không bị overwrite và có audit.
- Bảo toàn dữ liệu: estimate on-read, append-only price history, no fact rewrite.
- Rủi ro cần người dùng duyệt: shared Dashboard key có write quyền khi enable; daily granularity; giá OpenRouter là reference, unsupported dimensions unknown; sửa giá tác động mọi agent dùng cùng model.
- Chỉ thông qua implementation sau review independent không còn blocker. Live rollout chỉ sau tests/DB privilege/security gates; “phê duyệt kế hoạch” không bằng “cho phép deploy”.

### Rollout ba chặng

1. Code + tests + isolated PostgreSQL/UI; không dữ liệu/cấu hình live.
2. Migration production + sync dry-run rồi apply khi có quyền; read back sample/exact changed versions. Enable scheduler, manual writes vẫn off; monitor counts/TTL/status.
3. Enable pricing write sau chấp thuận shared-key quyền; thử model test/manual reset và verify estimate, giữ recorded totals nguyên vẹn.

Rollback: disable sync và write flags, giữ snapshots/audit. Không drop/revert database hoặc switch inference route. Nếu UI/API mới lỗi, quay về version ứng dụng trước tương thích schema additive, không xóa fact.

## 6. Tiêu chí nghiệm thu bắt buộc

- Full catalog mới có model dù chưa dùng; local-only model vẫn quản lý được.
- Interval persist/restart/concurrent worker đúng; manual sync phản ánh queued/running/success/failure thật.
- Manual price thắng auto, sync không overwrite; auto reset và history hoạt động theo interval.
- Null/zero/precision/date/variant/matching/cached/tier boundaries có tests.
- Sửa giá tính lại estimate đúng scope và survives page reload; recorded cost/token/request unchanged.
- API writes có auth/feature flag/revision conflict/audit; shared-key limitation rõ ràng.
- Dashboard/filter/account/CSV đồng nhất, no partial-as-full totals.
- No inference/key/agent/runtime side effects ngoài scope được duyệt.

## 7. Self-review

Kế hoạch đã thêm full catalog + manual edit thay cho missing-price-only. Đã kiểm tra repo auth thực, không invent admin role. UI existing renderPricing được reuse nhưng không nhận local state là DB persistence. Scheduler chạy độc lập ingest với lease để tránh multi-worker duplicate. Không giả ngày observed là historical effective date. Có preview/optimistic concurrency/rollback/approval gates. Chưa thực thi code/tests/migration; mọi acceptance checkbox chưa checked là chủ ý.

## 8. Sửa sau review độc lập — hợp đồng bắt buộc

Review độc lập kết luận bản đầu đúng hướng nhưng còn blockers. Các sửa dưới đây bổ sung/ưu tiên hơn ví dụ giản lược ở Task 1; chưa có kiểm chứng implementation hoặc review lại độc lập bản sửa.

### A. Kết nối ghi

- `backend/store.open_db` vẫn readonly. Thêm context kết nối ghi riêng trong `backend/pricing.py`, explicit transaction; không tắt readonly toàn backend.
- Quyền tối thiểu trên bảng/sequence pricing, không cấp quyền ghi fact. Test actual API save thành công, read connection vẫn từ chối write. Đây là gate trước bật mutation.

### B. Adapter usage thay vì đoán token semantics

- Cả usage, usage-by-account và preview dùng cùng adapter theo nguồn. Adapter trả input_includes_cache, cache_coverage, text_only_evidence và extra_billable_evidence; chưa có evidence thì unknown, không default False.
- Billing có input/cache tách riêng: không trừ cache khỏi input. Gateway chỉ trừ cache nếu contract xác nhận input đã gồm cache. Điều kiện cache<=input chỉ áp dụng nhánh inclusive.
- Độ phủ lấy từ truy vấn read-only nguồn trước aggregate: đếm missing rows, không suy ra đầy đủ từ SUM khác NULL. Không rewrite facts/rollups. Khi nguồn không đủ evidence modality hoặc phụ phí, trả unsupported/incomplete.
- Fixtures bắt buộc: billing cache riêng, Gateway mixed NULL, monitoring thiếu cache, đủ text evidence, chưa đủ evidence. Ví dụ Task 1 chỉ là normalized synthetic fixture, không phải shape dữ liệu hiện có.

### C. Giá legacy, trạng thái thiếu và freshness

- Adapter ref_price giữ source/effective_from gốc. Chỉ map google/vendor sang official khi provenance đủ chứng minh giá nhà cung cấp; derived không tự nâng thành official. derived chỉ giữ như legacy reference có nhãn riêng, không dùng làm fallback mới trong selector này.
- Thêm status vào mỗi price version và price_last_verified_at ở catalog. Snapshot mới missing/unsupported tạo version đánh dấu từ ngày hiệu lực kế tiếp, chặn âm thầm dùng OpenRouter version cũ. Manual hoặc official đủ điều kiện vẫn ưu tiên như cũ.
- Unchanged valid price cập nhật price_last_verified_at, không tạo price version. HTTP lỗi giữ snapshot cũ nhưng stale được biểu thị riêng. Missing price không cập nhật verified timestamp.
- Stale sau hai lần interval hiện hành là cảnh báo độ mới hiện tại, không sửa lịch sử eligibility. Estimate lịch sử tính theo version/status có hiệu lực ngày đó. Stale hiện tại hiển thị subtotal có nhãn, không silently coi verified hoặc zero.
- Hai snapshot cùng ngày: version mới nhất thắng kể từ ngày hiệu lực; snapshot invalid cũng tham gia selector trước validation. Khi override/reset hữu hạn hết hạn, override cũ còn interval hợp lệ xuất hiện lại; UI preview nói rõ và test trước/trong/sau.

### D. Một lịch giá cho mỗi model local

- Unique local_model_id khi non-null. Khi local đã có catalog row, giữ row đó làm canonical và giữ mọi manual history khi link OpenRouter exact alias.
- Nếu external row cũng đã tồn tại: khóa cả hai; nếu chỉ local có manual history, chuyển external automatic history/link sang canonical row trong transaction, giữ version IDs; nếu cả hai có manual history thì unresolved, không tự merge/chọn một bên.
- Mapping dựa exact dim_model_alias, không tên bị bỏ namespace. Mapping không rõ xử lý bằng script kiểm soát dry-run/apply với audit, không thêm UI mapping. Conflict hai lịch manual phải operator quyết định trước apply; không xóa lịch sử để giải quyết.
- Bổ sung CLI mapping vào scripts/sync_model_catalog.py, read-back canonical ID và revisions. Test local có override rồi mới xuất hiện trên OpenRouter, alias collision và concurrent link/save.

### E. Scheduler không bị ingest treo giữ vô hạn

- Lưu last_worker_seen riêng trong ref_price_sync_state, cập nhật trước due-check, không reuse heartbeat chỉ được ghi sau ingest thành công.
- Vòng loop hiện hữu vẫn tuần tự: try/except chỉ cách ly lỗi, không cách ly treo. Thêm timeout hữu hạn cho subprocess ingest, cấu hình dựa thời gian đo được trong validation; hết timeout dừng child và báo failure, không để child cũ chạy chồng vòng mới. Không thêm queue/service.
- Test ingest timeout rồi scheduler tiếp tục; worker offline/lease expired phản ánh đúng UI. Gate activation gồm heartbeat thật và kết nối ghi thật, không chỉ GRANT.

### Kết luận sau tiếp thu review

Đề xuất duyệt hướng làm sau các sửa A–E và API query-key ở mục 3.2. Không tuyên bố reviewer đã duyệt bản sửa hoặc tests đã pass. Chờ người dùng chấp thuận default 24h, hiệu lực theo ngày, shared-key quyền sửa và giá tham chiếu; production rollout vẫn xin phép riêng.
