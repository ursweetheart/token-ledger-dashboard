# Shared OpenRouter Model & Pricing Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tự phát hiện model đang được các agent sử dụng nhưng thiếu giá, tra OpenRouter catalog, lưu giá tham chiếu nếu khớp chắc chắn và hiển thị cost ước tính có nguồn gốc rõ ràng.

**Architecture:** Tái sử dụng auto-register model và ledger-refresh hiện có. Một bước đồng bộ catalog dùng chung chạy ngoài inference path; snapshot giá OpenRouter nằm riêng để không ghi đè giá chính chủ. Backend chọn giá theo thời điểm và trả estimated cost/coverage; frontend không tự biến giá thiếu thành zero hoặc dùng giá mới nhất cho toàn lịch sử.

**Tech Stack:** Python stdlib urllib/json/decimal/unittest, PostgreSQL, Alembic/psycopg2 hiện có, FastAPI và JavaScript hiện có. Không dependency mới, không provider SDK.

**Spec:** Yêu cầu người dùng trong hội thoại: dùng API OpenRouter quét model mới và giá khi gần 10 agent gọi model chưa có trong database. Hợp đồng tại mục 1 của chính tài liệu này là spec triển khai. Tài liệu `2026-09-22-dms-gateway-openrouter.md` là phương án sai phạm vi, **không dùng để triển khai yêu cầu này**.

## Global Constraints

- Không chuyển inference sang OpenRouter; không thêm model route hoặc OpenRouter provider key vào LiteLLM/DMS.
- Dùng chung cho mọi agent có usage đi vào ledger, không hard-code DMS hoặc số agent.
- Không sửa code của từng agent, auth, fallback, model mặc định hoặc Virtual Key quota.
- Cost thực ghi nhận, cost do Gateway tính và cost ước tính catalog là các mức bằng chứng khác nhau; không gọi mọi SpendLogs cost là hóa đơn.
- Không ghi đè `fact_call.cost_usd`, cost hóa đơn, giá chính chủ hoặc dữ liệu lịch sử bằng estimate OpenRouter.
- Không secret reads, paid generation, migration production, deploy, commit/push trong lượt lập kế hoạch.
- Giữ cả `token_ledger`, `token_ledger_v2`, `litellm`, volumes và mọi WIP hiện có. Không rebuild/drop DB.
- Dùng unittest/Node test runner có sẵn; các con số PASS chỉ được báo sau thực thi.

---

## 1. Hợp đồng chức năng

### 1.1 Luồng đúng

```text
Agent bất kỳ → Gateway/provider hiện tại → usage/SpendLogs
                                      ↓
                        auto_register_models hiện có
                                      ↓
                      model đang dùng nhưng thiếu giá
                                      ↓
             catalog OpenRouter được cache dùng chung
                                      ↓
           exact ID / explicit alias hợp lệ, duy nhất?
                    có ↓                 ↓ không
              lưu snapshot giá       unresolved
                    ↓
          backend tính estimate nếu đủ dữ liệu
                    ↓
       dashboard: recorded / estimated / unknown + coverage
```

OpenRouter ở đây là **nguồn catalog/pricing**, không phải đường inference bắt buộc. Model không có trong OpenRouter vẫn phải hiện usage và trạng thái chưa có giá, không biến mất khỏi báo cáo.

### 1.2 Quy tắc giá

