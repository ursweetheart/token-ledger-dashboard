"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const appSource = fs.readFileSync(path.join(__dirname, "..", "web", "js", "app.js"), "utf8");

/* `\n\}` chứ không `\n\}\n`: app.js dùng CRLF, nên sau `}` là `\r\n`. Các test
   khác trong thư mục này đã dùng đúng dạng — bản đầu của file này thì không, và
   nó im lặng không trích được gì. */
function load(rowsTrongPhamVi, userFilter) {
  const helper = appSource.match(/function userFilterLabel\(u\)\{[\s\S]*?\n\}/);
  const gap = appSource.match(/function rowHasUserIdentity\(r\)\{[\s\S]*?\n\}/);
  const scope = appSource.match(/function userScopeGap\(\)\{[\s\S]*?\n\}/);
  assert.ok(helper && gap && scope, "ba hàm phải tồn tại");

  const sandbox = {
    console, String, Boolean, Object,
    state: { filters: { user: userFilter } },
    scopedRows: () => rowsTrongPhamVi,
    aggregate: (rows) => ({
      r: rows.reduce((s, x) => s + (x.r || 0), 0),
      tokens: rows.reduce((s, x) => s + (x.tokens || 0), 0)
    }),
    distinct: (xs) => Array.from(new Set(xs))
  };
  vm.createContext(sandbox);
  vm.runInContext(helper[0] + "\n" + gap[0] + "\n" + scope[0], sandbox);
  return sandbox;
}

test("dòng có nhãn user thật thì được coi là quy được về người", () => {
  const s = load([], "");
  assert.equal(s.rowHasUserIdentity({ a: "DMS", ug: "tuan.tran" }), true);
});

test("nhãn TRÙNG TÊN AGENT không phải là danh tính người", () => {
  const s = load([], "");
  // Đây là agent một-người-dùng: `ug` bị điền bằng chính tên agent.
  assert.equal(s.rowHasUserIdentity({ a: "Sale Agent", ug: "Sale Agent" }), false);
  assert.equal(s.rowHasUserIdentity({ a: "DMS", ug: "" }), false);
});

test("không lọc user thì không cảnh báo gì", () => {
  const s = load([{ a: "X", ug: "", r: 9, tokens: 9 }], "");
  assert.equal(s.userScopeGap(), null);
});

test("lọc user mà mọi dòng đều có danh tính thì cũng không cảnh báo", () => {
  const s = load([{ a: "X", ug: "an", r: 1, tokens: 1 }], "an");
  assert.equal(s.userScopeGap(), null);
});

test("đếm đúng phần bị loại, và liệt kê agent liên quan", () => {
  const s = load([
    { a: "DMS", ug: "an", r: 10, tokens: 100 },
    { a: "Ralli", ug: "Ralli", r: 5, tokens: 50 },   // trùng tên agent
    { a: "Sale", ug: "", r: 2, tokens: 20 }          // rỗng
  ], "an");
  const g = s.userScopeGap();
  assert.equal(g.rows, 2, "hai dòng không quy được về user");
  assert.equal(g.requests, 7);
  assert.equal(g.tokens, 70);
  assert.deepEqual(g.agents, ["Ralli", "Sale"]);
});

test("KHÔNG để sót bộ lọc user sau khi tạm gỡ nó ra", () => {
  // userScopeGap() tạm đặt filters.user="" để đếm; nếu quên trả lại thì mọi
  // renderer chạy sau đó sẽ mất bộ lọc mà không ai báo.
  const s = load([{ a: "X", ug: "", r: 1, tokens: 1 }], "an");
  s.userScopeGap();
  assert.equal(s.state.filters.user, "an", "phải khôi phục bộ lọc");
});

/* ─── Nhãn hiển thị trùng nhau ─── */
/* Đo 08/09 trên database thật: 938 tài khoản `kind='real'` chỉ có 890 nhãn khác
   nhau. 41 nhãn bị trùng, phủ 89 tài khoản; nặng nhất 6 tài khoản một nhãn. Nên
   đây không phải trường hợp lý thuyết. */
function loadCount(accounts) {
  const helper = appSource.match(/function userFilterLabel\(u\)\{[\s\S]*?\n\}/);
  const counter = appSource.match(/function userLabelAccountCount\(label\)\{[\s\S]*?\n\}/);
  assert.ok(helper && counter, "hai hàm phải tồn tại");
  const sandbox = { console, String, Boolean, USER_ACCOUNTS: accounts };
  vm.createContext(sandbox);
  vm.runInContext(helper[0] + "\n" + counter[0], sandbox);
  return sandbox.userLabelAccountCount;
}

test("đếm đúng số tài khoản dùng chung một nhãn", () => {
  const count = loadCount([
    { a: "DMS", ug: "Nguyễn Trang" },
    { a: "Sale", ug: "Nguyễn Trang" },
    { a: "DMS", ug: "Trần B" }
  ]);
  assert.equal(count("Nguyễn Trang"), 2);
  assert.equal(count("Trần B"), 1);
});

test("nhãn rỗng không đếm, và tài khoản không có danh tính cũng không", () => {
  const count = loadCount([
    { a: "Ralli", ug: "Ralli" },
    { a: "DMS", ug: "" }
  ]);
  assert.equal(count(""), 0);
  assert.equal(count("Ralli"), 0, "nhãn trùng tên agent không được tính là một người");
});
