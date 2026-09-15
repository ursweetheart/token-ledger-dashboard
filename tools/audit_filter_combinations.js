/* Soat TO HOP BO LOC cua dashboard (muc 8.4 + 8.5 cua change
 * revise-dashboard-ui-after-2026-07-25-review).
 *
 * VI SAO CAN MOT CONG CU RIENG
 * ----------------------------
 * Hai muc do doi "kiem thu bo loc ket hop" va "kiem thu du lieu thieu userId /
 * thieu budget / cay mot cap / du lieu rong". Lam bang mat tren trinh duyet thi
 * moi lan chi thay MOT to hop, va cai hong hay gap nhat khong phai bo cuc vo -
 * la mot o hien `NaN`, `undefined` hay `Infinity` giua bang so.
 *
 * KHONG DUNG PHEP QUET CHUOI LAM PHEP KIEM CHINH. Ban dau file nay quet DOM
 * tim "NaN"/"undefined"/"Infinity". Da kiem nguoc 08/09: chen mot NaN CO Y vao
 * `ov-cost-total` roi chay lai -> cong cu VAN BAO SACH. Ly do la mot phat hien
 * that ve chinh dashboard:
 *
 *     num(v) = isNaN(Number(v)) ? 0 : Number(v)      <- 126 cho goi
 *     fmt(n) = Math.round(num(n)).toLocaleString()
 *
 * NaN bi doi thanh 0 o TANG DINH DANG, nen mot phep tinh hong khong hien ra
 * chu "NaN" - no hien ra so 0, trong hop ly. Quet chuoi khong bao gio bat duoc.
 *
 * Nen phep kiem chinh la BAT BIEN SO HOC: moi dong co dung MOT agent, nen cong
 * tong cua tung agent phai bang tong khong loc. Bo loc hong theo bat ky kieu
 * nao - bo sot dong, dem trung, tra nham tap - deu lam dang thuc nay gay.
 * Phep quet chuoi van giu, nhung chi la loi phu.
 *
 *     set DASHBOARD_KEY=<khoa cua may chu>
 *     node tools/soat_to_hop_bo_loc.js
 *
 * CAN backend that dang chay (postgres + api o 127.0.0.1:8000), giong
 * tools/chay_dashboard_trong_node.js. Vi vay no nam o tools/ chu khong o tests/:
 * no khong the "luon xanh".
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
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

// Chay TRONG IIFE cua app.js. Xem "BAY KHI CHEN PHEP DO" trong
// tools/chay_dashboard_trong_node.js: noi code SAU `})();` thi khong thay bien nao.
const PROBE = `
window.__ketQua = null;
(function cho(conLai){
  try {
    if (!(REAL_ACCOUNTS || []).length) {
      if (conLai <= 0) { window.__ketQua = { loi: "het gio cho du lieu" }; return; }
      setTimeout(function(){ cho(conLai - 1); }, 200);
      return;
    }
  } catch (e) { window.__ketQua = { loi: e.message }; return; }

  var rowsGoc = allDayRows();
  var giaTri = {
    dept:     distinct(buildDepartmentFilterOptions(rowsGoc)).slice(0, 6),
    agent:    distinct(rowsGoc.map(function(r){ return r.a; }).filter(Boolean)).slice(0, 6),
    provider: distinct(rowsGoc.map(function(r){ return modelProvider(r.m); }).filter(Boolean)),
    model:    Object.keys(state.pricing).slice(0, 4),
    user:     distinct(USER_ACCOUNTS.map(userFilterLabel).filter(Boolean)).slice(0, 5)
  };

  var toHop = [];
  // Tung bo loc mot minh, het moi gia tri.
  Object.keys(giaTri).forEach(function(k){
    giaTri[k].forEach(function(v){ var f = {}; f[k] = v; toHop.push(f); });
  });
  // Cap doi: phong ban x agent, va user x agent - hai cap hay lam rong ket qua nhat.
  giaTri.dept.slice(0,3).forEach(function(d){
    giaTri.agent.slice(0,3).forEach(function(a){ toHop.push({ dept: d, agent: a }); });
  });
  giaTri.user.slice(0,3).forEach(function(u){
    giaTri.agent.slice(0,3).forEach(function(a){ toHop.push({ user: u, agent: a }); });
  });
  // Truong hop RONG: to hop khong the co dong nao.
  toHop.push({ dept: "__khong-ton-tai__" });
  toHop.push({ user: "__khong-ai__", agent: giaTri.agent[0] || "" });

  var xau = [];
  var goc = JSON.parse(JSON.stringify(state.filters));
  var gocRange = JSON.parse(JSON.stringify(state.range));

  function datLoc(f){
    state.filters = { dept:"", user:"", provider:"", model:"", agent:"" };
    Object.keys(f || {}).forEach(function(k){ state.filters[k] = f[k]; });
  }

  function quetDom(nhan){
    var co = [];
    for (var id in window.__store) {
      var el = window.__store[id];
      var s = String((el && el.innerHTML) || "") + " " + String((el && el.textContent) || "");
      ["NaN", "undefined", "Infinity", "[object Object]"].forEach(function(dau){
        if (s.indexOf(dau) >= 0) co.push({ id: id, dau: dau, mau: s.slice(Math.max(0, s.indexOf(dau) - 40), s.indexOf(dau) + 40) });
      });
    }
    if (co.length) xau.push({ toHop: nhan, loi: co.slice(0, 4), tong: co.length });
  }

  // ── BAT BIEN: phan hoach theo agent ───────────────────────────────────
  // Moi dong usage co dung MOT agent, nen cong tong tung agent = tong khong loc.
  // Day la phep kiem CHINH; xem ghi chu dau file vi sao quet chuoi khong du.
  datLoc({});
  var tongChung = aggregate(scopedRows());
  var moiAgent = distinct(allDayRows().map(function(r){ return r.a; }).filter(Boolean));
  var congDon = { r:0, tokens:0, cost:0 };
  moiAgent.forEach(function(a){
    datLoc({ agent: a });
    var g = aggregate(scopedRows());
    congDon.r += g.r; congDon.tokens += g.tokens; congDon.cost += g.cost;
  });
  var batBien = [];
  [["r", 0], ["tokens", 0], ["cost", 0.01]].forEach(function(pair){
    var k = pair[0], dungSai = pair[1];
    var lech = Math.abs(congDon[k] - tongChung[k]);
    if (lech > dungSai) batBien.push({ truong: k, tong: tongChung[k], congDon: congDon[k], lech: lech });
  });

  // ── BAT BIEN: moi to hop phai <= tong ────────────────────────────────
  toHop.forEach(function(f){
    datLoc(f);
    var g;
    try { g = aggregate(scopedRows()); renderAll(); }
    catch (e) { xau.push({ toHop: f, nem: e.constructor.name + ": " + e.message }); return; }
    if (g.r > tongChung.r || g.tokens > tongChung.tokens || g.cost > tongChung.cost + 0.01) {
      xau.push({ toHop: f, vuot: { r: g.r + "/" + tongChung.r, tokens: g.tokens + "/" + tongChung.tokens } });
    }
    quetDom(f);
  });

  // 8.5: khoang ngay RONG (khong ngay nao co du lieu)
  state.filters = { dept:"", user:"", provider:"", model:"", agent:"" };
  state.range = { start: "1999-01-01", end: "1999-01-31" };
  try { renderAll(); quetDom({ __kyRong: "1999-01-01..1999-01-31" }); }
  catch (e) { xau.push({ toHop: { __kyRong: 1 }, nem: e.constructor.name + ": " + e.message }); }

  state.filters = goc; state.range = gocRange;
  window.__ketQua = { soToHop: toHop.length + 1, xau: xau, batBien: batBien,
    soAgent: moiAgent.length, tongChung: { r: tongChung.r, tokens: tongChung.tokens }, giaTri: {
    dept: giaTri.dept.length, agent: giaTri.agent.length, provider: giaTri.provider.length,
    model: giaTri.model.length, user: giaTri.user.length } };
})(75);
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

window.__store = store;

for (const f of ["web/js/fallback/ralli-users.js", "web/js/api.js", "web/js/app.js"]) {
  if (!fs.existsSync(path.join(ROOT, f))) continue;
  try { run(f); }
  catch (e) {
    console.log(`NEM LOI khi nap ${f}: ${e.constructor.name}: ${e.message}`);
    process.exit(1);
  }
}

setTimeout(() => {
  const kq = window.__ketQua;
  console.log("=".repeat(72));
  if (!kq) { console.log("PROBE khong chay xong trong 20 giay."); process.exit(1); }
  if (kq.loi) { console.log("LOI: " + kq.loi); process.exit(1); }
  console.log(`Da dat ${kq.soToHop} to hop bo loc`);
  console.log(`  gia tri co that: dept=${kq.giaTri.dept} agent=${kq.giaTri.agent} ` +
              `provider=${kq.giaTri.provider} model=${kq.giaTri.model} user=${kq.giaTri.user}`);
  console.log(`  bat bien phan hoach: cong tong ${kq.soAgent} agent vs tong khong loc`);
  if (kq.batBien.length) {
    console.log("  ==> GAY:");
    kq.batBien.forEach(b => console.log(`      ${b.truong}: tong=${b.tong} congDon=${b.congDon} lech=${b.lech}`));
  } else {
    console.log("  ==> khop (r, tokens, cost)");
  }
  console.log("=".repeat(72));
  if (!kq.xau.length && !kq.batBien.length) { console.log("SACH: bat bien khop, khong to hop nao nem loi hay vuot tong."); process.exit(0); }
  if (kq.batBien.length && !kq.xau.length) process.exit(1);
  console.log(`CO ${kq.xau.length} TO HOP CO VAN DE:\n`);
  kq.xau.slice(0, 12).forEach(x => {
    console.log("  to hop: " + JSON.stringify(x.toHop));
    if (x.nem) console.log("    NEM: " + x.nem);
    (x.loi || []).forEach(l => console.log(`    [${l.dau}] #${l.id}: …${l.mau.replace(/\s+/g, " ")}…`));
    if (x.tong > 4) console.log(`    … con ${x.tong - 4} o nua`);
    console.log("");
  });
  process.exit(1);
}, 20000);
