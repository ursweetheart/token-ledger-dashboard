const test = require('node:test');
const assert = require('node:assert/strict');
const http = require('node:http');
const { createMonitor } = require('../tools/gateway-status/server');

const ids = ['edge', 'lb', 'proxy1', 'proxy2', 'route'];
const bodies = { edge: 'edge-ok\n', lb: 'lb-ok\n', proxy1: JSON.stringify("I'm alive!"), proxy2: JSON.stringify("I'm alive!"), route: JSON.stringify("I'm alive!") };
async function listen(t, server) {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => { server.close(resolve); server.closeAllConnections(); }));
  return `http://127.0.0.1:${server.address().port}`;
}
async function fixture(t, overrides = {}, options = {}) {
  const hits = [];
  const upstream = await listen(t, http.createServer((req, res) => {
    const id = req.url.slice(1);
    hits.push({ id, headers: req.headers });
    if (overrides[id]) return overrides[id](req, res);
    res.end(bodies[id]);
  }));
  const targets = Object.fromEntries(ids.map(id => [id, `${upstream}/${id}`]));
  const url = await listen(t, createMonitor({ targets, cacheMs: 0, ...options }));
  return { url, hits };
}
async function status(url) { return (await fetch(`${url}/api/status`)).json(); }
test('rejects invalid health bodies, redirects, oversized bodies without leaking content', async t => {
  for (const [id, body] of [['edge', 'edge-ok SECRET'], ['lb', 'lb-ok extra'], ['proxy1', 'I\'m alive!'], ['proxy2', '{"status":"ok","key":"SECRET"}'], ['route', 'null']]) {
    const { url } = await fixture(t, { [id]: (_req, res) => res.end(body) });
    const component = (await status(url)).components.find(c => c.id === id);
    assert.equal(component.status, 'unreachable');
    assert.equal(component.detail, 'Invalid liveness response.');
    assert.doesNotMatch(JSON.stringify(component), /SECRET/);
  }
  const { url, hits } = await fixture(t, {
    proxy1: (_req, res) => { res.writeHead(302, { Location: '/SECRET' }); res.end(); },
    proxy2: (_req, res) => res.end('x'.repeat(4097)),
  });
  const result = await status(url);
  assert.equal(result.components[2].detail, 'HTTP 302 returned.');
  assert.equal(result.components[3].detail, 'Liveness response too large.');
  assert.equal(hits.length, 5);
});

test('bounds total time including a response that keeps sending bytes', async t => {
  const { url } = await fixture(t, {
    proxy1: (_req, _res) => {},
    proxy2: (_req, res) => {
      res.write('"');
      const timer = setInterval(() => res.write(' '), 10);
      res.on('close', () => clearInterval(timer));
    },
  }, { timeoutMs: 80 });
  const start = performance.now();
  const response = await fetch(`${url}/api/status`, { signal: AbortSignal.timeout(1500) });
  const result = await response.json();
  assert.ok(performance.now() - start < 1000);
  for (const c of result.components.slice(2, 4)) {
    assert.equal(c.status, 'unreachable');
    assert.equal(c.detail, 'Liveness check timed out.');
  }
});

test('DNS and connection refusal are controlled English without URL or error leaks', async t => {
  const closed = http.createServer();
  const closedUrl = await listen(t, closed);
  await new Promise(resolve => closed.close(resolve));
  const { url } = await fixture(t, {}, { targets: {
    edge: 'http://secret-credential.invalid/SECRET', lb: closedUrl,
    proxy1: closedUrl, proxy2: closedUrl, route: closedUrl,
  } });
  const result = await status(url);
  assert.equal(result.components[0].detail, 'Service name could not be resolved.');
  assert.equal(result.components[1].detail, 'Connection refused.');
  assert.doesNotMatch(JSON.stringify(result), /SECRET|secret-credential|127\.0\.0\.1|ECONN|ENOTFOUND/);
});

test('concurrent callers share one collection and cache expires', async t => {
  const { url, hits } = await fixture(t, { edge: (_req, res) => setTimeout(() => res.end(bodies.edge), 30) }, { cacheMs: 80 });
  const batch = await Promise.all(Array.from({ length: 12 }, () => status(url)));
  assert.equal(hits.length, 5);
  for (const result of batch) assert.deepEqual(result, batch[0]);
  assert.deepEqual(await status(url), batch[0]);
  assert.equal(hits.length, 5);
  await new Promise(resolve => setTimeout(resolve, 100));
  await status(url);
  assert.equal(hits.length, 10);
});

