# Gateway Local Pilot Prerequisites and Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Make the Docker-based LiteLLM Gateway stack runnable locally, prove its database isolation and telemetry path, then pilot exactly one low-risk agent while preserving `token_ledger` and `token_ledger_v2`.

**Architecture:** The dashboard runtime ledger is `token_ledger_v2`; `token_ledger` remains an untouched legacy/reconciliation database. LiteLLM runs under the Compose `gateway` profile, creates only its own `litellm` database, and is reached through the local nginx load balancer at `127.0.0.1:4000`. Gateway request records must be ingested only into `token_ledger_v2` after their final measured shape and idempotency mapping are implemented.

**Tech Stack:** Windows 11, WSL 2, Docker Desktop, Docker Compose, PostgreSQL 17, Redis 7, nginx, LiteLLM fork, Python backend, Node test runner.

---

## Current verified state

- The no-drop decision is implemented locally but **not committed**: `token_ledger` is legacy/reconciliation; `token_ledger_v2` is runtime and Gateway ingestion target; LiteLLM is isolated in `litellm`.
- The Compose Gateway profile, init scripts, nginx config, and LiteLLM config exist in this repo.
- Default database configuration is guarded by `tests/database-defaults.test.js`.
- Docker CLI/engine are not installed or not on PATH in this environment (`docker: command not found`).
- WSL and `winget` are available.
- The required sibling LiteLLM fork is missing at `C:/litellm_rang_dong`; `docker-compose.yml` builds from `../litellm_rang_dong`, so the Gateway cannot build until it is restored or the build context is deliberately changed.
- Do not use `docker compose down -v` against the dashboard stack: it removes named volumes and conflicts with the retention requirement.

## Non-negotiable safety invariants

1. Never run `DROP DATABASE`, rename `token_ledger_v2`, or delete the existing PostgreSQL volume.
2. Keep `token_ledger` available for historical reconciliation and rollback.
3. Keep `token_ledger_v2` as the sole runtime/Gateway ingestion target; never duplicate an attempt/request into both ledgers.
4. LiteLLM may create `LiteLLM_*` tables only in database `litellm`; there must be zero such tables in both ledger databases.
5. Do not copy API keys, JWTs, passwords, or the project `.env` into source control, docs, the LiteLLM fork, or chat output.
6. Keep `forward_client_headers_to_llm_api: false` and `turn_off_message_logging: true`; Gateway must not forward employee identity headers or prompts to the provider.
7. Keep cache disabled during the initial reconciliation pilot, because cache hits alter the relationship between Gateway metrics and provider billing.

---

### Task 1: Preserve and commit the completed no-drop decision separately

**Objective:** Put the completed decision-alignment changes under version control before adding environment-dependent Gateway work.

**Files:**
- Modify/review: `.env.example`
- Modify/review: `db/connect.py`
- Modify/review: `docker-compose.yml`
- Modify/review: `docker/pgadmin-servers.json`
- Modify/review: `docs/reference/ke-hoach-nen-thang-9-2026.md`
- Modify/review: `openspec/changes/change-the-schema-without-dropping-it/{proposal.md,tasks.md,specs/schema-migrations/spec.md}`
- Add/review: `tests/database-defaults.test.js`

**Step 1: Re-run the decision regression guard.**

Run:
```bash
node --test tests/database-defaults.test.js
openspec validate --all --strict
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.js
git diff --check
```

Expected: all checks pass; strict OpenSpec remains valid; no whitespace errors.

**Step 2: Inspect the staged scope before adding it.**

Run:
```bash
git diff -- .env.example db/connect.py docker-compose.yml docker/pgadmin-servers.json docs/reference/ke-hoach-nen-thang-9-2026.md openspec/changes/change-the-schema-without-dropping-it tests/database-defaults.test.js
python tools/diagnostics/scan_secrets.py
```

Expected: no actual secret finding; no accidental unrelated edits.

**Step 3: Commit only this logical decision.**

