'use strict';
const http = require('node:http');
const https = require('node:https');
const fs = require('node:fs');
const path = require('node:path');

const STATIC = new Map([
  ['/', ['index.html', 'text/html; charset=utf-8']],
  ['/app.js', ['app.js', 'application/javascript; charset=utf-8']],
  ['/style.css', ['style.css', 'text/css; charset=utf-8']],
]);
const SECURITY_HEADERS = {
  'Cache-Control': 'no-store',
  'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'",
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
};

const SCOPE = 'Liveness checks only. Provider access, credentials, database and Redis readiness are not verified.';
const COMPONENTS = [
  ['edge', 'Gateway edge', 'http://token-ledger-gateway-edge:8080/edge-health'],
  ['lb', 'Load balancer', 'http://token-ledger-gateway-lb:4000/lb-health'],
  ['proxy1', 'Proxy 1', 'http://token-ledger-litellm-1:4000/health/liveliness'],
  ['proxy2', 'Proxy 2', 'http://token-ledger-litellm-2:4000/health/liveliness'],
  ['route', 'Load-balanced route', 'http://token-ledger-gateway-lb:4000/health/liveliness'],
];

function probe(id, name, url, timeoutMs) {
  const start = performance.now();
  return new Promise(resolve => {
    const transport = new URL(url).protocol === 'https:' ? https : http;
    let done = false;
    let request;
    const finish = detail => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      request?.destroy();
      resolve({ id, name, status: detail ? 'unreachable' : 'reachable', detail: detail || 'Liveness check passed.', latency_ms: Math.round(performance.now() - start) });
    };
    // Start before request creation: socket inactivity timeouts do not bound DNS or trickle responses.
    const timer = setTimeout(() => finish('Liveness check timed out.'), timeoutMs);
    request = transport.get(url, { agent: false, headers: id === 'edge' ? { Host: process.env.LLM_GATEWAY_DOMAIN || 'apigateway.rangdong.com.vn' } : {} }, res => {
      res.on('error', () => finish('Connection failed.'));
      res.on('aborted', () => finish('Connection failed.'));
      if (res.statusCode !== 200) {
        finish(`HTTP ${res.statusCode} returned.`);
        res.destroy();
        return;
      }
      let bytes = 0;
      const chunks = [];
      res.on('data', chunk => {
        bytes += chunk.length;
        if (bytes > 4096) {
          finish('Liveness response too large.');
          res.destroy();
        } else chunks.push(chunk);
      });
      res.on('end', () => {
        const body = Buffer.concat(chunks).toString('utf8');
        let valid = false;
        if (id === 'edge' || id === 'lb') valid = body === `${id}-ok` || body === `${id}-ok\n`;
        else {
          // Pinned LiteLLM 4373a32: FastAPI serializes a JSON string, not an object.
          try { valid = JSON.parse(body) === "I'm alive!"; } catch { /* invalid body */ }
        }
        finish(valid ? null : 'Invalid liveness response.');
      });
    });
    request.on('error', error => finish(
      ['ENOTFOUND', 'EAI_AGAIN'].includes(error.code) ? 'Service name could not be resolved.'
        : error.code === 'ECONNREFUSED' ? 'Connection refused.'
          : error.code === 'ETIMEDOUT' ? 'Liveness check timed out.' : 'Connection failed.'
    ));
  });
}

function createMonitor({ targets = {}, timeoutMs = 2500, cacheMs = 1000 } = {}) {
  if (!Number.isFinite(timeoutMs) || timeoutMs < 1 || timeoutMs > 2500) throw new RangeError('Invalid probe deadline.');
  if (!Number.isFinite(cacheMs) || cacheMs < 0 || cacheMs > 2000) throw new RangeError('Invalid cache duration.');
  let cached;
  let expires = 0;
  let inFlight;
  async function collect() {
    if (cached && performance.now() < expires) return cached;
    if (!inFlight) {
      inFlight = Promise.all(COMPONENTS.map(([id, name, url]) => probe(id, name, targets[id] || url, timeoutMs)))
        .then(components => {
          const up = Object.fromEntries(components.map(c => [c.id, c.status === 'reachable']));
          const status = components.every(c => c.status === 'reachable') ? 'reachable'
            : up.edge && up.lb && up.route && (up.proxy1 || up.proxy2) ? 'degraded' : 'unavailable';
          cached = { status, checked_at: new Date().toISOString(), scope: SCOPE, components };
          expires = performance.now() + cacheMs;
          return cached;
        }).finally(() => { inFlight = null; });
    }
    return inFlight;
  }
  return http.createServer(async (req, res) => {
    for (const [name, value] of Object.entries(SECURITY_HEADERS)) res.setHeader(name, value);
    const send = (code, body, type = 'text/plain; charset=utf-8') => {
      res.writeHead(code, { 'Content-Type': type });
      res.end(body);
    };
    // Deliberately local-only browser access, including when Docker publishes the port.
    if (!/^(localhost|127\.0\.0\.1|\[::1\])(?::[0-9]{1,5})?$/i.test(req.headers.host || '')) {
      return send(403, 'Forbidden.');
    }
    if (req.method !== 'GET') {
      res.setHeader('Allow', 'GET');
      return send(405, 'Method not allowed.');
    }
    if (req.url === '/api/status') {
      try {
        return send(200, JSON.stringify(await collect()), 'application/json; charset=utf-8');
      } catch {
        return send(503, JSON.stringify({ error: 'Status collection unavailable.' }), 'application/json; charset=utf-8');
      }
    }
    const asset = STATIC.get(req.url);
    if (!asset) return send(404, 'Not found.');
    try {
      send(200, await fs.promises.readFile(path.join(__dirname, asset[0])), asset[1]);
    } catch {
      send(503, 'Status page unavailable.');
    }
  });
}

module.exports = { createMonitor };

if (require.main === module) {
  const fail = () => {
    console.error('Unable to start status monitor.');
    process.exitCode = 1;
  };
  const bind = process.env.STATUS_BIND || '127.0.0.1';
  const port = process.env.STATUS_PORT ?? '8089';
  if (!/^[0-9]{1,5}$/.test(port) || Number(port) > 65535 || !['127.0.0.1', '0.0.0.0', '::1', '::'].includes(bind)) {
    fail();
  } else {
    const server = createMonitor();
    server.on('error', fail);
    server.listen(Number(port), bind, () => {
      console.log(`Gateway status listening at http://127.0.0.1:${server.address().port}`);
    });
  }
}
