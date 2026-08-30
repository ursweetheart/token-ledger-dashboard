"use strict";

/* Bộ lọc phải làm mới dashboard ở MỌI lần chọn, không chỉ lần đầu.

   Lỗi cũ: fillSelect() gán `el.innerHTML` vô điều kiện, mà renderFilters() chạy
   trong mọi renderAll(), còn renderAll() lại được gọi từ chính onchange của
   select đó. Dựng lại <option> ngay trong lúc trình duyệt đang xử lý sự kiện
   change làm `el.value` bị đồng bộ về theo thuộc tính `selected` vừa dựng, nên
   lần chọn sau không sinh sự kiện change nữa.

   tools/chay_dashboard_trong_node.js KHÔNG bắt được lỗi này: phần tử giả của nó
   có getAttribute() luôn trả null và setAttribute() rỗng, nên nhánh "danh sách
   không đổi thì đừng đụng DOM" không bao giờ chạy. Vì thế phép kiểm ở đây dựng
   phần tử giả riêng, có thuộc tính thật. */

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const SRC = fs.readFileSync(
  path.join(__dirname, "..", "web", "js", "app.js"), "utf8");

function layHam(ten) {
  const dau = SRC.indexOf("function " + ten + "(");
  assert.ok(dau >= 0, "khong tim thay function " + ten);
  const dong = SRC.slice(dau).split("\n").map((l) => l.replace("\r", ""));
  const het = dong.findIndex((l) => l === "}");
  assert.ok(het > 0, "khong tim thay dau dong cua " + ten);
  return dong.slice(0, het + 1).join("\n");
}

/* <select> giả: giữ thuộc tính thật, và mô phỏng đúng luật của trình duyệt là
   gán innerHTML thì `value` bị đặt lại theo cây <option> vừa dựng. Chính luật
   đó là thứ gây ra lỗi cũ, nên phần tử giả phải có nó thì phép kiểm mới có
   nghĩa. */
function taoSelect() {
  return {
    _attrs: {}, _opts: [], _value: "", _html: "", soLanDungLaiDom: 0,

    get innerHTML() { return this._html; },
    set innerHTML(v) {
      this._html = v;
      this.soLanDungLaiDom++;
      this._opts = (v.match(/value="[^"]*"/g) || [])
        .map((x) => x.slice(7, -1).replace(/&quot;/g, '"').replace(/&amp;/g, "&"));
      this._value = this._opts[0] || "";
    },

    get value() { return this._value; },
    set value(v) {
      this._value = this._opts.indexOf(String(v)) >= 0 ? String(v) : "";
    },

    getAttribute(k) {
      return Object.prototype.hasOwnProperty.call(this._attrs, k) ? this._attrs[k] : null;
    },
    setAttribute(k, v) { this._attrs[k] = String(v); }
  };
}

function dungSandbox() {
  const el = taoSelect();
  const sandbox = {
    JSON, String, Object,
    state: {
      filters: { dept: "", user: "", provider: "", model: "", agent: "" },
      matrixExpanded: {}
    },
    soLanRenderAll: 0,
    document: { getElementById: () => el },
    el
  };
  sandbox.renderAll = function () { sandbox.soLanRenderAll++; };
  vm.runInNewContext(
    [layHam("esc"), layHam("escAttr"), layHam("fillSelect")].join("\n"), sandbox);
  return sandbox;
}

test("chon bo loc lan thu hai van lam moi dashboard", () => {
  const s = dungSandbox();
  const opts = ["Trợ lý ảo Ralli", "Trợ Lý Ảo Hợp Đồng", "Tool dịch"];

  s.fillSelect("f-agent", opts, "", "Tất cả agent");
  assert.equal(s.el.soLanDungLaiDom, 1, "lan dau phai dung DOM");

  // Lần chọn thứ nhất.
  s.el.value = "Trợ lý ảo Ralli";
  s.el.onchange.call(s.el);
  assert.equal(s.state.filters.agent, "Trợ lý ảo Ralli");
  assert.equal(s.soLanRenderAll, 1);

  // renderAll() thật sẽ gọi lại renderFilters() -> fillSelect() với cùng danh sách.
  s.fillSelect("f-agent", opts, s.state.filters.agent, "Tất cả agent");
  assert.equal(s.el.soLanDungLaiDom, 1,
               "danh sach khong doi thi KHONG duoc dung lai DOM");
  assert.equal(s.el.value, "Trợ lý ảo Ralli",
               "lua chon phai con nguyen sau khi ve lai");

  // Lần chọn thứ hai — đúng chỗ bản cũ chết.
  s.el.value = "Tool dịch";
  s.el.onchange.call(s.el);
  assert.equal(s.state.filters.agent, "Tool dịch");
  assert.equal(s.soLanRenderAll, 2,
               "lan chon thu hai cung phai lam moi dashboard");
});

test("danh sach lua chon doi thi moi dung lai DOM", () => {
  const s = dungSandbox();
  s.fillSelect("f-model", ["gemini-2.5-flash"], "", "Tất cả model");
  assert.equal(s.el.soLanDungLaiDom, 1);
  s.fillSelect("f-model", ["gemini-2.5-flash"], "", "Tất cả model");
  assert.equal(s.el.soLanDungLaiDom, 1, "danh sach y nguyen");
  s.fillSelect("f-model", ["gemini-2.5-flash", "gemini-2.5-pro"], "", "Tất cả model");
  assert.equal(s.el.soLanDungLaiDom, 2, "danh sach doi thi phai dung lai");
});

test("onchange chi gan MOT lan, khong gan lai sau moi lan ve", () => {
  const s = dungSandbox();
  const opts = ["a", "b"];
  s.fillSelect("f-agent", opts, "", "Tất cả agent");
  const tay = s.el.onchange;
  s.fillSelect("f-agent", opts, "", "Tất cả agent");
  assert.equal(s.el.onchange, tay, "phai la cung mot ham");
});

test("gia tri lua chon di qua thuoc tinh value, khong qua phan chu", () => {
  const s = dungSandbox();
  const ten = "TT&TMĐT";              // ký tự & phải escape trong thuộc tính
  s.fillSelect("f-dept", [ten], ten, "Tất cả phòng ban");
  assert.ok(s.el.innerHTML.indexOf('value="TT&amp;TMĐT"') >= 0, s.el.innerHTML);
  assert.equal(s.el.value, ten, "value phai khop lai duoc voi state.filters");
});
