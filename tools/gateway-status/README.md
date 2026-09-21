# Gateway status web app

Private English-language monitor using existing HTML/CSS/JavaScript and a built-in Node HTTP collector. No npm install, API keys, Docker socket, raw logs or paid model calls.

## Single-container Gateway

`token-ledger-gateway-lb` now contains **Nginx + Node**, not a separate status service. Published Gateway ports are HTTP `${LLM_GATEWAY_EDGE_BIND:-127.0.0.1}:${LLM_GATEWAY_EDGE_PORT:-8088}:4000` and additive HTTPS `${LLM_GATEWAY_TLS_BIND:-127.0.0.1}:${LLM_GATEWAY_TLS_PORT:-443}:4443` (certificates: `docker/gateway/tls/README.md`). Node listens only on container loopback `127.0.0.1:8089`; there is **no host 8089 fallback**.

- `/`, `/app.js`, `/style.css`, `/api/status`: existing collector/frontend through Nginx, admin TCP-peer ACL, only `Host: localhost` forwarded, no client credentials or body.
- `/gateway/v1/chat/completions`: strips `/gateway`, preserves query/body/auth/identity; OpenAI base URL `/gateway/v1`.
- `/v1/chat/completions`: legacy compatibility.
- `/lb-health`, `/edge-health`: Nginx liveness only. Container health additionally checks that Node serves HTTP, without requiring any backend to be healthy.
- Internal LB hostnames retain `/health/liveliness` and `/health/readiness`. Other paths return 404; unknown hosts are rejected.

The image builds from `docker/gateway/Dockerfile` using the existing Nginx base and Alpine Node (22+), Bash, Tini and su-exec. Tini reaps adopted children; Bash forwards shutdown to service process groups, gracefully drains Nginx, stops Node, and exits nonzero when either service exits unexpectedly. A 25-second bound fits Compose's 30-second stop grace. Node runs as the unprivileged `nginx` user. No backend `depends_on` gate prevents the web starting when LiteLLM is absent.

**Shared failure domain:** losing either process stops the entire container. Web and inference are both unavailable until restart; an already-open page expires its previous result to unknown. This is not an independent uptime monitor. Dashboard remains separate and also gains its own TLS listener.

## Infrastructure handoff (operator configuration, not deployed here)

```text
Public FQDN: apigateway.rangdong.com.vn
Public TLS: gateway-lb :4443 (host :443 by default), or an approved infrastructure reverse proxy
Application upstream: http://<verified-VM-IP>:8088
Web: /
OpenAI base URL: https://apigateway.rangdong.com.vn/gateway/v1
Chat endpoint: /gateway/v1/chat/completions
```

Keep `Host`, `Authorization`, trusted `X-User`, `X-Forwarded-For` and incoming `X-Forwarded-Proto`; allow 25 MB request bodies and 600-second inference timeouts, disable response buffering/cache for SSE, and never retry an already-sent inference POST.

Binding and `LLM_GATEWAY_ADMIN_CIDR` default to loopback, deliberately. No admin subnet or proxy address is assumed. For a separate TLS-proxy machine, the operator must verify the VM address and actual TCP peer, bind 8088 to the VM LAN IP, firewall-allow only the infrastructure proxy, and set an approved admin source `/32` or CIDR. Docker NAT can make local host requests appear from a bridge peer: web 403 is expected until that peer is verified. Do not broaden to the whole Docker subnet or `0.0.0.0/0` to bypass this check.

`LLM_GATEWAY_LAN_CIDR` separately allows approved LAN peers (default `127.0.0.1/32`). Keep both CIDRs narrow; neither trusts client X-Forwarded-For.

The UI has no login. If all users share an allowed TLS-proxy/NAT peer, that proxy **must enforce admin access** for all four web routes before forwarding. Client XFF does not grant web access. Inference retains its existing auth policy, not the web ACL. Domain/CIDR are trusted operator configuration and must be a valid hostname and single address/CIDR. Envsubst is restricted to DOMAIN, ADMIN_CIDR and LAN_CIDR; Nginx runtime variables and dynamic Docker DNS (`resolver`, `zone`, `resolve`) are preserved.