Run:
```bash
git add .env.example db/connect.py docker-compose.yml docker/pgadmin-servers.json docs/reference/ke-hoach-nen-thang-9-2026.md openspec/changes/change-the-schema-without-dropping-it tests/database-defaults.test.js
git commit -m "docs: preserve legacy ledger during gateway migration"
```

Expected: one focused commit. Do not commit `.env` or generated evidence containing secret-shaped values.

---

### Task 2: Install the minimum container runtime

**Objective:** Install Docker Desktop with the WSL 2 backend, which is currently the blocking missing dependency.

**Files:** None in the repository.

**Step 1: Inspect WSL status.**

Run from an elevated Windows Terminal only if Windows reports WSL needs updating:
```bash
wsl --status
wsl --version
```

Expected: WSL 2 is available. Update WSL if Docker Desktop requests it.

**Step 2: Install Docker Desktop for Windows from the official Docker installer.**

Use the official Docker Desktop Windows installation path, select the WSL 2 backend, and restart/log out if the installer requires it. Do not install a separate Docker Engine inside a WSL distribution, because it conflicts with Docker Desktop's WSL integration.

**Step 3: Enable WSL integration and start Docker Desktop.**

In Docker Desktop Settings:
- enable **Use the WSL 2 based engine**;
- enable WSL Integration for the distribution used for development;
- ensure Linux containers are selected.

**Step 4: Verify from this repository.**

Run:
```bash
docker --version
docker compose version
docker info --format '{{.ServerVersion}}'
```

Expected: all commands exit 0 and return a server version. Do not proceed to Gateway startup without this result.

---

### Task 3: Restore and verify the pinned LiteLLM fork

**Objective:** Restore the exact build input expected by Compose without guessing its source or changing `build.context` merely to make a build work.

**Files:**
- Read: `docker-compose.yml:36-51`
- Restore outside repo: `C:/litellm_rang_dong`

**Step 1: Recover the intended fork from the existing approved local clone/backup or its documented upstream.**

The compose build context is exactly `../litellm_rang_dong`. Restore it there; do not place a nested Git repository inside `C:/token-ledger-dashboard`.

**Step 2: Verify identity and cleanliness without exposing environment files.**

Run:
```bash
git -C C:/litellm_rang_dong rev-parse --short HEAD
git -C C:/litellm_rang_dong status --short
```

Expected: the pinned/approved revision used by the recorded probe (historically `f005afa146`) or an explicitly reviewed newer revision; working tree clean.

**Step 3: Verify that no `.env` is copied into the fork.**

Run:
```bash
python C:/token-ledger-dashboard/tools/diagnostics/scan_secrets.py
```

Expected: zero severe findings across the project worktree. Scan the fork with the same policy before building if it is outside the project scan root.

---

### Task 4: Provision local-only Gateway secrets and ports

**Objective:** Create the required local runtime configuration without placing secrets into Git.

**Files:**
- Create locally only: `.env` (ignored)
- Reference: `.env.example:57-86`

**Step 1: Copy the template without printing its resulting values.**

Run:
```bash
cp .env.example .env
```

**Step 2: Set the three mandatory Gateway values in `.env`.**

Required:
- `LITELLM_MASTER_KEY` — generate with the documented `sk-` prefix;
- `LITELLM_SALT_KEY` — generate once and retain securely, since rotating it invalidates stored Virtual Keys;
- `KEY_GOOGLE_AI_STU` — supply only the approved provider key.

Also set non-default `REDIS_PASSWORD` and `GATEWAY_PGPASSWORD` before any deployment beyond a strictly local loopback pilot. Do not paste values into terminal transcript, source code, or documentation.

**Step 3: Verify safe configuration shape.**

Run:
```bash
python tools/diagnostics/scan_secrets.py
git status --short
```

Expected: `.env` is ignored; no secret-bearing artifacts are staged; scanner reports no severe repository findings.

---

### Task 5: Bring up the baseline database without deleting existing data

**Objective:** Confirm the existing ledgers are reachable before adding the Gateway profile.

**Files:**
- Read: `docker-compose.yml:81-128`

