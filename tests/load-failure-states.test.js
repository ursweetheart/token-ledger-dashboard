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
/* Key store name is `KEY_PREFIX + base()` (api.js), and since 29/08 `base()`
   depends on the protocol. This must follow the same rule. */
const khoTen = (protocol) =>
  "tokenledger.key:" + (protocol === "file:" ? "http://127.0.0.1:8000" : "");
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

/* Chạy trọn api.js + app.js với một `fetch` giả, rồi trả về DOM giả để đọc.
 *
 * `khoa` là khoá đọc API cất sẵn trong localStorage. MẶC ĐỊNH LÀ CÓ, vì bốn
 * kịch bản hỏng bên dưới nói về chuyện xảy ra SAU khi đã qua cửa khoá. Truyền
 * `null` để dựng lại cảnh "chưa nhập khoá bao giờ".
 *
 * Thêm ngày 21/08/2026 cùng change require-a-key-to-read-the-api. Không có
 * tham số này thì cả bốn kịch bản cũ dừng ở ô nhập khoá và không bao giờ chạm
 * tới nhánh chúng đang kiểm - phép kiểm vẫn "chạy" nhưng đo nhầm thứ khác. */
function runDashboard(protocol, fakeFetch, khoa = "khoa-gia-cho-phep-kiem", search = "") {
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
  /* Tên kho khoá GẮN VỚI ĐỊA CHỈ backend — xem khối KEY_PREFIX trong api.js.
     Harness chạy với location.search rỗng nên base() = DEFAULT_BASE. */
  if (khoa) localStorage.setItem(khoTen(protocol), khoa);
  store.__ls = localStorage;
  function Chart() { this.destroy = () => {}; this.update = () => {}; }
  Chart.defaults = { color: "", borderColor: "", font: {}, plugins: { legend: { labels: {} } }, maintainAspectRatio: true };

  const window = {
    location: { search, protocol, href: protocol + "//127.0.0.1:8080/" },
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

/* ─── Khoá đọc API (change require-a-key-to-read-the-api, 21/08/2026) ───────
   Hai trạng thái này KHÔNG được trộn vào bốn nhánh trên: người mở lần đầu chưa
   làm gì sai, còn khoá sai là một câu chuyện khác hẳn "chưa bật backend". */

test("chưa nhập khoá: hiện ô nhập, và KHÔNG gọi endpoint nào", async () => {
  const goi = [];
  const fetchDem = (u) => {
    goi.push(String(u));
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
  };
  const store = await runDashboard("http:", fetchDem, null);

  assert.equal(store["key-gate"].hidden, false, "phải hiện ô nhập khoá");
  assert.ok(!/\bwrong\b/.test(store["key-gate"].className),
    "chưa nhập khoá lần nào thì KHÔNG được tô như khoá sai");
  assert.equal(store["load-note"].hidden, true,
    "dải nạp dữ liệu phải ẩn — ô nhập khoá là thứ duy nhất nói chuyện lúc này");
  assert.equal(textOf(store["conn-text"]), "Chưa nhập khoá");

  /* Điều quan trọng nhất: KHÔNG một request nào được bắn đi. Cứ gọi rồi ăn 401
     thì mỗi lần mở trang lại thêm một dòng 401 vào log máy chủ, và người dùng
     nhận thông báo "khoá không đúng" cho một khoá họ chưa hề nhập. */
  assert.deepEqual(goi, [], `đã gọi ${goi.length} endpoint khi chưa có khoá: ${goi}`);

  assert.equal(textOf(store["status-period"]), "—");
  assert.equal(textOf(store["header-data-date"]), "—");
});

test("khoá sai: nói RIÊNG là khoá sai, và xoá khoá hỏng đi", async () => {
  const fetch401 = () => Promise.resolve(
    { ok: false, status: 401, json: () => Promise.resolve({}) });
  const store = await runDashboard("http:", fetch401, "khoa-sai");

  assert.equal(store["key-gate"].hidden, false, "phải hiện lại ô nhập khoá");
  assert.match(store["key-gate"].className, /\bwrong\b/,
    "401 phải tô mức lỗi, khác với lần đầu chưa nhập");
  assert.equal(textOf(store["conn-text"]), "Khoá không đúng");
  assert.match(String(store["key-gate-msg"].innerHTML), /401/,
    "phải nói rõ máy chủ trả 401, không nói chung chung");

  /* Khoá hỏng phải bị xoá. Giữ lại thì mỗi lần tải trang là một 401 nữa, và
     người dùng thấy "khoá không đúng" cho thứ họ không vừa nhập. */
  assert.equal(store.__ls.getItem(khoTen("http:")), null,
    "khoá sai vẫn còn trong localStorage");

  assert.equal(textOf(store["status-period"]), "—");
  assert.equal(textOf(store["header-data-date"]), "—");
});

test("khoá của backend này KHÔNG gửi sang backend khác", async () => {
  /* `?api=...` vốn là tính năng có thật để trỏ sang máy khác. Từ lúc trình
     duyệt giữ một bí mật, tham số đó quyết định luôn GỬI BÍ MẬT ĐI ĐÂU: ai gửi
     link `dashboard?api=http://host-la:8000` là lấy được khoá của người bấm.
     Cất khoá theo từng địa chỉ thì địa chỉ lạ đơn giản là không có khoá nào. */
  const goi = [];
  const fetchDem = (u) => {
    goi.push(String(u));
    return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({}) });
  };
  const store = await runDashboard("http:", fetchDem, "khoa-cua-may-nha",
                                   "?api=http://host-la:8000");

  assert.deepEqual(goi, [],
    `khoá đã bị gửi sang địa chỉ lạ: ${goi}`);
  assert.equal(store["key-gate"].hidden, false,
    "địa chỉ lạ phải hỏi khoá mới, không dùng lại khoá của máy nhà");
  assert.equal(store.__ls.getItem(khoTen("http:")), "khoa-cua-may-nha",
    "khoá của máy nhà không được đụng tới");
});

test("khoá không bao giờ đi qua URL", () => {
  const apiJs = fs.readFileSync(path.join(ROOT, "web", "js", "api.js"), "utf8");
  /* api.js đã có sẵn `?api=...` để đổi địa chỉ backend, nên "thêm ?key=... cho
     nhanh" là lối tự nhiên nhất — và nó bỏ khoá vào log truy cập, lịch sử
     trình duyệt và header Referer. Ba chỗ đó không xoá lại được. */
  const code = apiJs.replace(/\/\*[\s\S]*?\*\//g, "").replace(/^\s*\/\/.*$/gm, "");
  for (const dau of ['get("key")', "get('key')", "?key=", "&key="]) {
    assert.ok(!code.includes(dau), `api.js đưa khoá vào URL qua ${JSON.stringify(dau)}`);
  }
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
