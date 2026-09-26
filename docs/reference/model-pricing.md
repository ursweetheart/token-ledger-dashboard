# Model reference pricing (implementation preview)

**Not rollout-ready.** These changes are local and uncommitted. No production migration, scheduler activation, inference call or recorded-cost rewrite is authorized by this document.

## Contract

- Public GETs fetch both fixed OpenRouter endpoints: `/api/v1/models` and `/api/v1/embeddings/models`. No API key, inference or per-model requests. The default CLI is read-only and never opens a database: `python scripts/sync_model_catalog.py`.
- Prices are USD per million tokens; API amounts are decimal strings. Missing is not zero. Catalog namespaces identify model publishers, not hosting endpoints.
- Selection: active manual override, provenance-qualified Google legacy price, then dated OpenRouter snapshot. Derived legacy references are not promoted to official prices.
- Dates use Asia/Ho_Chi_Minh calendar days. API intervals are `[from_day,to_day)`; UI end date is inclusive. New automatic snapshots apply the next business day, not retroactively. Missing/unsupported snapshots supersede old automatic prices.
- Reset creates a manual `mode=auto` version, not a deletion. Older overrides can resume after a finite override/reset expires. Manual schedules survive sync.
- Estimates are calculated on read. Original cost, tokens, requests, invoices, quota spend and facts remain unchanged. Unknown modality/cache/paid-dimension evidence means incomplete or unsupported, not free. Gateway/monitoring evidence currently often cannot support an estimate.
- Model mapping is exact only. Preview/date/free suffixes are identities. The known preview billing SKUs `54F8-C433-9340` and `5882-9C22-CC57` remain ineligible where legacy ingestion collapsed their identity. No fuzzy mapping or `rules.guess_model` pricing match.

## API and permissions

Read APIs reuse Dashboard authentication. Writes additionally require `PRICING_WRITE_ENABLED=1`, a non-open-mode principal and `PRICING_WRITE_DSN`. Every shared Dashboard key holder can write when enabled; there is no per-person admin role. Audit identity is `shared_key`.

`store.open_db` remains database-enforced read-only. Configure a separate writer with SELECT on source/pricing tables and INSERT/UPDATE on pricing tables plus sequence USAGE. Do not grant fact writes. Mapping CLI additionally requires DELETE on the external catalog row. New dim_model inserts register local pricing rows through an invoker-rights trigger; ingestion roles therefore need INSERT on `ref_model_catalog`. Verify these grants in staging before rollout.

- GET `/api/pricing/models` (provider, q, offset, limit up to 200)
- GET `/api/pricing/history?catalog_key=...`
- POST `/api/pricing/preview?catalog_key=...` (read-only impact)
- POST `/api/pricing/versions?catalog_key=...` (expected_revision; explicit retroactive confirmation)
- GET/PUT/POST `/api/pricing/sync` (state/settings/queue)

Encode catalog keys as query parameters, including slashes and plus signs. Preview is point-in-time, not frozen invoice impact. Save conflicts return 409; preserve the draft and preview again. Successful saves read the exact stored version back.

## Scheduler and operator mapping

The existing refresh loop checks pricing independently before ingest. Default schedule is disabled, interval 24 hours, allowed range 1–168. Manual sync queues work; 202 is not success. Check worker heartbeat, lease and last-success/error state. `GATEWAY_REFRESH_STEP_TIMEOUT` bounds each ingestion subprocess (default 120 seconds; must be calibrated before activation). No FastAPI background scheduler is added.

Mapping dry-run: `python scripts/sync_model_catalog.py --db "$PRICING_WRITE_DSN" --link-local LOCAL_ID --openrouter-id EXACT_ID`. Only add `--apply` after reviewing the exact alias and canonical row. Existing local manual history is preserved; external manual history conflicts require operator resolution. Do not expose DSNs in logs or chat.

Migration is additive revision 013. Never invoke a default database target during validation. An explicit Alembic `-x db=...` or explicit in-process configuration carries the selected DSN. The rebuild path currently refuses schemas containing the pricing catalog to prevent CASCADE erasing history; use incremental ingestion, not rebuild.

## Known unfinished validation / rollout gates

- User-approved `db/02_catalog.sql` was seeded only into asserted `pricing_full_test` at `127.0.0.1:55439`: read-back 8 agents, 12 models, 12 legacy prices. Its already-stamped 013 predated the trigger addition; the disposable schema was brought in line with that reviewed SQL (12 local catalog rows plus trigger), without reseeding or touching another database.
- Real Uvicorn HTTP on `127.0.0.1:55440` now has an opt-in regression gate: `PRICING_FULL_HTTP=1 python -m unittest discover -s tests -p pricing_full_http_cases.py -v`. It verifies catalog official-price selection, preview/save/409/history/reset, unchanged billing/usage/fact totals, minimum ingestion-role trigger grants and rebuild refusal. The seeded schema exposed and fixed two defects: catalog omitted official legacy prices; PostgreSQL `SUM(bigint)` returned integral Decimal values rejected as invalid tokens. The fixes were reproduced RED over HTTP before changing implementation.
- Browser verification is BLOCKED: the browser tool cannot start because Chrome/Chromium is absent from system, agent-browser, Puppeteer and Playwright caches. HTTP evidence is not visual/browser evidence; no browser PASS is claimed.
- UI still exposes JSON history/preview, has incomplete draft/navigation/loading guards, and provider input is not a complete provider selector.
- Per-model freshness appears in catalog UI but is not yet propagated into estimate subtotal labels. Audit coverage reporting is not implemented in `scripts/audit_db.py`.
- Account-level source evidence, concurrent mapping/save/sync races, large-range performance and minimum-privilege ingestion-trigger execution require fuller integration coverage.
- Network code checks a 30-second deadline around reads with socket timeouts, but slow-drip reads are not yet a proven strict wall-clock cap. Backoff is currently fixed 15 minutes, not adaptive.

Rollback: disable schedule and pricing writes, keep snapshots and audit history. Do not drop tables, rebuild ledgers or change inference routing. Production rollout remains a separate approval.
