/* Bốn nhánh thất bại khi nạp dữ liệu phải NÓI RA, riêng biệt, và không hiện số.
 *
 * VÌ SAO PHÉP KIỂM NÀY TỒN TẠI
 * ----------------------------
 * Trước 17/08/2026, mọi thất bại đều thành `null` rồi `return` im lặng ở ba chỗ
 * (api.js catch, hai lệnh return trong napTuBackend). Hệ quả: bốn tình huống rất
 * khác nhau trông y hệt nhau trên màn hình — dashboard giữ nguyên số cũ và chỉ
 * ghi một dòng console.warn.
 *
 * Đã đo lúc đó: ba thẻ to nhất (request · token · tiền) trùng khớp giữa trạng
 * thái "backend chạy" và "backend chết", nên mắt không bắt được gì.
 *
 * Phép kiểm này không cần backend: nó thay `fetch` bằng bản giả, nên chạy được
 * ở mọi nơi và không phụ thuộc dữ liệu.
 */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "web", "index.html"), "utf8");

/* Danh sách id lấy từ CHÍNH index.html: thiếu id nào là lỗi thật của mã nguồn,
   không phải thiếu sót của bộ kiểm. */
const ids = [...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]);

function makeEl(id) {
  return {
    id, value: "", innerHTML: "", textContent: "", className: "", hidden: false,
    children: [], dataset: {}, style: {}, checked: false, disabled: false,
    classList: {
      _s: new Set(),
      add(c) { this._s.add(c); }, remove(c) { this._s.delete(c); },
      toggle(c, on) {
        if (on === undefined) { this._s.has(c) ? this._s.delete(c) : this._s.add(c); }
        else if (on) this._s.add(c); else this._s.delete(c);
      },
      contains(c) { return this._s.has(c); }
    },
    appendChild(c) { this.children.push(c); return c; }, removeChild() {},
    setAttribute() {}, removeAttribute() {}, getAttribute() { return null; },
    addEventListener() {}, removeEventListener() {},
    querySelector() { return null; }, querySelectorAll() { return []; },
    focus() {}, blur() {}, click() {}, getContext() { return {}; },
    closest() { return null; }, insertAdjacentHTML() {}, scrollIntoView() {}
  };
}

/* Chạy trọn api.js + app.js với một `fetch` giả, rồi trả về DOM giả để đọc. */
function runDashboard(protocol, fakeFetch) {
  const store = {};
  ids.forEach((i) => { store[i] = makeEl(i); });

  const document = {
    body: makeEl("__body"), documentElement: makeEl("__html"), readyState: "complete",
    getElementById(id) { return store[id] || null; },
    createElement(t) { const e = makeEl("__n"); e.tagName = String(t).toUpperCase(); return e; },
    querySelector() { return null; }, querySelectorAll() { return []; },
    addEventListener() {}, removeEventListener() {},
    createDocumentFragment() { return makeEl("__f"); }
  };
  const localStorage = {
    _d: {}, getItem(k) { return Object.prototype.hasOwnProperty.call(this._d, k) ? this._d[k] : null; },
    setItem(k, v) { this._d[k] = String(v); }, removeItem(k) { delete this._d[k]; }, clear() { this._d = {}; }
  };
  function Chart() { this.destroy = () => {}; this.update = () => {}; }
  Chart.defaults = { color: "", borderColor: "", font: {}, plugins: { legend: { labels: {} } }, maintainAspectRatio: true };

  const window = {
    location: { search: "", protocol, href: protocol + "//127.0.0.1:8080/" },
    localStorage, document, Chart,
    addEventListener() {}, removeEventListener() {},
    matchMedia() { return { matches: false, addEventListener() {} }; },
    getComputedStyle() { return {}; }, devicePixelRatio: 1
  };
  window.window = window;

  const sandbox = {
    window, document, localStorage, Chart, fetch: fakeFetch, URLSearchParams,
    // Im lặng: bài kiểm này soát DOM chứ không soát console.
    console: { log() {}, warn() {}, error() {} },
    setTimeout, clearTimeout, setInterval, clearInterval, Promise, Math, Date, JSON,
    requestAnimationFrame: (f) => setTimeout(f, 0), navigator: { userAgent: "node" },
    URL, TextEncoder, Blob: function () {}, alert: () => {}
  };
  sandbox.globalThis = sandbox;
  sandbox.self = sandbox;

  for (const f of ["web/js/api.js", "web/js/app.js"]) {
    vm.runInNewContext(fs.readFileSync(path.join(ROOT, f), "utf8"), sandbox, { filename: f });
  }
  // init() chạy ngay vì readyState = "complete"; đợi promise của napTuBackend.
  return new Promise((res) => setTimeout(() => res(store), 800));
}