function request(url, pathname, options = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request(url, { path: pathname, ...options }, res => {
      let body = '';
      res.setEncoding('utf8');
      res.on('data', chunk => { body += chunk; });
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body }));
    });
    req.on('error', reject);
    req.end();
  });
}

test('strict routing and security headers expose only approved static files and API', async t => {
  const fs = require('node:fs');
  const path = require('node:path');
  const { url, hits } = await fixture(t);
  for (const [route, filename, type] of [['/', 'index.html', 'text/html'], ['/app.js', 'app.js', 'application/javascript'], ['/style.css', 'style.css', 'text/css']]) {
    const result = await request(url, route);
    const file = path.join(__dirname, '../tools/gateway-status', filename);
    assert.equal(result.status, fs.existsSync(file) ? 200 : 503);
    if (fs.existsSync(file)) {
      assert.equal(result.body, fs.readFileSync(file, 'utf8'));
      assert.ok(result.headers['content-type'].startsWith(type));
    }
    assert.equal(result.headers['cache-control'], 'no-store');
    assert.equal(result.headers['x-content-type-options'], 'nosniff');
    assert.equal(result.headers['x-frame-options'], 'DENY');
    assert.equal(result.headers['referrer-policy'], 'no-referrer');
    assert.match(result.headers['content-security-policy'], /default-src 'self'/);
    assert.doesNotMatch(result.headers['content-security-policy'], /unsafe-inline|unsafe-eval/);
  }
  for (const pathname of ['/server.js', '/.env', '/index.html', '/../server.js', '/%2e%2e/.env', '/api/status?url=http://SECRET', '/app.js?x=1']) {
    const result = await request(url, pathname);
    assert.equal(result.status, 404);
    assert.doesNotMatch(result.body, /SECRET|require\(|process.env/);
  }
  for (const method of ['POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS']) {
    const result = await request(url, '/api/status', { method });
    assert.equal(result.status, 405);
    assert.equal(result.headers.allow, 'GET');
  }
  assert.equal(hits.length, 0);
  const result = await request(url, '/api/status', { headers: { Authorization: 'Bearer SECRET', Cookie: 'secret=SECRET', Origin: 'http://evil.invalid' } });
  assert.equal(result.status, 200);
  assert.equal(result.headers['cache-control'], 'no-store');
  assert.equal(result.headers['access-control-allow-origin'], undefined);
  for (const hit of hits) {
    assert.equal(hit.headers.authorization, undefined);
    assert.equal(hit.headers.cookie, undefined);
  }
});

test('rejects browser DNS-rebinding Host values before probing', async t => {
  const { url, hits } = await fixture(t);
  for (const host of ['evil.invalid', 'localhost.evil.invalid', '127.0.0.1.evil.invalid', 'localhost@evil.invalid', '127.0.0.1:bad']) {
    assert.equal((await request(url, '/api/status', { headers: { Host: host } })).status, 403);
  }
  assert.equal(hits.length, 0);
  assert.equal((await request(url, '/api/status', { headers: { Host: 'localhost:8089' } })).status, 200);
});

test('internal collector failure returns a generic 503 and retries next time', async t => {
  const targets = {};
  Object.defineProperty(targets, 'edge', { get() { throw new Error('SECRET internal path'); } });
  const url = await listen(t, createMonitor({ targets }));
  const response = await fetch(`${url}/api/status`, { signal: AbortSignal.timeout(500) });
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: 'Status collection unavailable.' });
  assert.equal((await request(url, '/api/status')).status, 503);
});

test('factory rejects unsafe timeout and cache limits', () => {
  for (const timeoutMs of [0, -1, 2501, NaN, Infinity, '80']) assert.throws(() => createMonitor({ timeoutMs }));
  for (const cacheMs of [-1, 2001, NaN, Infinity, '80']) assert.throws(() => createMonitor({ cacheMs }));
});

test('default probes use actual Docker container names, not optional network aliases', async t => {
  const seen = [];
  const originalGet = http.get;
  const upstream = await listen(t, http.createServer((req, res) => {
    res.end(req.url === '/edge-health' ? bodies.edge : req.url === '/lb-health' ? bodies.lb : bodies.proxy1);
  }));
  t.mock.method(http, 'get', (url, options, callback) => {
    seen.push(String(url));
    return originalGet(`${upstream}${new URL(url).pathname}`, options, callback);
  });
  const url = await listen(t, createMonitor());
  assert.equal((await status(url)).status, 'reachable');
  assert.deepEqual(seen, [
    'http://token-ledger-gateway-edge:8080/edge-health',
    'http://token-ledger-gateway-lb:4000/lb-health',
    'http://token-ledger-litellm-1:4000/health/liveliness',
    'http://token-ledger-litellm-2:4000/health/liveliness',
    'http://token-ledger-gateway-lb:4000/health/liveliness',
  ]);
});