**Step 1: Start only the dashboard/database profile.**

Run:
```bash
docker compose up -d postgres pgadmin
docker compose ps
```

Expected: `token-ledger-postgres` becomes healthy. Do **not** run `docker compose down -v`.

**Step 2: Verify all three database boundaries once Gateway has initialized its own database.**

Before Gateway startup, record that the existing ledger databases do not contain `LiteLLM_*` tables. After startup, repeat this check for both ledgers and query `litellm` separately.

Expected:
- `token_ledger`: legacy data preserved; zero `LiteLLM_*` tables;
- `token_ledger_v2`: runtime ledger; zero `LiteLLM_*` tables;
- `litellm`: LiteLLM's own schema only.

**Step 3: Check historical totals with the project audit query.**

Run the existing read-only audit/acceptance path rather than writing ad-hoc migration SQL.

Expected: legacy historical totals remain unchanged from their recorded baseline.

---

### Task 6: Build and start the isolated Gateway profile

**Objective:** Start LiteLLM, Redis, Redis replica, nginx, and the gateway database init job with local-only network bindings.

**Files:**
- Read: `docker-compose.yml:130-276`
- Read: `docker/gateway/config.gateway.yaml`
- Read: `docker/gateway/init-db.sh`
- Read: `docker/gateway/entrypoint.sh`
- Read: `docker/gateway/nginx.conf`

**Step 1: Validate resolved Compose configuration without printing secrets.**

Run:
```bash
docker compose --profile gateway config --quiet
```

Expected: exit 0. Do not use `docker compose config` output as a shareable artifact because it can resolve environment values.

**Step 2: Build then start Gateway.**

Run:
```bash
docker compose --profile gateway build
docker compose --profile gateway up -d
docker compose --profile gateway ps
```

Expected: `gateway-db-init` exits successfully; Redis services healthy; both LiteLLM containers healthy; nginx is listening on `127.0.0.1:4000` only.

**Step 3: Verify health and loopback exposure.**

Run:
```bash
curl --fail --silent --show-error http://127.0.0.1:4000/health/liveliness
docker compose --profile gateway ps
```

Expected: HTTP 200 and all long-running Gateway services healthy. Confirm no Compose port uses `0.0.0.0`.

---

### Task 7: Run a controlled one-request smoke test and inspect LiteLLM logging

**Objective:** Prove that identity and accounting fields are recorded safely before onboarding an agent.

**Files:**
- Read: `docker/gateway/config.gateway.yaml:42-67`
- Use existing probe/documentation evidence as reference only; do not reintroduce raw JWT-bearing artifacts.

**Step 1: Create a short-lived Virtual Key for a test service account through LiteLLM's supported admin API.**

Give it a minimal budget/rate limit and a non-production test identity. Do not use the master key in application config or client code.

**Step 2: Send one request through only `http://127.0.0.1:4000`.**

Include the normalized `X-User` value and a non-sensitive trace value. Do not send a JWT or real user prompt designed to carry personal information.

**Step 3: Query the LiteLLM `SpendLogs` record in database `litellm`.**

Verify:
- `end_user` is populated from `X-User`;
- headers are retained where required for traceability;
- prompts/responses are not retained;
- request status and token/cost fields are present;
- no `LiteLLM_*` table exists in either ledger database;
- `forward_client_headers_to_llm_api` remains disabled.

Expected: one inspectable record whose fields match the documented measured schema, without storing prompt text or secrets.

---

### Task 8: Implement Gateway-to-`token_ledger_v2` ingestion before onboarding real traffic

**Objective:** Turn measured LiteLLM records into a provenance-preserving runtime ledger flow without double-counting.

**Files likely to change:**
- Create/change the current OpenSpec change for Gateway ingestion and request provenance.
- Modify: `backend/store.py` and/or a dedicated ingestion module only after symbol/data-flow inspection.
- Modify: `db/migrations/versions/*` for additive schema only.
- Add: Python integration tests under `tests/`.

**Step 1: Write an OpenSpec proposal and an explicit idempotency contract.**