1. Model đã có giá chính chủ hợp lệ theo thời điểm: giữ nguyên, không ưu tiên OpenRouter chỉ vì mới hơn.
2. Recorded cost hiện có được bảo toàn. Giá OpenRouter chỉ tạo trường estimate riêng, không điền đè vào trường recorded.
3. OpenRouter price là giá tham chiếu tại OpenRouter. Với request gọi trực tiếp provider, UI phải ghi **“Ước tính theo giá OpenRouter”**, không phải “chi phí thực trả”.
4. Rate API `prompt`/`completion` là USD/token; `ref_price` legacy dùng USD/triệu token. Dùng Decimal, kiểm tra đơn vị, không trộn hai dạng.
5. Null/missing ≠ zero. Chỉ giá zero explicit và hợp lệ mới được xem là miễn phí theo catalog.
6. Không dùng tổng token thay input/output riêng. Không cộng reasoning thêm nếu đã nằm trong completion_tokens.
7. Cache read/write, tier context, audio/image/tool/search là dimensions riêng. Chỉ tính khi có đủ usage phân rã và đơn vị xác minh. Bản đầu chỉ tự tính **text input/output flat-rate không cache** đã xác nhận eligibility; cached/tiered/multimodal/không rõ modality giữ `unsupported_usage` hoặc `insufficient_usage`, không ước đoán thành số đầy đủ.
8. Không lấy giá quan sát hôm nay giả làm giá hiệu lực của tháng trước. Snapshot áp dụng từ ngày UTC kế tiếp ngày quan sát cho các aggregate day-level; ngày quan sát và trước đó báo `no_historical_price` nếu không có snapshot cũ. Đây là giới hạn có chủ ý để tránh áp giá ngược trong cùng ngày.
9. Giá biến mất/thay đổi: giữ snapshot cũ cho lịch sử; không dùng last-good vô hạn cho hiện tại. TTL catalog 24h; quá 48h không xác minh được freshness thì estimate mới có trạng thái `stale_price` và amount null. Historical interval đã được xác minh vẫn giữ nguyên.
10. Tổng có một phần unknown phải trả coverage và subtotal được biết, không hiện subtotal như tổng đầy đủ.

### 1.3 Matching

- Ưu tiên raw model ID khớp chính xác OpenRouter ID.
- Chỉ bỏ prefix kỹ thuật `openrouter/` khi đó thực sự là provider prefix trong raw provenance. Không tùy ý bỏ mọi prefix.
- `gemini/<id>` → `google/<id>` chỉ là mapping provider đã khai explicit; phải tìm đúng ID duy nhất trong catalog.
- Không bỏ date suffix, `:free`, `:extended`, preview; không fuzzy match/display-name match; không gán `gemini-flash-lite` alias Gateway thành một model cụ thể nếu không có actual upstream name.
- Alias chưa rõ/đụng nhiều ID → unresolved. Explicit mappings ở `db/rules.py`, không tạo UI quản lý mapping hoặc fuzzy search engine.

## 2. Bằng chứng và giới hạn kiểm tra

Baseline Gateway repo: `D:/token-ledger-dashboard`, branch `ChiThanh`, HEAD `cc109c4e0bde2f5c2e10622a46a9cba82d33a514`; có WIP chưa commit. Ngày lập 2026-09-22.

| Source đã đọc | Hiện trạng |
|---|---|
| `db/load_gateway.py:258` | Đã auto-register dim_model/dim_model_alias; không tự lấy giá |
| `db/load_gateway.py:152` | Cost lấy từ SpendLogs metadata.cost_breakdown.total_cost |
| `db/gen_catalog.py:331` | ref_price được tạo từ Google SKU catalog |
| `db/migrations/sql/001_baseline.sql:586` | ref_price khóa `(model_id,effective_from DATE)`, chỉ input/output/cached và source |
| `backend/store.py:121` | models() chỉ trả giá mới nhất, chưa đủ để tính lịch sử |
| `backend/store.py:333,389` | usage theo ngày/model và account; account không có measured cost để tự phân bổ |
| `web/js/api.js:378` | Giá thiếu đang bị chuyển thành zero |
| `web/js/app.js:443,736` | Account và tổng quan có đường tính estimate riêng bằng giá latest |
| `scripts/refresh_gateway.py:76` | Chuỗi load → daily → hourly → percentiles có thể tái sử dụng |
| `scripts/audit_db.py:741` | Đã có cảnh báo model có usage nhưng thiếu ref_price |
| Alembic head trong source | `012_nhip_tim_lam_moi`; kiểm tra lại trước tạo revision tiếp theo |

