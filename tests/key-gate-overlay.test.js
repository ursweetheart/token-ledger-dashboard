/* Cổng khoá phải PHỦ KÍN, và phần còn lại của trang phải được ẩn hẳn.
 *
 * VÌ SAO PHÉP KIỂM NÀY TỒN TẠI
 * ----------------------------
 * Trước 20/09/2026 `.key-gate` là một khối `max-width:640px` nằm trong luồng
 * trang: dashboard vẫn ở đó phía dưới, chỉ là rỗng. Người xem cuộn trúng sẽ
 * tưởng dashboard hỏng chứ không phải mình chưa đăng nhập.
 *
 * Hành vi của cổng khoá (hiện ô nhập, không gọi dữ liệu, 401 thì báo sai khoá)
 * đã có `load-failure-states.test.js` lo. File này chỉ giữ ba thứ mà một lần
 * dọn CSS vô tình rất dễ làm mất, và mất thì không có lỗi nào được ném ra:
 *
 *   1. lớp phủ đúng là lớp phủ (`position:fixed` + `inset:0`)
 *   2. nền ĐẶC, không trong suốt — trong suốt là để lộ bố cục phía sau
 *   3. `body.locked` ẩn mọi thứ ngoài chính cổng khoá, và được bật/tắt đúng lúc
 */
"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const ROOT = path.resolve(__dirname, "..");
const html = fs.readFileSync(path.join(ROOT, "web", "index.html"), "utf8");
const appJs = fs.readFileSync(path.join(ROOT, "web", "js", "app.js"), "utf8");
const apiJs = fs.readFileSync(path.join(ROOT, "web", "js", "api.js"), "utf8");

/* Khối CSS của `.key-gate`, lấy nguyên văn để đọc từng thuộc tính. */
const gateCss = (() => {
  const m = html.match(/\.key-gate\{([\s\S]*?)\}/);
  assert.ok(m, "khong tim thay khoi CSS .key-gate trong index.html");
  return m[1];
})();

test("cong khoa la mot lop phu, khong phai mot khoi trong luong trang", () => {
  assert.match(gateCss, /position:\s*fixed/,
    "thieu position:fixed — cong khoa se tro lai nam trong luong trang");
  assert.match(gateCss, /inset:\s*0/,
    "thieu inset:0 — lop phu khong kin bon canh");
});

test("nen cua cong khoa phai dac", () => {
  const bg = gateCss.match(/background:\s*([^;]+);/);
  assert.ok(bg, "khoi .key-gate khong khai background");
  assert.doesNotMatch(bg[1], /rgba\([^)]*,\s*0?\.\d+\s*\)/,
    "nen trong suot se de lo bo cuc phia sau");
});

test("body.locked an moi thu tru chinh cong khoa", () => {
  assert.match(html, /body\.locked\s*>\s*\*:not\(\.key-gate\)/,
    "thieu luat an phan con lai cua trang");
});

test("mo cong khoa thi bat body.locked, dong thi tat", () => {
  const show = appJs.slice(appJs.indexOf("function showKeyGate"),
                           appJs.indexOf("function hideKeyGate"));
  const hide = appJs.slice(appJs.indexOf("function hideKeyGate"));
  assert.match(show, /classList\.add\(["']locked["']\)/,
    "showKeyGate khong bat body.locked");
  assert.match(hide.slice(0, 400), /classList\.remove\(["']locked["']\)/,
    "hideKeyGate khong tat body.locked — dashboard se trang tron sau khi nhap dung khoa");
});

/* Bỏ chú thích trước khi soi mã. `api.js` CÓ nhắc `?key=` trong chú thích, ngay
   chỗ giải thích vì sao cố ý không đọc nó — soi cả chú thích thì phép kiểm bắt
   nhầm đúng lời cam kết mà nó đang bảo vệ. */
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/(^|[^:])\/\/.*$/gm, "$1");
}

test("khoa khong bao gio doc tu dia chi URL", () => {
  /* Giữ nguyên cam kết đã ghi trong api.js: khoá nằm trong URL là khoá đi vào
     lịch sử trình duyệt và nhật ký máy chủ, những nơi không xoá lại được. */
  const code = stripComments(apiJs);
  assert.doesNotMatch(code, /\.get\(\s*["']key["']\s*\)/,
    "api.js doc khoa tu tham so URL");
  assert.doesNotMatch(code, /[?&]key=/,
    "api.js co dau hieu ghep khoa vao dia chi URL");
});
