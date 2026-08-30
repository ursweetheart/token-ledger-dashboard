"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const appSource = fs.readFileSync(path.join(__dirname, "..", "web", "js", "app.js"), "utf8");

test("department filter options are built from all reporting roots instead of only rows in scope", () => {
  const helperMatch = appSource.match(/function buildDepartmentFilterOptions\([\s\S]*?\n\}/);
  assert.ok(helperMatch, "buildDepartmentFilterOptions helper should exist");

  const code = helperMatch[0];
  const sandbox = {
    console,
    Object,
    Array,
    String,
    Math,
    ORG_UNITS: [
      { id: "dept-1", name: "Công ty" },
      { id: "dept-2", name: "PBH" },
      { id: "dept-3", name: "CN HCM" },
      { id: "dept-4", name: "Đội 1" },
      { id: "dept-6", name: "Đang trong quá trình thử nghiệm" }
    ],
    isExcludedUnit: (u) => !u || !u.name || u.name === "Đang trong quá trình thử nghiệm",
    reportingRootOf: (unitId) => ({ id: unitId, name: unitId === "dept-2" ? "PBH" : unitId === "dept-3" ? "CN HCM" : "Công ty" }),
    // Đơn vị "auto:" do unitOf() dựng — sáu agent Google Cloud Console sống ở đây.
    unitRoots: () => [
      { id: "auto:Sale Agent", name: "Sale Agent", auto: true },
      { id: "auto:Chưa quy được", name: "Chưa quy được", auto: true }
    ],
    isUnattributedUnit: (u) => !!u && u.name === "Chưa quy được",
    doesNotExist: null,
  };

  vm.runInNewContext(code + "\n; this.result = buildDepartmentFilterOptions();", sandbox);
  assert.ok(Array.isArray(sandbox.result));
  // "Sale Agent" vào danh sách theo quy ước "phòng ban của agent Google Cloud
  // Console là chính tên agent"; "Chưa quy được" thì không, nó là sọt đựng.
  assert.equal(sandbox.result.join(","), "CN HCM,Công ty,PBH,Sale Agent,Đội 1");
  assert.equal(sandbox.result.indexOf("Chưa quy được"), -1);
});

test("danh muc tai khoan giu moi user real cua database", () => {
  const match = appSource.match(/function buildAccountCatalogueFromDb\([\s\S]*?\n\}/);
  assert.ok(match, "database account catalog should exist");

  const sandbox = {
    console, Object, Array, String, Math,
    REAL_ACCOUNTS: [
      { account_id: 1, username: "tuan.nv", full_name: "Tuấn NV", kind: "real", agent: "Trợ lý ảo Ralli", unit_id: "u1", unit_name: "PBH1", is_shared: false, role: "employee", is_enabled: true, created_at: "2026-08-01", in_directory: true },
      { account_id: 2, username: "lan.nv", full_name: "Lan NV", kind: "real", agent: "Trợ lý ảo Ralli", unit_id: "u2", unit_name: "PBH2", is_shared: false, role: "employee", is_enabled: true, created_at: "2026-08-01", in_directory: true },
      { account_id: 3, username: "hai.nv", full_name: "Hai NV", kind: "real", agent: "Trợ Lý Ảo Hợp Đồng", unit_id: "u3", unit_name: "Phòng BH1", is_shared: false, role: "employee", is_enabled: true, created_at: "2026-08-01", in_directory: true },
      // Tài khoản dịch vụ: /api/accounts vốn đã lọc `kind='real'`, đây là lưới thứ hai.
      { account_id: 4, username: "svc.sale", full_name: "Sale service", kind: "service_account", agent: "Sale Agent", unit_id: "u1", unit_name: "PBH1", is_shared: true, role: "AI Agent", is_enabled: true, created_at: "2026-08-01", in_directory: false }
    ],
    unitById: (id) => ({ id: id, name: id === "u1" ? "PBH1" : id === "u2" ? "PBH2" : "Phòng BH1" }),
    unitOf: (name) => ({ id: "u3", name: name || "Phòng BH1" }),
    isExcludedUnit: (u) => !u || (u.name && u.name === "Đang trong quá trình thử nghiệm")
  };

  vm.runInNewContext(match[0] + "\n; this.catalog = buildAccountCatalogueFromDb();", sandbox);
  const names = sandbox.catalog.map((u) => u.n || u.user || u.login || "");
  assert.deepEqual(names.sort(), ["Hai NV", "Lan NV", "Tuấn NV"].sort());
});

