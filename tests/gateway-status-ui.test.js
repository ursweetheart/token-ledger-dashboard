const test = require('node:test');
const assert = require('node:assert/strict');
const {createMonitorUI} = require('../tools/gateway-status/app.js');
const {readFileSync} = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const read = file => readFileSync(path.join(root, file), 'utf8');


test('status web starts with gateway profile independently of unhealthy backends', () => {
  const compose = read('docker-compose.yml');
  const block = compose.match(/^  gateway-status:\r?\n(?:(?: {4}[^\n]*|\s*)\r?\n)*/m)?.[0];
  assert.ok(block, 'gateway-status service must exist');
  assert.match(block, /profiles: \["gateway"\]/);
  assert.match(block, /container_name: token-ledger-gateway-status/);
  assert.match(block, /127\.0\.0\.1:8089:8089/);
  assert.match(block, /STATUS_BIND: "0\.0\.0\.0"/);
  assert.match(block, /\.\/tools\/gateway-status:\/app:ro/);
  assert.match(block, /command: \["node", "server\.js"\]/);
  assert.doesNotMatch(block, /depends_on:|docker\.sock|env_file:/);
});

const html = read('tools/gateway-status/index.html');
test.beforeEach(t => t.mock.timers.enable({apis: ['Date', 'setTimeout', 'setInterval'], now: 1800000000000}));
test('scrollable table has a named keyboard focus target with visible focus', () => {
  const wrapper = html.match(/<div\b[^>]*class="table-scroll"[^>]*>/)[0];
  assert.match(wrapper, /tabindex="0"/);
  assert.match(wrapper, /role="region"/);
  assert.match(wrapper, /aria-labelledby="components-heading"/);
  assert.match(read('tools/gateway-status/style.css'), /\.table-scroll:focus-visible\s*\{[^}]*outline:/);
});

test('atomic status announcement excludes the frequently updated timestamp', () => {
  const live = html.match(/<(?<tag>\w+)\b[^>]*aria-live="polite"[^>]*aria-atomic="true"[^>]*>(?<body>[\s\S]*?)<\/\k<tag>>/);
  assert.ok(live, 'Expected a polite atomic status announcement');
  assert.match(live.groups.body, /id="overall"/);
  assert.match(live.groups.body, /id="summary"/);
  assert.doesNotMatch(live.groups.body, /id="checked"/);
  assert.match(html, /id="checked"/);
});

function harness(options) {
  const nodes = new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(([, id]) =>
    [id, Object.assign(new EventTarget(), {textContent: '', dataset: {}, disabled: false})]));
  const document = Object.assign(new EventTarget(), {visibilityState: 'visible', getElementById(id) {
    assert.ok(nodes.has(id), `Missing HTML ID: ${id}`);
    return nodes.get(id);
  }});
  const window = new EventTarget();
  return {nodes, document, window, ui: createMonitorUI(document, options)};
}
function snapshot() {
  return {status: 'reachable', checked_at: new Date().toISOString(), components:
    ['edge', 'lb', 'proxy1', 'proxy2', 'route'].map(id => ({id, status: 'reachable', detail: 'HTTP check passed.', latency_ms: 3}))};
}

test('monitor shows measured liveness, never claims provider readiness', async () => {
  const {nodes, ui} = harness();
  await ui.refresh(async () => ({ok: true, json: async () => snapshot()}));
  assert.equal(nodes.get('overall').textContent, 'Gateway reachable');
  assert.equal(nodes.get('proxy1-status').textContent, 'Reachable');
  assert.match(nodes.get('scope').textContent, /Provider.*not verified/);
  assert.equal(nodes.get('refresh').disabled, false);
});

test('failed monitor refresh clears previously reachable components', async () => {
  const {nodes, ui} = harness();
  await ui.refresh(async () => ({ok: true, json: async () => snapshot()}));
  await ui.refresh(async () => { throw new Error('secret diagnostic'); });
  assert.equal(nodes.get('overall').textContent, 'Status unknown');
  assert.equal(nodes.get('edge-status').textContent, 'Unknown');
  assert.doesNotMatch(nodes.get('summary').textContent, /secret diagnostic/);
});

test('stale, incomplete and inconsistent snapshots cannot show green', async () => {
  for (const modify of [
    d => { d.checked_at = '2000-01-01T00:00:00Z'; },
    d => { d.components.pop(); },
    d => { d.components[0].status = 'unreachable'; },
    d => { d.components[0].latency_ms = -1; }
  ]) {
    const {nodes, ui} = harness();
    const data = snapshot(); modify(data);
    await ui.refresh(async () => ({ok: true, json: async () => data}));
    assert.equal(nodes.get('overall').textContent, 'Status unknown');
  }
});