const jsonOk = (body) => ({ ok: true, status: 200, json: () => Promise.resolve(body) });

const SCENARIOS = {
  // fetch chỉ reject khi KHÔNG tới được máy chủ
  unreachable: () => Promise.reject(new TypeError("Failed to fetch")),
  // health trả lời bình thường, /api/usage trả 500
  endpointError: (u) => Promise.resolve(
    String(u).includes("/api/usage?")
      ? { ok: false, status: 500, json: () => Promise.resolve({}) }
      : jsonOk(String(u).includes("/api/health")
          ? { ranges: { usage: { from: "2026-01-01", to: "2026-08-13", rows: 1 } }, warnings: [] }
          : { rows: [] })),
  // nối được, nhưng health không báo khoảng ngày nào cho usage
  emptyDatabase: () => Promise.resolve(jsonOk({ ranges: { usage: {} }, warnings: [] }))
};

/* Bốn kịch bản: tên · protocol · fetch giả */
const CASES = [
  ["backend không tới được", "http:", SCENARIOS.unreachable],
  ["một endpoint trả HTTP 500", "http:", SCENARIOS.endpointError],
  ["database chưa có dữ liệu usage", "http:", SCENARIOS.emptyDatabase],
  ["mở bằng file://", "file:", SCENARIOS.unreachable]
];

function textOf(el) {
  if (!el) return "";
  return String(el.textContent || el.innerHTML || "");
}

for (const [name, protocol, fakeFetch] of CASES) {
  test(`nạp hỏng (${name}): báo lên màn hình, không hiện số nào`, async () => {
    const store = await runDashboard(protocol, fakeFetch);

    const note = store["load-note"];
    assert.ok(note, "index.html phải có #load-note để hiện trạng thái nạp");
    assert.equal(note.hidden, false, "dải thông báo phải hiện khi nạp hỏng");
    assert.match(note.className, /\berror\b/, "dải phải ở mức 'error'");

    const message = String((store["load-note-text"] || {}).innerHTML || "");
    assert.ok(message.length > 40, `thông báo quá ngắn: ${JSON.stringify(message)}`);

    assert.equal(textOf(store["conn-text"]), "Không có dữ liệu",
      "chỉ báo kết nối phải nói không có dữ liệu");

    // Điều quan trọng nhất: KHÔNG con số nào được hiện ra.
    assert.equal(textOf(store["status-period"]), "—", "kỳ dữ liệu phải là '—'");
    assert.equal(textOf(store["header-data-date"]), "—", "ngày dữ liệu phải là '—'");
  });
}

test("bốn nhánh nói bốn điều KHÁC nhau", async () => {
  const messages = [];
  for (const [, protocol, fakeFetch] of CASES) {
    const store = await runDashboard(protocol, fakeFetch);
    messages.push(String((store["load-note-text"] || {}).innerHTML || "").slice(0, 120));
  }
  assert.equal(new Set(messages).size, CASES.length,
    "hai nhánh trở lên đang nói giống nhau — quay về đúng chỗ cũ:\n" + messages.join("\n---\n"));
});

test("giao diện không còn khẳng định trạng thái gán cứng", () => {
  /* "Gateway hoạt động" và "lần cuối 2 phút trước" từng là chữ TĨNH trong
     index.html: không có gateway nào tồn tại, và "2 phút" là hằng số nên dữ liệu
     cũ bao lâu nó cũng nói vậy. */
  const visible = html.replace(/<!--[\s\S]*?-->/g, "");   // bỏ comment
  for (const claim of ["Gateway hoạt động", "lần cuối 2 phút", "Cập nhật realtime"]) {
    assert.ok(!visible.includes(claim),
      `index.html vẫn còn khẳng định gán cứng: ${JSON.stringify(claim)}`);
  }
});

test("frontend không còn chứa dữ liệu số liệu nhúng", () => {
  const appJs = fs.readFileSync(path.join(ROOT, "web", "js", "app.js"), "utf8");
  for (const ident of ["SEED_DAYS", "buildJuneExcelWeeks", "basePricing", "RALLI_USERS"]) {
    const declared = new RegExp("^(var|function)\\s+" + ident + "\\b", "m").test(appJs);
    assert.ok(!declared, `${ident} vẫn được khai báo trong app.js`);
  }
  assert.ok(!fs.existsSync(path.join(ROOT, "web", "js", "fallback")),
    "web/js/fallback/ phải đã bị xoá");
  assert.ok(!fs.existsSync(path.join(ROOT, "web", "js", "app.js.bak")),
    "web/js/app.js.bak phải đã bị xoá");
});
