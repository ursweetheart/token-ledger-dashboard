# Implementation checkpoint — 2026-09-24

Status: **29/38 tasks verified; not ready to archive or deploy without the remaining checks.**
Source baseline before implementation: `4d8cbca723b0855e7da49eefa9ad8cc8cd09282b`.
The working tree already contained the related legacy directory lookup change.
Its directory-only lookup and regression tests were preserved alongside this feature.
Unrelated catalog, planning files, other change artifacts and backup files are excluded.

## Implemented

- Additive migration 014, registry ownership, ID sequences and observed identity mapping.
- Empty default YAML and explicit dry-run/apply CLI; no implicit migrate/rebuild/export.
- Agent-scoped, exact identity discovery, single service accounts and fallback counters.
- Initial date-scoped backfill, shared apply/load/refresh lock and retryable pending state.
- Authenticated read-only identity API, dedicated dashboard panel and unknown adoption denominator.
- Bulk-loader preflight guards and config-directory read-only Compose mount.
- Vietnamese operator runbook and warnings over the old legacy onboarding instructions.

## Commands actually run

Dedicated PostgreSQL container: `gateway-onboarding-test-pg`, PostgreSQL 17,
user/database `onboarding` / `onboarding_test`. No production credentials.
Every integration test creates a UUID-named disposable database and removes only that database.

```powershell
docker run --rm --network container:gateway-onboarding-test-pg -e GATEWAY_ONBOARDING_TEST_DSN=postgresql://onboarding:onboarding_test@127.0.0.1:5432/onboarding_test -v D:/RangDonk/token-ledger-dashboard:/app:ro token-ledger-onboarding-test:local -m pytest -p no:cacheprovider tests/gateway_registration_cases.py -q --tb=short
# 35 passed

docker run --rm -v D:/RangDonk/token-ledger-dashboard:/app:ro token-ledger-onboarding-test:local -m pytest -p no:cacheprovider tests -q --tb=short
# 198 passed, 34 skipped, 30 subtests passed

node --test tests/*.test.js
# 117 passed (including 3 new panel tests)

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
- Fixture includes two multiple agents, one single, case-sensitive IDs,
  before-start/boundary dates, unknown tags, cache duplicate and failure-only identity.
  Result: 7 facts, 210 raw tokens, USD 0.007; successful resolved usage is
  6 calls / 180 tokens. Five observed identities remain separate, including
  `Alice` in two agents. Replaying preserves fact/account IDs and money.
- A new agent's old requests are loaded despite another agent's September 24
  watermark. UTC August 31 17:00 belongs to the September 1 reporting boundary.
- Injected daily/hourly/performance/heartbeat/loader failures retain pending;
  retry completes without duplicated facts. A competing process is refused
  while the advisory lock is held.
- All three legacy bulk entrypoints are refused with unchanged table snapshots.
- API tests reject missing credentials and invalid filters; ten observed IDs
  do not become staff accounts or a 100% adoption denominator.

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
6. Existing unit-test doubles needed to represent the new preflight/lock call
   order. Assertions still check refusal, mutation ordering and timeout retry.

Live DB was inspected read-only, not migrated/refreshed. Its baseline DMS
source/dashboard difference of 2 rows / 40 tokens remains outside this change's
acceptance claim; no data was edited to hide it.

## Remaining acceptance work (unchecked tasks)

- Complete the live baseline inventory and broader mixed-source/directory fixture.
- Expand adversarial identity/multi-tag and concurrent-discovery tests.
- Browser visual acceptance is unavailable in this session (no browser execution tool).
  DOM harness tests are not a substitute for visual verification.
- Rebuild the actual production tools image and verify host atomic config saves
  through the Compose mount. The test image used a read-only source bind mount.
- Exercise the real LiteLLM/fake-provider HTTP path: tag and X-User propagation
  through to the UI. Current integration tests insert controlled source ledger rows.
- Complete the full legacy/pricing reconciliation and CI acceptance record.
- Review loader deadline handling: the loader now runs in the lock-owning process;
  rollup subprocess timeouts remain, but the loader no longer inherits the previous
  subprocess wall-clock timeout. Do not claim timeout coverage for that step yet.

No production rollout, paid model request, push or archive has been performed.
Use [the runbook](../../../docs/reference/gateway-agent-registration.md) after
remaining acceptance checks, not as evidence those commands already ran live.