## Minimal migration — Gateway LB only

These are operator instructions, not an automatic deployment. Inspect the existing LB/status container Compose labels, project, network and port ownership first. Stop on any ownership/network replacement mismatch. Preserve the previous LB image and config for rollback.

1. Validate `docker compose --profile gateway config --quiet` and build only `docker compose build gateway-lb`.
2. In a maintenance window run `docker compose --profile gateway up -d --no-deps gateway-lb`. This recreates only LB; do not use `compose down`, `--remove-orphans`, network/volume removal, or restart Dashboard, PostgreSQL, pgAdmin, Redis or LiteLLM.
3. Verify `docker compose exec -T gateway-lb nginx -t`, container health, `/lb-health`, root/assets/status from an allowed admin peer and 403 from a denied peer. An internal diagnostic without publishing Node is `docker compose exec -T gateway-lb wget -q -O- http://127.0.0.1:4000/api/status`. Verify current component observations separately from actual inference readiness.
4. **Only after the new LB is verified**, remove the verified obsolete collector: `docker stop token-ledger-gateway-status` then `docker rm token-ledger-gateway-status`. Leaving it temporarily during verification does not make it part of the new topology. If an even older edge still owns 8088, resolve that exact container's ownership in the maintenance window; do not broadly remove orphans.

Rollback before removing the old collector: restore the saved prior LB configuration/image and recreate only LB with `--no-deps`. After removal, rollback also requires restoring the previous Compose status service and explicitly starting only it. Expect a brief LB/web outage during recreation. Source is copied into the image, so collector/frontend/entrypoint edits require rebuilding LB; Nginx template bind-mount edits require restart to rerender. Testing an old running config does not validate an edited template.

## What is measured

| Component | Internal target |
| --- | --- |
| Load balancer | `http://token-ledger-gateway-lb:4000/lb-health` with configured domain Host; expects `lb-ok` |
| Proxy 1 | `http://token-ledger-litellm-1:4000/health/liveliness` |
| Proxy 2 | `http://token-ledger-litellm-2:4000/health/liveliness` |
| Load-balanced route | `http://token-ledger-gateway-lb:4000/health/liveliness` |

Reachable means all four liveness checks passed, not provider/auth/database/Redis readiness or successful inference. Degraded means LB, route and one proxy respond. Unavailable means required checks failed; unknown means no valid current monitor snapshot. Probes have total deadlines/size limits and sanitized observations; they never infer a missing startup key from a failed connection. Stale browser results expire and page restoration invalidates them.

## Local development and tests

Standalone development remains `node tools/gateway-status/server.js` (Node 22+), serving `http://127.0.0.1:8089/` by default. This is not the deployed container topology; host Node usually cannot resolve Docker container names. Keep all four runtime files together. Do not expose this unauthenticated development server publicly.

```sh
node --test tests/*.test.js
python -m unittest discover -s tests -p 'test_*.py'
python tools/gateway-smoke/harnesses/lb_handoff_test.py /path/to/nginx
python tools/gateway-smoke/harnesses/lb_bundle_test.py
```

Native harness requires Nginx >=1.27.3 and Node; it uses ephemeral loopback backends and the real collector, testing ACL/header stripping, routing/auth/query/body, SSE, no replay, upstream faults and recovery. It does not test container supervision or Docker DNS.

Docker harness builds the actual image, creates a unique mock-only network and loopback ephemeral publication, then removes only its own resources. It tests image/envsubst/health, missing backends at startup and subsequent discovery, web/assets/status, transport/fault behavior, Node hang detection, process death supervision and graceful stop. No production services, paid inference, public TLS/DNS or cloud provider readiness are tested.
