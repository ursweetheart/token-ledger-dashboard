/* Lớp gọi API hạn mức — ĐƯỜNG GHI DUY NHẤT của cả frontend.
 *
 * VÌ SAO PHÉP KIỂM NÀY TỒN TẠI
 * ----------------------------
 * Ngày 17/08/2026 dự án đã xoá một panel nhập tay vì nó là cái bẫy: người dùng
 * gõ số, bấm Lưu, số HIỆN LÊN và cộng vào tổng — rồi tải lại trang là mất sạch.
 * Ghi chú xoá nó còn nằm nguyên trong index.html.
 *
 * Tab Setting là lần đầu dự án có một ô nhập thật sự ghi được. Nên ba điều dưới
 * đây phải được khoá lại:
 *
 *   1. lưu hỏng phải trả `ok:false` KÈM LÝ DO, không lặng lẽ coi như xong
 *   2. lý do phải là câu của máy chủ ("must not be negative"), không phải một
 *      câu chung chung mà người đọc không sửa được gì
 *   3. khoá phải đi trong header, tên khoá agent phải được mã hoá vào URL
 *
 * Chạy api.js trong một hộp cát với `fetch` giả: không cần backend, không cần
 * trình duyệt.
 */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const apiSrc = fs.readFileSync(path.join(ROOT, "web", "js", "api.js"), "utf8");

/* Dựng `TokenLedgerAPI` với một `fetch` ghi lại mọi lượt gọi. */
function makeApi(reply) {
  const calls = [];
  const store = { "tokenledger.key:": "khoa-gia-cho-phep-kiem" };
  const localStorage = {
    getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
    setItem(k, v) { store[k] = String(v); },
    removeItem(k) { delete store[k]; }
  };
  const window = {
    location: { search: "", protocol: "http:", href: "http://127.0.0.1:8080/" },
    localStorage,
    fetch(url, opts) {
      calls.push({ url, opts: opts || {} });
      return Promise.resolve(reply(url, opts || {}));
    }
  };
  window.window = window;
  const sandbox = {
    window, localStorage, console,
    fetch: window.fetch, URLSearchParams, JSON, Promise, encodeURIComponent
  };
  vm.createContext(sandbox);
  vm.runInContext(apiSrc, sandbox, { filename: "api.js" });
  return { api: window.TokenLedgerAPI, calls };
}

const okReply = (body) => () => ({
  ok: true, status: 200, json: () => Promise.resolve(body)
});
const errReply = (status, detail) => () => ({
  ok: false, status, json: () => Promise.resolve({ detail })
});

test("doc han muc goi dung endpoint bang GET", async () => {
  const { api, calls } = makeApi(okReply({ count: 0, rows: [] }));
  const res = await api.quotaList();
  assert.equal(res.ok, true);
  assert.match(calls[0].url, /\/api\/quota$/);
  assert.notEqual(calls[0].opts.method, "POST");
});

test("dat han muc gui POST kem so tien trong than yeu cau", async () => {
  const { api, calls } = makeApi(okReply({ quota_usd: 50 }));
  const res = await api.quotaSet("ralli-tagged", "50");
  assert.equal(res.ok, true);
  assert.equal(calls[0].opts.method, "POST");
  assert.match(calls[0].url, /key_alias=ralli-tagged/);
  assert.deepEqual(JSON.parse(calls[0].opts.body), { quota_usd: "50" });
});

test("nap them goi endpoint khac han voi dat han muc", async () => {
  const { api, calls } = makeApi(okReply({ quota_usd: 80 }));
  await api.quotaTopUp("ralli-tagged", "30");
  assert.match(calls[0].url, /\/api\/quota\/top-up\?/);
});

test("ten khoa duoc ma hoa vao URL", async () => {
  const { api, calls } = makeApi(okReply({}));
  await api.quotaSet("ten co dau cach & dau", "1");
  assert.doesNotMatch(calls[0].url.split("key_alias=")[1], /[ &]/);
});

test("khoa di trong header, khong di trong URL", async () => {
  const { api, calls } = makeApi(okReply({}));
  await api.quotaSet("x", "1");
  assert.equal(calls[0].opts.headers["Authorization"], "Bearer khoa-gia-cho-phep-kiem");
  assert.doesNotMatch(calls[0].url, /khoa-gia-cho-phep-kiem/);
});

test("luu hong tra ve ok:false kem LY DO cua may chu", async () => {
  const { api } = makeApi(errReply(400, "'quota_usd' must not be negative, got -5.0"));
  const res = await api.quotaSet("x", "-5");
  assert.equal(res.ok, false);
  /* Câu của máy chủ nói được VÌ SAO. Một câu "lưu không được" chung chung thì
     người dùng không sửa được gì. */
  assert.match(res.message, /must not be negative/);
});

test("gateway hong tra ve ok:false, khong nem", async () => {
  const { api } = makeApi(errReply(502, "Gateway tra HTTP 403."));
  const res = await api.quotaSet("x", "1");
  assert.equal(res.ok, false);
  assert.match(res.message, /403/);
});

test("khong toi duoc backend cung tra ve ok:false", async () => {
  const { api } = makeApi(() => { throw new Error("mang chet"); });
  let res;
  try {
    res = await api.quotaSet("x", "1");
  } catch (e) {
    assert.fail("quotaSet nem loi - phia goi se khong phan biet duoc that bai");
  }
  assert.equal(res.ok, false);
});

test("than tra loi khong phai JSON van cho ra mot thong bao", async () => {
  const { api } = makeApi(() => ({
    ok: false, status: 500, json: () => Promise.reject(new Error("khong phai json"))
  }));
  const res = await api.quotaSet("x", "1");
  assert.equal(res.ok, false);
  assert.ok(res.message, "phai co thong bao de hien ra man hinh");
});