API công khai `GET https://openrouter.ai/api/v1/models` đã trả thành công không auth ở lượt điều tra trước. Thấy `pricing.prompt`, `completion`, cache fields và `overrides` cho context tiers. Đây là live catalog evidence, không generation/billing evidence. Chưa query database live; không khẳng định số model/agent/giá thiếu đang tồn tại trên server.

## 3. File map và phạm vi nhỏ nhất

| File | Trách nhiệm |
|---|---|
| New `db/openrouter_pricing.py` | Fetch bounded, validate, exact matching, Decimal pricing, snapshot selection/eligibility |
| New `scripts/sync_openrouter_prices.py` | CLI dry-run/apply, candidates, DB transaction, freshness/backoff |
| Modify `db/rules.py` | Explicit alias mapping nhỏ; không auto-normalize model |
| New `db/migrations/sql/013_openrouter_price_snapshots.sql` + `versions/013_openrouter_price_snapshots.py` | Bảng snapshot + trạng thái đồng bộ riêng; forward-only |
| Modify `scripts/refresh_gateway.py` | Optional sync sau ingest, trước rollups; fail riêng không chặn usage |
| Modify `backend/store.py` | Batch load applicable prices, estimated fields theo row/day và coverage |
| Modify `web/js/api.js`, `web/js/app.js` | Dùng estimated fields + provenance; không ghi estimate vào invoice field |
| Modify `scripts/audit_db.py` | Unknown/stale/unsupported/coverage, không yêu cầu estimate phải trùng invoice |
| New `tests/test_openrouter_pricing.py`, `tests/openrouter-pricing.test.js` | Regression nhỏ nhưng đủ branches/money boundaries |
| New `docs/reference/openrouter-price-discovery.md` | Operational runbook, scope/limits/rollback |

Không sửa `docker/gateway/config.gateway.yaml`, agent repo, inference route, quota hook hoặc tạo scheduler/service mới. Bảng mới cần thiết vì ref_price hiện tại không lưu được raw payload, matching ID, fetched time và nhiều nguồn cùng ngày mà không xung đột.

## Task 1 — Pure parsing/matching và money contract (TDD)

**Interfaces:** new `decimal_rate(value: object) -> Decimal | None`; `match_model(raw: str, catalog_ids: set[str], aliases: dict[str,str]) -> str | None`; `flat_text_cost(usage: dict, pricing: dict) -> tuple[Decimal | None, str]`. `usage` có `prompt_tokens`, `completion_tokens`, `cached_tokens`, `modality`; thiếu field không mặc định bằng zero.

**Files:** create `db/openrouter_pricing.py`, `tests/test_openrouter_pricing.py`; modify `db/rules.py` chỉ khi thêm alias được xác nhận.

- [ ] Viết unittest đỏ, dùng fixture tổng hợp rõ ràng, không coi fixture là số provider thực:

```python
from decimal import Decimal
import unittest
from db.openrouter_pricing import decimal_rate, match_model, flat_text_cost

class PricingTest(unittest.TestCase):
    def test_exact_mapping_and_variant_safety(self):
        ids = {'google/gemini-2.5-flash-lite'}
        aliases = {'gemini/gemini-2.5-flash-lite': 'google/gemini-2.5-flash-lite'}
        self.assertEqual(match_model('gemini/gemini-2.5-flash-lite', ids, aliases),
                         'google/gemini-2.5-flash-lite')
        self.assertIsNone(match_model('gemini-flash-lite', ids, aliases))
        self.assertIsNone(match_model('google/gemini-2.5-flash-lite:free', ids, aliases))

    def test_cost_and_unknown_are_distinct(self):
        usage = dict(prompt_tokens=1000, completion_tokens=200,
                     cached_tokens=0, modality='text')
        price = dict(prompt='0.0000001', completion='0.0000004')
        self.assertEqual(flat_text_cost(usage, price), (Decimal('0.00018'), 'estimated'))
        self.assertEqual(flat_text_cost(usage, {}), (None, 'missing_rate'))
        self.assertEqual(flat_text_cost(usage, dict(price, overrides=[{}])),
                         (None, 'unsupported_pricing'))
        self.assertEqual(flat_text_cost(dict(usage, cached_tokens=None), price),
                         (None, 'insufficient_usage'))

    def test_bad_rates(self):
        for value in ('NaN', 'Infinity', '-1', True, {}, None):
            self.assertIsNone(decimal_rate(value))
        self.assertEqual(decimal_rate('0'), Decimal('0'))
```

