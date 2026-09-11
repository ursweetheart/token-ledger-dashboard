# Isolated Gateway smoke test

This is a single-Proxy functional test, not the production LB/Redis topology, not Law Insight integration, and not a load test.

Source: sibling `litellm_rang_dong`, verified at commit `5b13b8361e`. Test image uses Python 3.13 Debian rather than the fork's Wolfi image because its installed Python package failed to load GLIBC symbols. Source and uv.lock are unchanged. Only proxy and extra_proxy extras are installed; UI/runtime telemetry extras are not part of this test.

## Run from token-ledger-dashboard

```bash
docker build -f tools/gateway-smoke/Dockerfile -t tla-gateway-smoke:py313 ../litellm_rang_dong
python tools/gateway-smoke/run.py up
python tools/gateway-smoke/run.py test
python tools/gateway-smoke/run.py ps
```

`run.py` generates local test DB/master/salt credentials in `%LOCALAPPDATA%/Temp/tla-gateway-smoke-state.json`. Do not print or commit that file. No Google key is loaded or copied. The isolated internal Docker network blocks provider egress. Only the Proxy is published at `127.0.0.1:4100`; PostgreSQL is internal and has its own named volume/database.

The test creates an expiring app Virtual Key with `metadata.tags=["tla-hd"]`, verifies it via key/info, sends three concurrent requests with distinct synthetic X-User identities, checks invalid-key rejection, then polls SpendLogs. A successful run writes `result.json` with response IDs, usage and matching log rows. No successful result is implied by building this harness.

The test asserts response/log ID, user and token agreement, agent tag presence, no duplicate/missing rows and no canary prompt in selected log fields. It does not verify department mapping or token_ledger_v2 ingestion. The mock's token counts are synthetic and do not represent Google usage or billing.

Stop only services in this compose project when finished. Preserve the volume for diagnosis; do not use `down -v`. Never reuse this test image/config as a production rollout.
