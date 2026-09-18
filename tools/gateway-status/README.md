# Gateway status web app

Private English-language monitor. Plain HTML/CSS/JavaScript plus a small Node.js HTTP collector using built-ins only. Independent from Dashboard; no npm install, API keys, Docker socket, raw container logs or paid model requests.

## Run

Requires Node.js 22 or later. From the repository root:

```powershell
node tools/gateway-status/server.js
```

Open **http://127.0.0.1:8089/** on the same machine. The same server serves assets and `GET /api/status`. The page refreshes every 10 seconds and has a manual refresh button. Keep all four runtime files together: `server.js`, `index.html`, `app.js`, `style.css`.

The root Compose file includes service `gateway-status` in profile `gateway`, with container name `token-ledger-gateway-status`. It has no `ports:` mapping — it is not reachable from the host directly, only from other containers on the same Compose network by service name (`gateway-status:8089`), which is how `gateway-lb` reaches it. It starts with the Gateway profile but deliberately has no backend dependencies, so unavailable backends can still be reported. It uses the standard Node image and read-only source mount; no image build is needed.

To add only the monitor to an existing stack, without restarting Dashboard or Gateway services:

```powershell
docker compose --profile gateway up -d --no-deps gateway-status
docker compose --profile gateway exec -T gateway-status wget -qO- http://127.0.0.1:8089/api/status
```

This assumes the shared Compose network is intact and matches its configuration. If Compose reports a network replacement/conflict, stop and inspect it; do not use `down`, delete the network or remove volumes to install the monitor. `--profile gateway down` also affects unprofiled Dashboard services. Do not run an older standalone monitor on the same port.

Defaults for direct Node execution are `STATUS_BIND=127.0.0.1`, `STATUS_PORT=8089`, and `LLM_GATEWAY_DOMAIN=apigateway.rangdong.com.vn`; Compose sets the internal bind to `0.0.0.0` and does **not** publish the port to the host. The only host-facing entry point for the stack is `gateway-lb` on `8088`, which proxies `/`, `/app.js`, `/style.css` and `/api/status` to this container internally. Do not expose the monitor publicly: it has no login and accepts only localhost/loopback Host headers.

## What is measured

| Component | Internal target |
| --- | --- |
| Load balancer | `http://token-ledger-gateway-lb:4000/lb-health` with the configured domain Host; expects `lb-ok` |
| LiteLLM 1 | `http://token-ledger-litellm-1:4000/health/liveliness` |
| LiteLLM 2 | `http://token-ledger-litellm-2:4000/health/liveliness` |
| LB to proxy route | `http://token-ledger-gateway-lb:4000/health/liveliness` |

The monitor must resolve/reach these names. Running Node directly on a Windows host usually cannot resolve Docker container names; the page still works but reports unreachable checks, not a successful Gateway connection. Adapt server-side targets when deploying a different topology, never accept target URLs from browser requests.

- **Gateway reachable**: all four liveness checks passed. Not proof of provider, authentication, database or Redis readiness, nor successful inference.
- **Gateway degraded**: LB, LB-to-proxy route and at least one proxy responded; the other proxy failed.
- **Gateway unavailable**: one or more required checks failed.
- **Status unknown**: no valid current measurement from the monitor. Stale results expire; a restored page invalidates its result before refreshing.

Each probe has a total deadline and size limit. DNS failures, refused connections, timeouts, invalid responses and HTTP errors produce controlled English observations. Raw response bodies and secrets never reach the browser.

A connection failure alone cannot distinguish a stopped container from a missing startup key. Exact startup causes require operator inspection of the affected service logs; the UI does not invent that cause. An already-open page detects loss of the monitor, but a fresh navigation cannot load if its own server is down. This is not an external uptime service.

## Tests

```powershell
node --test tests/gateway-status-ui.test.js tests/gateway-status-server.test.js
```

Tests use isolated HTTP fixtures, not real providers. Browser clock-based freshness checks assume reasonably synchronized browser/server clocks.

For isolated Nginx routing, auth/header forwarding, SSE and failure/recovery checks:

```sh
python tools/gateway-smoke/harnesses/lb_handoff_test.py /path/to/nginx
```

Requires Nginx >=1.27.3 and Node. Uses temporary config, the real Node status
server and loopback mock inference backends only. Checks web assets/status,
TCP-peer ACL with spoofed XFF, header stripping, prefix/query/body forwarding,
legacy API, SSE, no replay, upstream faults, LB-down status fallback and startup
with missing status DNS. The fallback uses an ephemeral port, not host 8089.
The harness replaces Docker upstream names with loopback addresses and shortens
passive recovery to one second; it does **not** verify Docker DNS rotation,
Compose image startup, public TLS/DNS, provider auth or real inference. On Windows
it uses a 64-byte server-name hash bucket (the native build defaults to 32).


## Migrating the former edge into the LB