- [ ] RED: `python -m unittest discover -s tests -p test_openrouter_pricing.py -v` → module/function absent.
- [ ] Implement pure core; no network/DB/import-time I/O:

```python
from decimal import Decimal, InvalidOperation

def decimal_rate(value):
    if not isinstance(value, (str, int, Decimal)) or isinstance(value, bool):
        return None
    try:
        rate = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        return None
    return rate if rate.is_finite() and rate >= 0 else None

def match_model(raw, catalog_ids, aliases):
    if not isinstance(raw, str) or not raw or raw != raw.strip():
        return None
    candidate = raw if raw in catalog_ids else aliases.get(raw)
    if candidate is None and raw.startswith('openrouter/'):
        candidate = raw[len('openrouter/'):]
    return candidate if candidate in catalog_ids else None

def flat_text_cost(usage, pricing):
    if usage.get('modality') != 'text':
        return None, 'unsupported_usage'
    if pricing.get('overrides'):
        return None, 'unsupported_pricing'
    counts = [usage.get(k) for k in ('prompt_tokens', 'completion_tokens', 'cached_tokens')]
    if any(type(v) is not int or v < 0 for v in counts):
        return None, 'insufficient_usage'
    if counts[2] != 0:
        return None, 'unsupported_usage'
    rates = [decimal_rate(pricing.get(k)) for k in ('prompt', 'completion')]
    if any(r is None for r in rates):
        return None, 'missing_rate'
    return Decimal(counts[0]) * rates[0] + Decimal(counts[1]) * rates[1], 'estimated'
```

Caller phải kiểm tra usage không có extra billable dimensions (tool/search/cache-write/audio/image); không gọi hàm này nếu không xác minh được text-only. Không gán modality='text' chỉ vì model hỗ trợ text: model capability không chứng minh request modality. Với legacy aggregated rows thiếu bằng chứng thì unknown là đúng.

- [ ] Thêm tests duplicate IDs, malformed catalog, cache-write/search exclusion và recorded zero được giữ nguyên tại selection boundary ở Task 4; GREEN, review diff, không commit tự động.

## Task 2 — Catalog snapshot, transaction và fetch bounded

**Interfaces:** new `fetch_catalog() -> dict` chỉ GET fixed HTTPS endpoint; `sync_prices(cn, *, apply: bool, now: datetime) -> dict` trả counters `matched/unmatched/unsupported/changed/fresh/error`, không secret payload. CLI default dry-run, `--apply` mới ghi.

**Files:** new sync script và migration pair; expand `db/openrouter_pricing.py` và `tests/test_openrouter_pricing.py`.

- [ ] Viết test đỏ: dry-run không INSERT, lần thứ hai không duplicate, concurrent writers không tạo duplicate, model không tồn tại không INSERT FK, timeout không xóa cache, malformed catalog không replace last-good, catalog xóa model không làm mất historical snapshots.
- [ ] Tạo migration forward-only theo pattern `012_nhip_tim_lam_moi.py`, revision `013_openrouter_price_snapshots`, down_revision `012_nhip_tim_lam_moi` nếu head vẫn đúng. SQL contract:

```sql
CREATE TABLE ref_openrouter_price (
    model_id INTEGER NOT NULL REFERENCES dim_model(model_id),
    observed_at TIMESTAMPTZ NOT NULL,
    valid_from DATE NOT NULL,
    catalog_id TEXT NOT NULL,
    pricing JSONB NOT NULL,
    pricing_hash TEXT NOT NULL,
    last_verified_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (model_id, observed_at)
);
CREATE UNIQUE INDEX uq_openrouter_price_version
ON ref_openrouter_price (model_id, valid_from, pricing_hash);
CREATE TABLE ref_openrouter_sync (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    last_attempt_at TIMESTAMPTZ,
    last_success_at TIMESTAMPTZ,
    retry_after TIMESTAMPTZ,
    status TEXT NOT NULL
);
```

Không thêm vào ref_price legacy, không rewrite generated catalog. Một model được hỗ trợ bởi snapshot chung, không copy một giá cho mỗi agent. `pricing_hash` tính từ canonical pricing JSON + catalog_id bằng hashlib; retain raw pricing JSON đầy đủ.

- [ ] Implement transaction: lock singleton row, candidate models từ dim_model có fact usage/call; exact match; cùng price hash chỉ update last_verified_at, giá thay đổi append version. Hai giá đổi cùng ngày giữ observed_at để audit, day-level chọn version cuối quan sát của ngày trước. Không chỉnh snapshot historical.
- [ ] Fetch bằng stdlib với URL cố định, không auth, không redirects, timeout 10s và deadline/bounded read, giới hạn 16 MiB; parse dict/data list, unique nonempty IDs, pricing dict; invalid structure reject toàn response. Không một HTTP request cho mỗi model. Fake transport test slow/truncated/oversized/redirect/429/503.
- [ ] TTL 24h; lần fail đặt retry_after ít nhất 15 phút, respect Retry-After hợp lệ trong trần 24h. Catalog valid không match model = negative-cache đến TTL, tránh mọi refresh đều GET. Sau reboot đọc state DB, không reset backoff. Đồng bộ concurrent cùng lần dùng lock/single-flight; không giữ ingestion transaction trong lúc network.
- [ ] Test migration upgrade trên PostgreSQL test riêng, rerun idempotence và constraints; không dùng DB live. Lệnh CLI sau implementation:

```bash
python scripts/sync_openrouter_prices.py
python scripts/sync_openrouter_prices.py --apply
```

CLI nhận database bằng existing `connect` conventions; không hard-code credentials hay tự load config từ agent repos. `--apply` ở production chỉ sau approval. Stdlib fetch public không cần OpenRouter key.

## Task 3 — Gắn vào refresh hiện có, không làm mất usage

**Files:** `scripts/refresh_gateway.py`, sync script, tests Python ở trên.

**Interfaces:** giữ `STEPS` ingest/rollup hiện có; price sync là bước best-effort có trạng thái riêng sau successful ledger load. Tự động discovery tiếp tục ở `auto_register_models`, không sửa lại logic này.

- [ ] Test bằng subprocess mock: ledger load fail → không chạy price sync/rollups; price sync fail → rollups vẫn chạy và có warning counter; TTL fresh → không HTTP; unknown model vẫn vào fact_call dù catalog lỗi.
- [ ] Chèn explicit optional step, không đặt thành mandatory step của loop vốn stop-on-error:

```python
# Pseudocode wiring contract; apply at the existing successful-load boundary.
price_result = subprocess.run(
    [PY, str(ROOT / 'scripts/sync_openrouter_prices.py'), '--apply'],
    capture_output=True, text=True, timeout=30,
)
if price_result.returncode:
    print('WARNING: OpenRouter prices unavailable; usage refresh continues', file=sys.stderr)
```

Catch TimeoutExpired/OSError tại boundary này, không nuốt lỗi ingestion. Report sanitized counters từ stdout, không giả thành success. Bật qua `--sync-openrouter-prices` opt-in của existing refresh CLI; default off để rollback nhỏ, operator enable sau migration/tests. Không daemon/cron service mới.

