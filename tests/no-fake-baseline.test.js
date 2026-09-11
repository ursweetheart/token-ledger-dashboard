"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const appSource = fs.readFileSync(path.join(__dirname, "..", "web", "js", "app.js"), "utf8");

/* Baseline giả từng tồn tại: kỳ gốc được dựng bằng hệ số (0,88 / 0,57) khi không
   có số thật, và delta vẽ ra một mũi tên trông y hệt số đo. Các phép kiểm dưới
   đây khoá cả ba đường quay lại: hàm không nhận hệ số, không ai truyền hệ số,
   và không định danh nào chứa "mock" sống trong mã chạy. */

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/[^\n]*/g, "");
}

function loadBaseline() {
  const src = appSource.match(/function deltaBaseline\([\s\S]*?\n\}/);
  assert.ok(src, "deltaBaseline phải tồn tại");
  const sandbox = { console };
  vm.createContext(sandbox);
  vm.runInContext(src[0], sandbox);
  return sandbox.deltaBaseline;
}

/* Hợp đồng đổi ở ô 1.3 của `standardize-kpi-card-insights`: trước đây cả hai
   trạng thái "không có kỳ so sánh" và "kỳ trước đo được 0" đều bị ép về `v = 0`,
   nên một phép đo thật hiện lên màn hình thành "chưa có dữ liệu". Nay `has` mới
   là thứ tách hai trạng thái đó, nên phải kiểm `has` chứ không chỉ kiểm `v`. */
test("không có kỳ gốc thật thì has=false, không dựng bằng hệ số", () => {
  const deltaBaseline = loadBaseline();
  /* `{ ...x }` chứ không so thẳng: object do `vm.runInContext` dựng mang
     `Object.prototype` của sandbox, nên `deepStrictEqual` báo "same structure
     but are not reference-equal" dù nội dung khớp. Trải phẳng về realm này. */
  for (const khong_co of [null, undefined, -5]) {
    assert.deepEqual({ ...deltaBaseline(khong_co) }, { v: null, has: false });
  }
});

test("kỳ gốc đo được 0 KHÁC HẲN không có kỳ gốc", () => {
  assert.deepEqual({ ...loadBaseline()(0) }, { v: 0, has: true });
});

test("có kỳ gốc thật thì dùng nguyên giá trị đó", () => {
  const deltaBaseline = loadBaseline();
  assert.equal(deltaBaseline(42).v, 42);
});

test("hàm KHÔNG nhận thêm tham số hệ số nào", () => {
  // Nhận thêm tham số nghĩa là có sẵn chỗ để nhét hệ số vào lại.
  assert.equal(loadBaseline().length, 1, "deltaBaseline chỉ được nhận đúng 1 tham số");
});

test("không lời gọi renderDelta nào truyền hệ số baseline", () => {
  const calls = appSource.match(/renderDelta\([^;]*?\);/g) || [];
  assert.ok(calls.length > 0, "phải có ít nhất một lời gọi renderDelta");
  calls.forEach((call) => {
    // renderDelta(id, cur, prev, same, betterUp, fmtFn) = 6 tham số.
    const args = call.replace(/^renderDelta\(|\);$/g, "").split(",");
    assert.ok(args.length <= 6, `lời gọi thừa tham số, nghi là hệ số baseline: ${call}`);
  });
});

test("không định danh nào chứa `mock` sống trong mã chạy", () => {
  // KHÔNG dùng \bmock\b: nó bỏ sót đúng thứ cần bắt, vì `mockFactor` có ký tự
  // từ ngay sau "mock". Bản đầu của phép kiểm này mắc lỗi đó và vẫn xanh.
  const hit = stripComments(appSource).match(/mock/gi) || [];
  assert.deepEqual(hit, [], "không định danh nào chứa `mock` được sống trong mã chạy");
});

test("chính phép kiểm trên bắt được khi hệ số quay lại", () => {
  // Kiểm ngược: thêm lại `mockFactor` thì phép kiểm phải ĐỎ, không được im.
  const taiPham = "function deltaBaseline(realBase, mockFactor){ return {v:realBase||mockFactor}; }";
  assert.ok((stripComments(taiPham).match(/mock/gi) || []).length > 0,
    "phép kiểm phải bắt được `mockFactor`");
});