The only inference hop in this stack is now `gateway-lb:4000`. Host port `8088`
uses the existing `LLM_GATEWAY_EDGE_BIND` / `LLM_GATEWAY_EDGE_PORT` variables for
compatibility (loopback by default). TLS/DNS remain outside this stack, with
`Host: apigateway.rangdong.com.vn` and the incoming `X-Forwarded-Proto` preserved.
`/gateway/v1/chat/completions` strips `/gateway` before forwarding; legacy
`/v1/chat/completions` remains unchanged. `/edge-health` remains a
compatibility alias reporting **Nginx liveness only**, alongside `/lb-health`.
Internal LB Host names also allow `/health/liveliness` and `/health/readiness`.
The root `/`, `/app.js`, `/style.css`, and `/api/status` proxy to the existing
status server with only `Host: localhost`, no client headers or body. Other paths
return 404; unknown hosts are rejected. LiteLLM ports stay unpublished.

### Same-port web and API

- Web: `http://127.0.0.1:8088/` (admin ACL applies), or `http://192.168.20.111:8088/`
  from the LAN once `LLM_GATEWAY_EDGE_BIND` is set to that address (see below).
- OpenAI `base_url`: `http://127.0.0.1:8088/gateway/v1` (or the LAN address). Chat
  completions routes are not gated by either allowlist below, only by API key.
- `8089` is not published to the host. When Nginx is down and `8088` is
  unreachable, check the monitor directly inside its own container instead:
  `docker compose --profile gateway exec -T gateway-status wget -qO- http://127.0.0.1:8089/api/status`.

The UI has **no login**. Nginx allows loopback TCP peers plus two separate,
independently configured allowlists for the four web routes (`/`, `/app.js`,
`/style.css`, `/api/status`), and denies everyone else. It never trusts client
`X-Forwarded-For` for this ACL:

- `LLM_GATEWAY_ADMIN_CIDR` (default `127.0.0.1/32`) — the operator machine.
  Docker Desktop on Windows may NAT loopback requests to its bridge gateway
  address instead of `127.0.0.1` (see below); verify the real peer before
  widening this.
- `LLM_GATEWAY_LAN_CIDR` (default `127.0.0.1/32`, i.e. no LAN access) — other
  machines on the local network allowed to view the web/status UI. Set it to
  a real, narrow subnet (e.g. `192.168.20.0/24`), never `0.0.0.0/0`.

For direct LAN use, an operator must also set
`LLM_GATEWAY_EDGE_BIND=192.168.20.111` (bind the published port to the LAN
interface instead of loopback-only) and firewall 8088 to intended callers. No
subnet is assumed by default for either CIDR. Both are trusted operator
configuration, not request input; keep each a single valid address/CIDR.

Docker NAT may present a host/bridge address instead of loopback. Until its TCP
peer is verified and explicitly allowed, 8088 web access can fail closed with
403; use `docker compose --profile gateway exec -T gateway-status wget -qO-
http://127.0.0.1:8089/api/status` meanwhile. Do not allow the entire Docker subnet as a
shortcut. If multiple clients share a NAT peer, enforce admin restrictions
before NAT. When infrastructure TLS proxies share one allowed peer, **that
proxy must enforce the admin ACL on `/`, `/app.js`, `/style.css`, `/api/status`**;
otherwise every external user behind it would inherit web access. API callers
retain their existing authentication/identity policy, not the web ACL.

Status DNS is dynamic and status is not an LB startup dependency. Its absence
can fail web requests without stopping inference. Recreate only LB when changing
environment values; no live bind, firewall or deployment changes are made here.

Operator procedure only; these commands are not an automatic deployment:

1. Validate `docker compose --profile gateway config --quiet`. Inspect the existing
   `token-ledger-gateway-edge` container's Compose labels and port ownership, and
   confirm the shared network is intact. Stop on any ownership/network mismatch.
2. In a maintenance window, remove **only** the verified old edge container to free
   8088, then recreate **only** the LB (not its dependencies):

   ```sh
   docker stop token-ledger-gateway-edge
   docker rm token-ledger-gateway-edge
   docker compose --profile gateway up -d --no-deps gateway-lb
   docker compose --profile gateway exec -T gateway-lb nginx -t
   curl --fail -H 'Host: apigateway.rangdong.com.vn' http://127.0.0.1:8088/lb-health
   docker compose --profile gateway up -d --no-deps gateway-status
   docker compose --profile gateway restart gateway-status
   docker compose --profile gateway exec -T gateway-status wget -qO- http://127.0.0.1:8089/api/status
   ```

   The monitor restart loads its changed collector; it stays independent of LB
   outages. `up --no-deps` leaves Dashboard, PostgreSQL, Redis and LiteLLM untouched.
   Do not run `compose down`, `--remove-orphans`, volume or network removal.
   Expect a brief handoff outage between removing the old edge and LB readiness.
3. Verify four current monitor components and the internal liveness route; a green
   LB alone does not prove inference. Verify root/assets/status on 8088 from an
   allowed admin peer and 403 from a denied peer; check `gateway-status` directly
   with `docker compose exec` (see above) as fallback, since 8089 is not published
   to the host.
   `/status/` is not a route. Preserve the prior revision/config for rollback: stop/remove only the
   new LB to release 8088, restore the previous gateway files, then recreate only
   the previous LB and edge with `up -d --no-deps gateway-lb gateway-edge`.

`nginx.conf` is now mounted as an envsubst template. After editing it, `restart gateway-lb` regenerates the rendered config; testing the old running config before
that restart does not validate the edited template. Keep Docker DNS `resolver`,
upstream `zone` and `resolve`; do not enable `non_idempotent` retries.
