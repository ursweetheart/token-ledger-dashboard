const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function harness(answer) {
  function element() { return {textContent: '', children: [], disabled: false,
    appendChild(x) { this.children.push(x); }, replaceChildren() { this.children = []; }}; }
  const nodes = Object.fromEntries(['status', 'rows', 'prev', 'next'].map(x => ['gateway-identities-' + x, element()]));
  const calls = [];
  const window = {TokenLedgerAPI: {async gatewayIdentities(q) { calls.push({...q}); return answer(q); }}};
  vm.runInNewContext(fs.readFileSync('web/js/gateway-identities.js', 'utf8'), {
    window, document: {getElementById(id) { return nodes[id]; }, createElement: element}
  });
  return {nodes, calls, panel: window.GatewayIdentityPanel};
}
const tick = () => new Promise(resolve => setImmediate(resolve));
const dates = {start: '2026-09-01', end: '2026-09-30'};
function data() { return {ok: true, data: {agents: [{agent_id: 9, name: 'Support', user_mode: 'multiple', is_running: false}],
  rows: [{agent: 'Support', external_user_id: '<img onerror=alert(1)>', kind: 'gateway_observed', calls: 2, total_tokens: 30},
         {agent: 'Support', external_user_id: null, kind: 'whole_agent', calls: 1, total_tokens: 10}],
  total: 2, calls: 3, total_tokens: 40}}; }

test('observed/fallback identities use safe text, separate provenance and unknown adoption', async () => {
  const h = harness(data);
  h.panel.render(dates, 'Support'); await tick();
  assert.equal(h.calls.at(-1).agent_id, 9);
  assert.equal(h.calls.at(-1).start, dates.start);
  assert.equal(h.nodes['gateway-identities-rows'].children[0].children[1].textContent, '<img onerror=alert(1)>');
  assert.equal(h.nodes['gateway-identities-rows'].children[1].children[1].textContent, 'Chưa quy được');
  assert.match(h.nodes['gateway-identities-status'].textContent, /3 request · 40 token/);
  assert.match(h.nodes['gateway-identities-status'].textContent, /Chưa có danh bạ/);
  assert.match(h.nodes['gateway-identities-status'].textContent, /ngừng hoạt động/);
});

test('no traffic, failure-only, unavailable API and legacy agent remain distinct', async () => {
  const h = harness(() => { const r = data(); r.data.calls = r.data.total_tokens = 0; return r; });
  h.panel.render(dates, ''); await tick();
  assert.match(h.nodes['gateway-identities-status'].textContent, /Chưa có usage thành công/);
  h.panel.render(dates, 'legacy'); await tick();
  assert.match(h.nodes['gateway-identities-status'].textContent, /chưa được đăng ký/);
  const error = harness(() => ({ok: false, message: 'unavailable'}));
  error.panel.render(dates, ''); await tick();
  assert.match(error.nodes['gateway-identities-status'].textContent, /Không tải được/);
});

test('pagination resets with scope and stale asynchronous results cannot replace new scope', async () => {
  let first;
  const h = harness(q => q.start === dates.start ? new Promise(resolve => { first = resolve; }) : data());
  h.panel.render(dates, '');
  h.panel.render({start: '2026-09-02', end: dates.end}, ''); await tick();
  first({ok: true, data: {agents: [], rows: [], total: 0, calls: 0, total_tokens: 0}}); await tick();
  assert.match(h.nodes['gateway-identities-status'].textContent, /40 token/);
  assert.equal(h.calls.at(-1).offset, 0);
});
