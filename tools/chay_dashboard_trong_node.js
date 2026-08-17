/* Chay web/js/app.js trong Node voi DOM gia, noi vao backend THAT.
 *
 * CAN: docker compose up -d  +  uvicorn dang chay o 127.0.0.1:8000
 *
 * Vi sao o tools/ chu khong o tests/: no phu thuoc backend va du lieu that, nen
 * khong the "luon xanh". Phep kiem khong can backend nam o
 * tests/load-failure-states.test.js.
 *
 *     node tools/chay_dashboard_trong_node.js
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = "D:/RangDonk/token-ledger-dashboard";
const html = fs.readFileSync(path.join(ROOT, "web/index.html"), "utf8");

// --- moi id co that trong index.html --------------------------------------
const ids = [...html.matchAll(/id="([^"]+)"/g)].map(m => m[1]);
const classes = new Set([...html.matchAll(/class="([^"]+)"/g)]
  .flatMap(m => m[1].split(/\s+/)).filter(Boolean));

function makeEl(id) {
  const el = {
    id, value: "", innerHTML: "", textContent: "", className: "", hidden: false,
    children: [], dataset: {}, style: {}, checked: false, disabled: false,
    onclick: null, onchange: null, oninput: null,
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) { if (on === undefined) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); } else if (on) this._s.add(c); else this._s.delete(c); },
      contains(c) { return this._s.has(c); }
    },
    appendChild(c) { this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter(x => x !== c); },
    setAttribute() {}, removeAttribute() {}, getAttribute() { return null; },
    addEventListener() {}, removeEventListener() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    focus() {}, blur() {}, click() {},
    getContext() { return {}; },
    closest() { return null; },
    insertAdjacentHTML() {},
    scrollIntoView() {}
  };
  return el;
}

const store = {};
ids.forEach(i => { store[i] = makeEl(i); });

const document = {
  body: makeEl("__body"),
  documentElement: makeEl("__html"),
  readyState: "complete",
  getElementById(id) { return store[id] || null; },
  createElement(tag) { const e = makeEl("__new_" + tag); e.tagName = String(tag).toUpperCase(); return e; },
  querySelector() { return null; },
  querySelectorAll(sel) {
    // .tab duoc init() dung de gan onclick — tra ve mang rong la du
    return [];
  },
  addEventListener() {}, removeEventListener() {},
  createDocumentFragment() { return makeEl("__frag"); }
};

const localStorage = {
  _d: {},
  getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
  setItem(k, v) { this._d[k] = String(v); },
  removeItem(k) { delete this._d[k]; },
  clear() { this._d = {}; }
};

// Chart gia: app.js chi doc Chart.defaults va goi new Chart(...)
function Chart() { this.destroy = () => {}; this.update = () => {}; this.data = {}; }
Chart.defaults = { color: "", borderColor: "", font: {}, plugins: { legend: { labels: {} } }, maintainAspectRatio: true };

const loi = [];
const window = {
  location: { search: "", protocol: "http:", href: "http://127.0.0.1:8080/" },
  localStorage, document, Chart,
  addEventListener() {}, removeEventListener() {},
  matchMedia() { return { matches: false, addEventListener() {} }; },
  getComputedStyle() { return {}; },
  devicePixelRatio: 1
};
window.window = window;

const sandbox = {
  window, document, localStorage, Chart, fetch, URLSearchParams, console,
  setTimeout, clearTimeout, setInterval, clearInterval, Promise, Math, Date, JSON,
  requestAnimationFrame: (f) => setTimeout(f, 0),
  navigator: { userAgent: "node" },
  URL, TextEncoder, Blob: function () {}, alert: () => {}
};
sandbox.globalThis = sandbox;
sandbox.self = sandbox;

function run(file) {
  const src = fs.readFileSync(path.join(ROOT, file), "utf8");
  vm.runInNewContext(src, sandbox, { filename: file });
}

console.log("=".repeat(72));
console.log(`DOM gia: ${ids.length} id, ${classes.size} class doc tu index.html`);
console.log("=".repeat(72));

let ok = true;
for (const f of ["web/js/fallback/ralli-users.js", "web/js/api.js", "web/js/app.js"]) {
  if (!fs.existsSync(path.join(ROOT, f))) { console.log(`  bo qua (khong co): ${f}`); continue; }
  try { run(f); console.log(`  nap OK: ${f}`); }
  catch (e) {
    ok = false;
    console.log(`  NEM LOI khi nap ${f}:`);
    console.log(`    ${e.constructor.name}: ${e.message}`);
    console.log((e.stack || "").split("\n").slice(1, 6).map(l => "    " + l.trim()).join("\n"));
    break;
  }
}

if (!ok) process.exit(1);

// init() da chay khi nap app.js (readyState = "complete"). Doi promise cua
// napTuBackend roi doc DOM gia.
setTimeout(() => {
  console.log();
  console.log("=".repeat(72));
  console.log("TRANG THAI DOM GIA SAU KHI init() + napTuBackend() CHAY");
  console.log("=".repeat(72));
  const g = (id) => store[id];
  const show = (id, ...props) => {
    const e = g(id);
    if (!e) { console.log(`  ${id.padEnd(22)} KHONG CO PHAN TU NAY`); return; }
    console.log(`  ${id.padEnd(22)} ` + props.map(p => `${p}=${JSON.stringify(e[p])}`).join("  "));
  };
  show("load-note", "hidden", "className");
  show("load-note-icon", "textContent");
  show("load-note-text", "innerHTML");
  show("conn-dot", "className");
  show("conn-text", "textContent");
  show("freshness-wrap", "hidden");
  show("freshness-text", "textContent");
  show("status-period", "innerHTML");
  show("header-data-date", "innerHTML");
  console.log();
  console.log("  __probe    :", sandbox.window.__probe || "(khong co moc nao chay)");
  console.log("  __probeErr :", sandbox.window.__probeErr || "(khong loi)");
}, 4000);