test('one proxy outage, LB outage and recovery show distinct measured states', async () => {
  const {nodes, ui} = harness();
  for (const [id, status, label] of [
    ['proxy1', 'degraded', 'Gateway degraded'],
    ['lb', 'unavailable', 'Gateway unavailable'],
    [null, 'reachable', 'Gateway reachable']
  ]) {
    const data = snapshot(); data.status = status;
    if (id) data.components.find(c => c.id === id).status = 'unreachable';
    await ui.refresh(async () => ({ok: true, json: async () => data}));
    assert.equal(nodes.get('overall').textContent, label);
  }
});

test('a 29-second snapshot expires at 30 seconds between polls', async t => {
  const {nodes, ui} = harness();
  const data = snapshot();
  data.checked_at = new Date(Date.now() - 29000).toISOString();
  await ui.refresh(async () => ({ok: true, json: async () => data}));
  assert.equal(nodes.get('overall').dataset.state, 'reachable');
  t.mock.timers.tick(999);
  assert.equal(nodes.get('overall').dataset.state, 'reachable');
  t.mock.timers.tick(1);
  assert.equal(nodes.get('overall').dataset.state, 'unknown');
  for (const id of ['edge', 'lb', 'proxy1', 'proxy2', 'route']) {
    assert.equal(nodes.get(`${id}-status`).dataset.state, 'unknown');
  }
  assert.equal(nodes.get('checked').textContent, 'No current measurement');
});

test('snapshots already 30 seconds old are rejected', async () => {
  const {nodes, ui} = harness();
  const data = snapshot();
  data.checked_at = new Date(Date.now() - 30000).toISOString();
  await ui.refresh(async () => ({ok: true, json: async () => data}));
  assert.equal(nodes.get('overall').dataset.state, 'unknown');
});

for (const event of ['pageshow', 'visibilitychange']) {
  test(`${event} restoration invalidates synchronously before refreshing`, async t => {
    const {nodes, ui, document, window} = harness();
    let calls = 0;
    const fetcher = async () => {
      calls++;
      assert.equal(nodes.get('overall').dataset.state, 'unknown');
      return {ok: true, json: async () => snapshot()};
    };
    assert.equal(typeof ui.start, 'function', 'browser lifecycle must be exported for testing');
    await ui.start(window, fetcher);
    assert.equal(nodes.get('overall').dataset.state, 'reachable');
    // Simulate suspended timers: advance wall time without running scheduled callbacks.
    t.mock.timers.setTime(Date.now() + 60000);
    if (event === 'visibilitychange') {
      document.visibilityState = 'hidden';
      document.dispatchEvent(new Event(event));
      assert.equal(calls, 1);
      document.visibilityState = 'visible';
    }
    (event === 'pageshow' ? window : document).dispatchEvent(new Event(event));
    assert.equal(nodes.get('overall').dataset.state, 'unknown');
    assert.equal(nodes.get('edge-status').dataset.state, 'unknown');
    assert.equal(calls, 2);
    await new Promise(setImmediate);
    assert.equal(nodes.get('overall').dataset.state, 'reachable');
  });
}

test('exported lifecycle schedules polling and request timeouts with fake timers', async t => {
  const {nodes, ui, window} = harness();
  let calls = 0, signal;
  assert.equal(typeof ui.start, 'function', 'browser scheduling must be exported for testing');
  await ui.start(window, async (_, options) => {
    calls++;
    signal = options.signal;
    if (calls > 1) return new Promise(() => {});
    return {ok: true, json: async () => snapshot()};
  });
  t.mock.timers.tick(9999);
  assert.equal(calls, 1);
  t.mock.timers.tick(1);
  assert.equal(calls, 2);
  assert.equal(nodes.get('overall').dataset.state, 'unknown');
  t.mock.timers.tick(6000);
  await new Promise(setImmediate);
  assert.equal(signal.aborted, true);
  assert.equal(nodes.get('refresh').disabled, false);
  assert.equal(nodes.get('overall').dataset.state, 'unknown');
});

test('concurrent refresh calls do not overlap', async () => {
  const {ui} = harness();
  let calls = 0, release;
  const waiting = new Promise(resolve => { release = resolve; });
  const fetcher = async () => { calls++; await waiting; return {ok: true, json: async () => snapshot()}; };
  const first = ui.refresh(fetcher);
  await ui.refresh(fetcher);
  release(); await first;
  assert.equal(calls, 1);
});