/* Ô lọc User trước 30/08/2026 chỉ nhận user của hai agent gõ cứng ("Sale Agent",
   "Chatbot Contact Center"). Database không có tài khoản nào thuộc hai agent đó,
   nên ô lọc rỗng hoàn toàn. Phép kiểm cũ khoá đúng hành vi ấy lại; nay nó khoá
   luật MỚI: nhận mọi user thật, vẫn loại nhãn trùng tên agent. */
test("o loc User nhan moi user that, va loai nhan trung ten agent", () => {
  const match = appSource.match(/function userFilterLabel\(u\)\{[\s\S]*?\n\}/);
  assert.ok(match, "userFilterLabel helper should exist");

  const sandbox = {
    console, Object, Array, String, Math,
    USER_ACCOUNTS: [
      { a: "Trợ lý ảo Ralli", ug: "Tuấn NV" },
      { a: "Trợ lý ảo Ralli", ug: "Trợ lý ảo Ralli" },        // nhãn = tên agent
      { a: "Trợ Lý Ảo Hợp Đồng", ug: "Hai NV" },
      { a: "Trợ Lý Ảo Hợp Đồng", ug: "Trợ Lý Ảo Hợp Đồng" },  // nhãn = tên agent
      // Người dùng quy ước của agent Google Cloud Console.
      { a: "Sale Agent", ug: "Người dùng Agent Sale Agent" },
      { a: "Tool dịch", ug: "Người dùng Agent Tool dịch" }
    ]
  };

  vm.runInNewContext(
    match[0] + "\n; this.userList = (USER_ACCOUNTS || []).map(userFilterLabel).filter(Boolean);",
    sandbox);

  assert.deepEqual(sandbox.userList.sort(), [
    "Hai NV", "Người dùng Agent Sale Agent", "Người dùng Agent Tool dịch", "Tuấn NV"
  ].sort());
  // Tên agent trần không phải một danh tính người dùng.
  assert.ok(!sandbox.userList.includes("Trợ lý ảo Ralli"));
  assert.ok(!sandbox.userList.includes("Trợ Lý Ảo Hợp Đồng"));
});

/* Quy ước cho sáu project Google Cloud Console: phòng ban là chính tên agent,
   người dùng là "Người dùng Agent <tên agent>". Nhãn người dùng PHẢI khác tên
   agent — nếu trùng, userFilterLabel() coi đó là "không có danh tính" và loại
   nó khỏi ô lọc, tức agent lại không có user nào. */
test("nhan nguoi dung quy uoc khac ten agent", () => {
  const match = appSource.match(/function serviceAgentUserLabel\(agent\)\{[\s\S]*?\n\}/);
  assert.ok(match, "serviceAgentUserLabel helper should exist");

  const sandbox = { String };
  vm.runInNewContext(match[0] + "\n; this.nhan = serviceAgentUserLabel('Sale Agent');", sandbox);
  assert.equal(sandbox.nhan, "Người dùng Agent Sale Agent");
  assert.notEqual(sandbox.nhan, "Sale Agent");
});

/* isServiceAgent() phải đọc câu trả lời của database (/api/adoption `kind`),
   không được đoán bằng tên agent. */
test("isServiceAgent doc kind tu /api/adoption chu khong doan theo ten", () => {
  const match = appSource.match(/function isServiceAgent\(agent\)\{[\s\S]*?\n\}/);
  assert.ok(match, "isServiceAgent helper should exist");

  const sandbox = {
    String,
    ADOPTION_BY_AGENT: [
      { agent: "Sale Agent", kind: "service" },
      { agent: "Trợ lý ảo Ralli", kind: "people" }
    ]
  };
  vm.runInNewContext(match[0] +
    "\n; this.a = isServiceAgent('Sale Agent');" +
    "\n; this.b = isServiceAgent('Trợ lý ảo Ralli');" +
    "\n; this.c = isServiceAgent('Agent la hoac');", sandbox);
  assert.equal(sandbox.a, true);
  assert.equal(sandbox.b, false);
  assert.equal(sandbox.c, false, "agent khong co trong adoption thi khong duoc coi la service");
});