- [ ] Fixture sequence gồm nhiều agent cùng model + một model mới: một catalog GET, một snapshot dùng chung, không nhân token/cost theo số agent; refresh repeat không tăng fact counts.
- [ ] Run tests offline và kiểm tra run_once hiện có giữ heartbeat/step error behavior. Không chạy refresh production để “test thử”.

## Task 4 — Cost selection, lịch sử và UI dùng cùng một kết quả

**Files:** `backend/store.py`, `db/openrouter_pricing.py`, `web/js/api.js`, `web/js/app.js`, tests Python + new `tests/openrouter-pricing.test.js`.

**Interfaces:** bổ sung per usage row `estimated_cost_usd: string|null`, `estimate_status: string`, `estimate_source: string|null`, `price_observed_at: string|null`, `priced_rows: int`, `unpriced_rows: int`. Không gán estimate vào `cost_usd` hoặc `row.cost` vốn dùng để nhận dạng invoice. Các API hiện có vẫn giữ field cũ.

- [ ] Test đỏ precedence: recorded cost gồm explicit zero không bị overwrite; official historical rate thắng OpenRouter; giá tương lai không dùng; missing/ambiguous/stale/unsupported không ra zero; unknown row không bị loại.
- [ ] Implement one shared selector `estimate_usage_row(row: dict, prices: list[dict]) -> dict` trong pricing module; backend prefetch giá cho model IDs và time range một lần, không N+1. Applicable snapshot: valid_from <= usage_day, freshness interval phù hợp; legacy official ref_price dùng effective_from <= usage_day. Không dùng models() latest để tính lịch sử.
- [ ] Với Gateway, lấy eligibility từ raw ledger metadata đã có hoặc sanitized derived attributes ở read boundary; không query prompt text. Nếu raw hiện không đủ để chứng minh modality/cache-write/tool usage thì trạng thái insufficient, không đoán. Multi-tier cần per-request token/context, không áp daily total làm context; version đầu không tính tiered model. Historical price thiếu giữ unknown trừ khi có approved historical import riêng.
- [ ] Account rows không có measured cost: không chia tiền của agent xuống user. Chỉ estimate từ usage measured của đúng account; nếu thiếu usage breakdown thì unknown. Daily/hourly/account dùng cùng selector và coverage rules, không dùng công thức độc lập.
- [ ] `api.js` chuyển estimate fields riêng, giữ null bằng null; bỏ `price_cached || 0` tại các đường estimate được chuyển. `app.js` costOrNull và account aggregation ưu tiên fields backend cho rows mới, không fallback latest-price khi estimate_status rõ unknown. Giữ explicit legacy display behavior cho dữ liệu legacy chưa dùng OpenRouter và thêm warning provenance thay vì âm thầm tính lại toàn lịch sử.
- [ ] Node regression contract tổng unknown:

```javascript
const assert = require('node:assert/strict');
const test = require('node:test');
// Load actual app functions through the existing test harness pattern.
// Inputs below are fixtures, not live usage.
test('catalog estimates cannot become recorded invoice cost', () => {
  const row = {cost: null, estimated_cost_usd: '0.00018',
    estimate_status: 'estimated', estimate_source: 'openrouter'};
  assert.equal(row.cost, null);
  assert.equal(row.estimate_source, 'openrouter');
});
```

Thay assertion fixture-only bằng calls tới actual `costOrNull`/account aggregation qua test harness repo đã có khi thực hiện; fixture-only không đủ nghiệm thu. Test actual UI/CSV consumers: 2 priced + 1 unknown → total incomplete, known subtotal có nhãn; zero explicit → 0, không `—`; update price hôm nay không đổi hôm qua; agent filter không lẫn giá/user giữa agent.

- [ ] Nhãn: “Đã ghi nhận”, “Ước tính theo OpenRouter”, “Chưa có giá”, “Giá hết hạn xác minh”, “Chưa hỗ trợ cách tính này”; tooltip ID và observed_at. Không gọi SpendLogs cost là invoice nếu source metadata không xác nhận hóa đơn. Không redesign dashboard.

## Task 5 — Audit, regression, canary và handoff

