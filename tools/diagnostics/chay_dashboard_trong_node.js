/* Chay web/js/app.js trong Node voi DOM gia, noi vao backend THAT.
 *
 * CAN: docker compose up -d  +  uvicorn dang chay o 127.0.0.1:8000
 *
 * Vi sao o tools/ chu khong o tests/: no phu thuoc backend va du lieu that, nen
 * khong the "luon xanh". Phep kiem khong can backend nam o
 * tests/load-failure-states.test.js.
 *
 *     set DASHBOARD_KEY=<khoa cua may chu>
 *     node tools/diagnostics/chay_dashboard_trong_node.js
 *
 * PHAI CO KHOA (tu 21/08/2026)
 * ---------------------------
 * api.js doc khoa tu localStorage theo tung dia chi backend, o ten kho
 * `tokenledger.key:<base>`. localStorage gia cua file nay truoc day RONG, nen
 * load() dung ngay o o nhap khoa va KHONG goi mot endpoint nao - trong khi
 * harness van in "nap OK" va thoat 0. Do ngay 22/08/2026: exit 0, "nap OK" hai
 * lan, nhat ky uvicorn 0 dong GET /api/. Day la cho thu NAM dinh bay do; bon
 * cho kia la bon kich ban trong tests/load-failure-states.test.js.
 *
 * BAY KHI CHEN PHEP DO VAO app.js
 * ------------------------------
 * app.js boc trong mot IIFE: `(function(){ ... })();`. Moi bien cua no la bien
 * RIENG - noi code vao SAU `})();` thi khong thay gi ca, chi nhan
 * ReferenceError. Muon doc REAL_ACCOUNTS / USER_ACCOUNTS thi phai chen vao
 * TRUOC dau dong IIFE, nhu PROBE ben duoi lam.
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..", "..");
const REQUIRED_FILES = ["web/index.html", "web/js/api.js", "web/js/app.js"];

if (process.argv.includes("--check-files")) {
  let missing = false;
  for (const file of REQUIRED_FILES) {
    const resolved = path.join(ROOT, file);
    if (fs.existsSync(resolved)) console.log(`  ok: ${resolved}`);
    else {
      missing = true;
      console.error(`  THIEU: ${resolved}`);
    }
  }
  process.exit(missing ? 1 : 0);
}

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

// Dia chi backend phai KHOP voi DEFAULT_BASE cua api.js, vi ten kho khoa co
// chua dia chi. Sai mot ky tu la api.js coi nhu chua co khoa.
const BASE = process.env.DASHBOARD_BASE || "http://127.0.0.1:8000";
const KHOA = process.env.DASHBOARD_KEY || "";

const localStorage = {
  // Gieo khoa tu bien moi truong, KHONG go cung mot chuoi vao file nay.
  _d: KHOA ? { ["tokenledger.key:" + BASE]: KHOA } : {},
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
  // `?api=` because since 29/08 api.js returns an empty base over http, and
  // Node's fetch cannot resolve relative paths. Switching to protocol "file:"
  // instead hits api.js's own file:// guard.
  location: { search: "?api=" + BASE, protocol: "http:", href: "http://127.0.0.1:8080/" },
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

// Chay TRONG IIFE cua app.js - xem "BAY KHI CHEN PHEP DO" o dau file.
// Ghi ket qua ra window (dung chung voi ben ngoai) chu khong ra bien cuc bo.
// CHO cho toi khi napTuBackend() xong, KHONG chot mot con so giay.
// Ban dau chot luc 3400ms va bang bao cao doc luc 4000ms - chi cach nhau
// 600ms. Backend that co luc cham hon (bo test JS mat 9 giay), va khi do
// harness bao "khong nap duoc" trong khi no chi CHUA XONG. Mot phep kiem hong
// vi ly do sai con te hon la khong co phep kiem.
const PROBE = `
(function cho(conLai){
  try {
    var UA = USER_ACCOUNTS || [];
    if ((REAL_ACCOUNTS || []).length) {
      window.__do = {
        real: REAL_ACCOUNTS.length,
        user: UA.length,
        svc:  UA.filter(function(u){ return String(u.user||"").indexOf("svc.") === 0; }).length,
        hoatDong: UA.filter(function(u){ return u.active && !u.disabled; }).length,
        goc:  (unitChildIndex[""] || []).length,
        auto: (unitChildIndex[""] || []).filter(function(u){ return u && u.auto; }).length
      };
      return;
    }
  } catch (e) { window.__doErr = e.message; window.__doHet = true; return; }
  if (conLai <= 0) { window.__doHet = true; return; }
  setTimeout(function(){ cho(conLai - 1); }, 200);
})(75);   // toi da 15 giay
`;

function run(file) {
  let src = fs.readFileSync(path.join(ROOT, file), "utf8");
  if (file.endsWith("app.js")) {
    const i = src.lastIndexOf("})();");
    if (i < 0) throw new Error("khong tim thay dau dong IIFE cua app.js");
    src = src.slice(0, i) + PROBE + src.slice(i);
  }
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
// Doi PROBE bao xong (hoac het gio) roi moi doc DOM gia. Xem ghi chu o PROBE.
function khiXong(lam, conLai) {
  if (sandbox.window.__do || sandbox.window.__doHet || conLai <= 0) return lam();
  setTimeout(() => khiXong(lam, conLai - 1), 200);
}

khiXong(() => {
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

  // ── So lieu, va THOAT KHAC 0 neu khong nap duoc ────────────────────────
  // Truoc 22/08/2026 file nay thoat 0 ke ca khi khong goi duoc endpoint nao.
  // Mot cong cu kiem ma bao "xong" trong luc khong kiem gi thi te hon la
  // khong co cong cu.
  const d = sandbox.window.__do;
  console.log();
  console.log("=".repeat(72));
  if (d && d.real > 0) {
    console.log(`  REAL_ACCOUNTS ${d.real}  ·  USER_ACCOUNTS ${d.user}`
                + `  ·  dong svc.* ${d.svc}`);
    console.log(`  User hoat dong ${d.hoatDong}/${d.user}`
                + `  ·  don vi goc ${d.goc} (tu tao ${d.auto})`);
    console.log("DASHBOARD NAP DUOC.");
    return;
  }
  // Noi RO ba kha nang, va dung conn-text de chi ra kha nang nao.
  const conn = (store["conn-text"] || {}).textContent || "";
  console.log("  KHONG NAP DUOC DU LIEU.");
  console.log(`  conn-text = ${JSON.stringify(conn)}`);
  if (sandbox.window.__doErr) console.log(`  loi trong probe: ${sandbox.window.__doErr}`);
  console.log("  Ba kha nang:");
  console.log(`    (1) chua dat DASHBOARD_KEY  [tien trinh nay doc duoc:`
              + ` ${KHOA ? "co khoa" : "KHONG CO"}]`);
  console.log(`    (2) may chu chua chay o ${BASE}`);
  console.log("    (3) khoa sai -> may chu tra 401");
  process.exitCode = 1;
}, 100);   // toi da 20 giay, dai hon han PROBE de PROBE luon chot truoc