The contract must define a stable source record key from LiteLLM (for example the SpendLogs request identifier), `source='gateway'`, request/attempt status semantics, and retry behavior.

**Step 2: Write failing integration tests.**

Minimum cases:
- same Gateway record delivered twice creates one ledger request/attempt only;
- a failed attempt remains distinguishable from a successful request;
- `completion_tokens` is not summed again with `reasoning_tokens`;
- legacy `scrape` rows remain queryable and nullable in new Gateway-only columns;
- Gateway rows target only `token_ledger_v2`.

**Step 3: Implement additive migration and ingestion.**

Never alter/drop legacy tables as part of this work. Retain provenance (`data_era`, source, cost basis, model mapping source) at the record level.

**Step 4: Run tests and strict OpenSpec validation.**

Expected: all existing acceptance tests pass plus the new exact-once/double-count prevention tests.

---

### Task 9: Pilot one low-risk agent and run reconciliation before expansion

**Objective:** Establish a reversible operational pilot.

**Files likely to change:**
- Agent-specific environment/configuration outside this repository.
- Dashboard/reporting query only after ingestion exists.

**Step 1: Choose one low-volume, low-risk service-account agent.**

Do not pilot Ralli first: its absence of Google Monitoring AI rows reduces independent reconciliation coverage.

**Step 2: Route only that agent via the Gateway Virtual Key.**

Keep its former path available for rapid rollback. Do not enable cache during the two-week reconciliation period.

**Step 3: Reconcile by day × agent × model × status × source.**

Report Gateway records alongside app/billing/monitoring; missing source combinations must be `NULL`, not coerced to zero. Never sum raw multi-source facts directly; use the project's deduplicated resolution view/logic.

**Step 4: Run failure and rollback drills.**

Exercise one LiteLLM instance outage, a provider failure/fallback, and restoration of the agent's old path. Confirm attempts are recorded without inflating successful-request totals.

**Step 5: Promote only after the agreed parallel observation window.**

Expand one agent at a time only if data, cost, privacy, and failure-path evidence meet the acceptance thresholds.

---

## Installation checklist

Install now:

- [ ] Docker Desktop for Windows (WSL 2 backend)
- [ ] Ensure the WSL distribution is integrated with Docker Desktop
- [ ] Restore the approved LiteLLM fork at `C:/litellm_rang_dong`

Do not install yet:

- [ ] Kubernetes, cloud load balancers, or Redis Sentinel — not necessary for the local pilot
- [ ] A second PostgreSQL instance — Compose already provisions an isolated `litellm` database on the existing local PostgreSQL server
- [ ] Application-side telemetry libraries — first implement and test the server-side ingestion contract
- [ ] Cache — defer until reconciliation semantics are accepted

## Risks and decision gates

- **Docker installation is the immediate blocker.** Until Docker is available, the existing Compose Gateway profile cannot be built or exercised.
- **Missing LiteLLM fork is the second blocker.** Restoring the expected fork is safer than silently switching to an arbitrary upstream image.
- **Production credentials must not be used for a smoke test by default.** Use an approved provider key and a generated, least-privilege Virtual Key.
- **No agent should be switched before ingestion/idempotency is implemented.** LiteLLM `SpendLogs` alone are not yet the dashboard's provenance-preserving fact model.
- **The no-drop decision must remain independently committed.** Do not bury it inside an environment setup or Gateway feature commit.

## Definition of ready for the first agent pilot

1. Docker Desktop/Compose and the pinned LiteLLM fork are present and verified.
2. Gateway starts via `docker compose --profile gateway up -d` and health endpoint returns 200 on loopback only.
3. `token_ledger`, `token_ledger_v2`, and `litellm` boundaries are proven: `LiteLLM_*` tables appear only in `litellm`.
4. A controlled request proves identity/accounting logs are present, prompts are absent, and provider header forwarding is off.
5. Gateway-to-`token_ledger_v2` ingestion has exact-once tests and explicit failed-attempt handling.
6. A one-agent rollback and reconciliation procedure is documented and rehearsed.