**Files:** `scripts/audit_db.py`, `docs/reference/openrouter-price-discovery.md`; tests cùng scope.

- [ ] Sửa audit thiếu giá: phân biệt official price, matched OpenRouter snapshot, unresolved và unsupported. Không xóa warning ref_price; nâng nó thành coverage check. Không bắt giá OpenRouter trùng stored cost trong 1% để chứng minh correctness khi provider/route khác.
- [ ] Runbook có dry-run/apply/TTL/backoff/source/freshness/day-effective policy; nêu rõ hỗ trợ flat text đã xác minh, cache/tier/multimodal unknown trong version đầu. Catalog availability không bảo đảm model callable.
- [ ] Chạy lệnh verification từ repo root sau implementation:

```bash
python -m unittest discover -s tests -p 'test_openrouter_pricing.py' -v
node --test tests/openrouter-pricing.test.js
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.js
git diff --check
```

Dùng env dependency hiện có của repo; record baseline missing deps/failures, không cài/sửa production để giả green. CI có guards số test: chỉ cập nhật expected count từ actual runner output, không đoán.

- [ ] PostgreSQL isolated integration: migrations, snapshot select, concurrency, ingest idempotency, rollback toggle và read-only API response. Đối chiếu pre/post facts, tokens, stored cost bằng code; mọi stored totals phải giữ nguyên. Chỉ estimated fields/price snapshots được tăng.
- [ ] Live canary chỉ `GET /api/v1/models` + CLI dry-run trên DB được cấp quyền read-only; no generation/no provider key. Báo model matched/unmatched/unsupported theo exact IDs; không tuyên bố database server đã verified nếu chưa có access.
- [ ] Sau approval mới apply migration/sync rồi đọc lại rows chính xác để xác minh source, model IDs, rates, timestamps. Enable existing refresh opt-in; quan sát chu kỳ TTL và API/UI. Không restart các Gateway Proxy vì thay đổi này không thuộc inference.
- [ ] Rollback bằng tắt `--sync-openrouter-prices` và không chọn OpenRouter estimates; giữ snapshots audit, không drop bảng/facts. Migrations forward-only. Không tự commit/push/deploy.

## Acceptance và giới hạn

- [ ] Một cơ chế dùng chung tự xử lý model mới từ mọi agent, không sửa từng agent.
- [ ] Exact match, unsupported/unmatched hữu hình; không bịa model/giá hoặc zero.
- [ ] Catalog fetch bounded/cache/backoff, không trên request inference path.
- [ ] Official/recorded cost và facts lịch sử không đổi; estimate riêng có provenance.
- [ ] Giá có thời điểm, không áp latest ngược lịch sử; unsupported dimensions không bị bỏ qua im lặng.
- [ ] Account/daily/hourly/filter/export không mâu thuẫn coverage hoặc dùng hai công thức khác nhau.
- [ ] API outage không chặn ingest, không mất historical snapshots; stale visible.
- [ ] Tests có execution evidence và DB read-back khi được phép.

**Ngoài phạm vi:** chuyển model routing, OpenRouter generation API, update LiteLLM runtime pricing/quota enforcement, đồng bộ provider billing export, engine tính mọi loại multimodal/tier, historical backfill không có dữ liệu thời điểm. Đây là price discovery + conservative cost estimation, không phải thay hệ thống billing.

## Self-review

Đã loại kế hoạch DMS/OpenRouter inference sai phạm vi. Tái sử dụng auto-registration/refresh; không thêm service/SDK. Matching/pricing boundaries có test contract; giá OpenRouter không ghi đè ref_price vì PK hiện tại thiếu source granularity. Tính giá thiếu dữ liệu được giới hạn minh bạch thay vì kết quả sai. Các bước DB/runtime chỉ sau approval. Khi thực hiện cần đọc toàn bộ actual API/UI test harness trước edit để chuyển test contracts thành assertions trên production functions, không nghiệm thu bằng fixture-only checks.