test('CLI starts on loopback with STATUS_PORT and rejects invalid ports without leaking config', async t => {
  const { spawn, spawnSync } = require('node:child_process');
  const path = require('node:path');
  const file = path.join(__dirname, '../tools/gateway-status/server.js');
  const child = spawn(process.execPath, [file], { env: { ...process.env, STATUS_BIND: '127.0.0.1', STATUS_PORT: '0' }, stdio: ['ignore', 'pipe', 'pipe'] });
  t.after(() => child.kill());
  const url = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error('CLI failed to become ready')), 1500);
    child.once('exit', () => { clearTimeout(timer); reject(new Error('CLI exited before listening')); });
    child.stdout.on('data', data => {
      const match = String(data).match(/http:\/\/127\.0\.0\.1:\d+/);
      if (match) { clearTimeout(timer); resolve(match[0]); }
    });
  });
  assert.equal((await request(url, '/server.js')).status, 404);
  for (const value of ['SECRET', '-1', '65536', '80junk']) {
    const result = spawnSync(process.execPath, [file], { env: { ...process.env, STATUS_PORT: value }, encoding: 'utf8', timeout: 2000 });
    assert.equal(result.status, 1);
    assert.equal(result.stderr.trim(), 'Unable to start status monitor.');
  }
});

test('deadline covers stalled DNS before a socket connects', async t => {
  const originalGet = http.get;
  t.mock.method(http, 'get', (url, options, callback) => originalGet(url, { ...options, lookup() {} }, callback));
  const targets = Object.fromEntries(ids.map(id => [id, 'http://lookup-stalled.invalid/health']));
  const url = await listen(t, createMonitor({ targets, timeoutMs: 50 }));
  const response = await fetch(`${url}/api/status`, { signal: AbortSignal.timeout(1000) });
  const result = await response.json();
  assert.equal(result.status, 'unavailable');
  assert.ok(result.components.every(c => c.detail === 'Liveness check timed out.'));
});

test('broken responses fail safely and the exact 4096-byte limit succeeds', async t => {
  const valid = JSON.stringify("I'm alive!");
  const { url } = await fixture(t, {
    proxy1: (_req, res) => { res.writeHead(200, { 'Content-Length': 100 }); res.write(valid); res.socket.destroy(); },
    proxy2: (_req, res) => res.end(valid + ' '.repeat(4096 - Buffer.byteLength(valid))),
  });
  const result = await status(url);
  assert.equal(result.status, 'degraded');
  assert.equal(result.components[2].detail, 'Connection failed.');
  assert.equal(result.components[3].status, 'reachable');
});

const httpError = (_req, res) => { res.writeHead(503); res.end('SECRET credential'); };

test('one failed proxy degrades but failed load balancer or both proxies makes unavailable', async t => {
  for (const [overrides, expected] of [
    [{ proxy1: httpError }, 'degraded'],
    [{ proxy2: httpError }, 'degraded'],
    [{ lb: httpError }, 'unavailable'],
    [{ edge: httpError }, 'unavailable'],
    [{ route: httpError }, 'unavailable'],
    [{ proxy1: httpError, proxy2: httpError }, 'unavailable'],
  ]) {
    const { url } = await fixture(t, overrides);
    const result = await status(url);
    assert.equal(result.status, expected);
    for (const id of Object.keys(overrides)) {
      assert.equal(result.components.find(c => c.id === id).status, 'unreachable');
      assert.equal(result.components.find(c => c.id === id).detail, 'HTTP 503 returned.');
    }
    assert.doesNotMatch(JSON.stringify(result), /SECRET|credential\"/);
  }
});

test('all five real HTTP liveness checks produce the public contract', async t => {
  const { url, hits } = await fixture(t);
  const result = await status(url);
  assert.equal(result.status, 'reachable');
  assert.equal(result.scope, 'Liveness checks only. Provider access, credentials, database and Redis readiness are not verified.');
  assert.equal(new Date(result.checked_at).toISOString(), result.checked_at);
  assert.deepEqual(result.components.map(c => c.id), ids);
  for (const c of result.components) {
    assert.equal(c.status, 'reachable');
    assert.equal(c.detail, 'Liveness check passed.');
    assert.equal(typeof c.name, 'string');
    assert.ok(Number.isFinite(c.latency_ms) && c.latency_ms >= 0);
  }
  assert.equal(hits.length, 5);
  assert.equal(hits.find(h => h.id === 'edge').headers.host, process.env.LLM_GATEWAY_DOMAIN || 'apigateway.rangdong.com.vn');
});
