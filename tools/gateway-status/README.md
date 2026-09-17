# Gateway status web app

Private English-language monitor. Plain HTML/CSS/JavaScript plus a small Node.js HTTP collector using built-ins only. Independent from Dashboard; no npm install, API keys, Docker socket, raw container logs or paid model requests.

## Run

Requires Node.js 22 or later. From the repository root:

```powershell
node tools/gateway-status/server.js
```

Open **http://127.0.0.1:8089/** on the same machine. The same server serves assets and `GET /api/status`. The page refreshes every 10 seconds and has a manual refresh button. Keep all four runtime files together: `server.js`, `index.html`, `app.js`, `style.css`.

No Docker or Compose configuration is included. Server deployment is managed separately by the operator. For container deployment, set `STATUS_BIND=0.0.0.0`, publish port 8089 on host loopback only, and attach the monitor to the existing Gateway network. Defaults are `STATUS_BIND=127.0.0.1`, `STATUS_PORT=8089`, and `LLM_GATEWAY_DOMAIN=apigateway.rangdong.com.vn`. Do not expose the monitor publicly: it has no login and accepts only localhost/loopback Host headers.

## What is measured

| Component | Internal target |
| --- | --- |
| Nginx edge | `http://token-ledger-gateway-edge:8080/edge-health` with the configured Host; expects `edge-ok` |
| Load balancer | `http://token-ledger-gateway-lb:4000/lb-health`; expects `lb-ok` |
| LiteLLM 1 | `http://token-ledger-litellm-1:4000/health/liveliness` |
| LiteLLM 2 | `http://token-ledger-litellm-2:4000/health/liveliness` |
| LB to proxy route | `http://token-ledger-gateway-lb:4000/health/liveliness` |

The monitor must resolve/reach these names. Running Node directly on a Windows host usually cannot resolve Docker container names; the page still works but reports unreachable checks, not a successful Gateway connection. Adapt server-side targets when deploying a different topology, never accept target URLs from browser requests.

- **Gateway reachable**: all five liveness checks passed. Not proof of provider, authentication, database or Redis readiness, nor successful inference.
- **Gateway degraded**: edge, LB, LB-to-proxy route and at least one proxy responded; the other proxy failed.
- **Gateway unavailable**: one or more required checks failed.
- **Status unknown**: no valid current measurement from the monitor. Stale results expire; a restored page invalidates its result before refreshing.

Each probe has a total deadline and size limit. DNS failures, refused connections, timeouts, invalid responses and HTTP errors produce controlled English observations. Raw response bodies and secrets never reach the browser.

A connection failure alone cannot distinguish a stopped container from a missing startup key. Exact startup causes require operator inspection of the affected service logs; the UI does not invent that cause. An already-open page detects loss of the monitor, but a fresh navigation cannot load if its own server is down. This is not an external uptime service.

## Tests

```powershell
node --test tests/gateway-status-ui.test.js tests/gateway-status-server.test.js
```

Tests use isolated HTTP fixtures, not real providers. Browser clock-based freshness checks assume reasonably synchronized browser/server clocks.
