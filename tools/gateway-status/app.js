'use strict';

function createMonitorUI(document, {timers = globalThis, now = Date.now} = {}) {
  const ids = ['lb', 'proxy1', 'proxy2', 'route'];
  const scope = 'Liveness checks only. Provider access, credentials, database and Redis readiness are not verified.';
  const el = id => document.getElementById(id);
  let busy = false;
  let expiry;
  function unknown(message) {
    timers.clearTimeout(expiry);
    el('overall').textContent = 'Status unknown';
    el('overall').dataset.state = 'unknown';
    el('summary').textContent = message;
    el('checked').textContent = 'No current measurement';
    for (const id of ids) {
      el(`${id}-status`).textContent = 'Unknown';
      el(`${id}-status`).dataset.state = 'unknown';
      el(`${id}-detail`).textContent = 'Waiting for a fresh check.';
      el(`${id}-latency`).textContent = '—';
    }
  }
  async function refresh(fetcher = fetch) {
    if (busy) return;
    busy = true;
    el('refresh').disabled = true;
    el('scope').textContent = scope;
    unknown('Checking gateway components…');
    const controller = new AbortController();
    let timer;
    try {
      const data = await Promise.race([
        (async () => {
          const response = await fetcher('/api/status', {cache: 'no-store', signal: controller.signal});
          if (!response.ok) throw new Error('Monitor unavailable');
          return response.json();
        })(),
        new Promise((_, reject) => { timer = timers.setTimeout(() => {
          controller.abort();
          reject(new Error('Monitor timeout'));
        }, 6000); })
      ]);
      const age = now() - Date.parse(data.checked_at);
      if (!['reachable', 'degraded', 'unavailable'].includes(data.status) || !Number.isFinite(age) || age >= 30000 || age < -30000 ||
          !Array.isArray(data.components) || data.components.length !== ids.length ||
          !ids.every(id => data.components.filter(c => c && c.id === id).length === 1) ||
          !data.components.every(c => ['reachable', 'unreachable'].includes(c.status) && typeof c.detail === 'string' && c.detail.length <= 500 && Number.isFinite(c.latency_ms) && c.latency_ms >= 0)) {
        throw new Error('Invalid or stale snapshot');
      }
      const components = Object.fromEntries(data.components.map(c => [c.id, c]));
      const up = id => components[id].status === 'reachable';
      const computed = ids.every(up) ? 'reachable' : up('lb') && up('route') && (up('proxy1') || up('proxy2')) ? 'degraded' : 'unavailable';
      if (computed !== data.status) throw new Error('Inconsistent snapshot');
      el('overall').textContent = {reachable: 'Gateway reachable', degraded: 'Gateway degraded', unavailable: 'Gateway unavailable'}[data.status];
      el('overall').dataset.state = data.status;
      el('summary').textContent = {
        reachable: 'All component liveness checks passed. This is not an inference test.',
        degraded: 'The load-balancer liveness route responds, but one proxy is unavailable.',
        unavailable: 'One or more required checks failed. Review the observations below.'
      }[data.status];
      el('checked').textContent = `Last checked: ${new Date(data.checked_at).toLocaleString('en-GB')}`;
      for (const c of data.components) {
        el(`${c.id}-status`).textContent = c.status === 'reachable' ? 'Reachable' : 'Unreachable';
        el(`${c.id}-status`).dataset.state = c.status;
        el(`${c.id}-detail`).textContent = c.detail;
        el(`${c.id}-latency`).textContent = `${Math.round(c.latency_ms)} ms`;
      }
      expiry = timers.setTimeout(() => unknown('The last measurement expired. Waiting for a fresh check.'), 30000 - Math.max(0, age));
    } catch {
      unknown('The status monitor could not provide a fresh result. Gateway state is unknown; check the monitor service and your connection.');
    } finally {
      timers.clearTimeout(timer);
      busy = false;
      el('refresh').disabled = false;
    }
  }
  function start(window, fetcher = fetch) {
    const update = () => refresh(fetcher);
    const restore = () => {
      unknown('Checking gateway components…');
      return update();
    };
    el('refresh').addEventListener('click', update);
    window.addEventListener('pageshow', restore);
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') restore();
    });
    timers.setInterval(update, 10000);
    return update();
  }
  return {refresh, start};
}

if (typeof module !== 'undefined') module.exports = {createMonitorUI};
if (typeof window !== 'undefined') createMonitorUI(document).start(window);
