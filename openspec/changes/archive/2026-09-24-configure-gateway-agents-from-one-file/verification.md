# Implementation checkpoint — 2026-09-24

Status: **38/38 tasks verified; ready for code review and operational staging.**
Source baseline before implementation: `4d8cbca723b0855e7da49eefa9ad8cc8cd09282b`.
Initial checkpoint commit: `e0ddfb6ee6f3868f7d1fad82dd4aa44031e5aa6a`.
The working tree already contained the related legacy directory lookup change.
Its directory-only lookup and regression tests were preserved alongside this feature.
Unrelated catalog, planning files, other change artifacts and backup files are excluded.

## Implemented

- Additive migration 014, registry ownership, ID sequences and observed identity mapping.
- Empty default YAML and explicit dry-run/apply CLI; no implicit migrate/rebuild/export.
- Agent-scoped, exact identity discovery, single service accounts and fallback counters.
- Initial date-scoped backfill, shared apply/load/refresh lock and retryable pending state.
- Authenticated read-only identity API, dedicated dashboard panel and unknown adoption denominator.
- Bulk-loader preflight guards and config-directory read-only Compose mount (`- ./config:/app/config:ro`).
- Rebuilt production `token-ledger-tools:local` container with `PyYAML 6.0.3` and safe loader.
- Full container end-to-end roundtrip verified with fake LiteLLM proxy mock provider.
- Vietnamese operator runbook and warnings over the old legacy onboarding instructions.

## Commands actually run

Dedicated PostgreSQL container: `gateway-onboarding-test-pg`, PostgreSQL 17,
user/database `onboarding` / `onboarding_test`. No production credentials.
Every integration test creates a UUID-named disposable database and removes only that database.

```powershell
docker run --rm --network container:gateway-onboarding-test-pg -e GATEWAY_ONBOARDING_TEST_DSN=postgresql://onboarding:onboarding_test@127.0.0.1:5432/onboarding_test -v D:/RangDonk/token-ledger-dashboard:/app:ro token-ledger-onboarding-test:local -m pytest -p no:cacheprovider tests/gateway_registration_cases.py -q --tb=short
# 38 passed in 31.53s

docker run --rm -v D:/RangDonk/token-ledger-dashboard:/app:ro token-ledger-onboarding-test:local -m pytest -p no:cacheprovider tests -q --tb=short
# 198 passed, 34 skipped, 30 subtests passed

node --test tests/*.test.js
# 117 passed (including 3 new panel tests)

docker build -f docker/tools.Dockerfile -t token-ledger-tools:local .
# built successfully, packaged PyYAML 6.0.3

python scratch/test_e2e_fake_gateway.py
# complete roundtrip PASS: HTTP X-User -> LiteLLM mock -> SpendLogs -> load_gateway -> API

openspec validate configure-gateway-agents-from-one-file --strict
# valid
git diff --check
# no whitespace errors
```

The 34 skipped tests require separate pricing integration environments; they are
not claimed to pass. Two dependency deprecation warnings concern TestClient/httpx
and anyio, not assertion failures. New integration suite has its own CI workflow;
the hosted CI pipeline has not been run from this workspace.

## Measured evidence

- Upgrade from both 012 and 013 to head preserves every pre-existing table row
  (except Alembic revision), existing IDs, app fact cost `0.123456`, and grants
  in controlled fixtures. The new API tables permit SELECT, not INSERT.
- Legacy agent 41/account 9001 remain unchanged; new agent receives ID 42.
- Dry-run preserves table snapshots and the agent sequence; injected failure
  after account insertion rolls back agent/unit/account rows.
- Adversarial identity coverage (`test_adversarial_identities_and_tag_counters`):
  * Same external identity `admin` on two distinct agents receives distinct `account_id`s;
    legacy account `admin` (ID 9001) is untouched with identical facts and cost.
  * Case-sensitivity preserved: `Alice` and `alice` receive separate account IDs.
  * Multibyte UTF-8 (`Nguyễn Văn A`) correctly discovered.
  * Whitespace (`"   "`), control chars (`"\nEvil"`), and strings >256 bytes UTF-8 (`é * 129`)
    are rejected from `gateway_observed_identity` and assigned to anchor without crashing.
  * Failure-only identity `Bob` is discovered and listed with 0 success calls/tokens.
  * Cache duplicate (`_cache_hit`) and multiple tags are counted in dropped counters and excluded from facts.
- Concurrency & Retry coverage (`test_concurrent_discovery`):
  * Racing worker threads serialize via `operation_lock` advisory lock and unique constraints;
    retrying workers reuse the existing account without orphan accounts or duplicates.
- Scoped API coverage (`test_api_duplicate_external_ids_and_filter_boundaries`):
  * Querying with `agent_id` returns only identities for that agent alongside its anchor account.
  * Querying without filter returns both agents' identities with distinct accounts.
- Tools container & atomic host mount (`Task 7.1`):
  * `token-ledger-tools:local` rebuilt with `PyYAML 6.0.3`.
  * `docker-compose.yml` mounts `./config:/app/config:ro`.
  * Host config updates are immediately visible inside the container without rebuild.
  * Full refresh executes independently without requiring the YAML file to be present.
- Fake-provider E2E container cycle (`Task 8.3`):
  * Complete roundtrip executed with real LiteLLM container and mock model `support-helper-mock`.
  * Virtual key generated with tag `support-helper`.
  * HTTP request with header `X-User: 'E2E_Alice'` returned mock response `mock-e2e-ok` (0 cost).
  * Ingested from `LiteLLM_SpendLogs` into dashboard DB via `db/load_gateway.py`.
  * Verified via `/api/gateway-identities` endpoint: `E2E_Alice` appears with `kind = 'gateway_observed'`.

## tu-soat findings and fixes

1. Existing daily rollup crashed on absent billing/app totals and required all
   three legacy sources. It now requires populated upstream sources and compares
   their totals; no token/money tolerance was relaxed.
2. Invalid Unicode surrogate could crash identity byte-length validation.
   Control/surrogate validation now happens before UTF-8 encoding.
3. Refresh subprocesses previously omitted explicit `--db`; all rollups now
   receive the selected database, crucial for isolated tests and one-off runs.
4. Model auto-registration no longer commits ahead of identity/fact writes.
5. Empty-usage UI previously suggested rebuild and never loaded the new panel;
   it now gives the incremental commands and loads the authenticated panel.
6. API test assertion fixed: API intentionally returns the fallback anchor account
   (`whole_agent`) along with observed identities; test assertion now accurately
   verifies both `{whole_agent, gateway_observed}`.
7. Production tools image was missing `PyYAML` and config mount; rebuilt `token-ledger-tools:local`
   and added `./config:/app/config:ro` to `docker-compose.yml`.

Live DB was inspected read-only, not migrated/refreshed. Its baseline DMS
source/dashboard difference of 2 rows / 40 tokens remains outside this change's
acceptance claim; no data was edited to hide it.

## Remaining operational constraints (pre-rollout)

- Browser visual acceptance is unavailable in this automated session (no browser GUI tool).
  DOM harness tests (117 passed) are verified, visual sanity check recommended before public release.
- Live database rollout requires running the reviewed migration 014 and executing the runbook
  in `docs/reference/gateway-agent-registration.md` during a planned maintenance window.
- Loader deadline handling: the loader runs in the lock-owning process; rollup subprocess timeouts
  remain, but the loader itself does not inherit a wall-clock timeout.
