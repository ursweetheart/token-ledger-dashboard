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
      { id: "dept-5", name: "Đơn vị sử dụng Sale Agent" },
      { id: "dept-6", name: "Đang trong quá trình thử nghiệm" }
    ],
    isExcludedUnit: (u) => !u || !u.name || u.name === "Đang trong quá trình thử nghiệm" || u.name === "Đơn vị sử dụng Sale Agent",
    reportingRootOf: (unitId) => ({ id: unitId, name: unitId === "dept-2" ? "PBH" : unitId === "dept-3" ? "CN HCM" : "Công ty" }),
    doesNotExist: null,
  };

  vm.runInNewContext(code + "\n; this.result = buildDepartmentFilterOptions();", sandbox);
  assert.ok(Array.isArray(sandbox.result));
  assert.equal(sandbox.result.length, 4);
  assert.equal(sandbox.result.join(","), "CN HCM,Công ty,PBH,Đội 1");
});

test("specific-user selector excludes agent labels and keeps only real user names from the two specific agents", () => {
  const source = fs.readFileSync(path.join(__dirname, "..", "web", "js", "app.js"), "utf8");
  const match = source.match(/function isSpecificUserAgent\(agentName\)[\s\S]*?function userFilterLabel\(u\)\{[\s\S]*?\n\}/);
  assert.ok(match, "specific-user filter helper should exist");

  const sandbox = {
    console,
    Object,
    Array,
    String,
    Math,
    SPECIFIC_USER_AGENTS: { "Sale Agent": true, "Chatbot Contact Center": true },
    isSpecificUserAgent: (agentName) => !!({ "Sale Agent": true, "Chatbot Contact Center": true })[String(agentName || "").trim()],
    userFilterLabel: (u) => {
      var agent = String((u && u.a) || "").trim();
      var label = String((u && (u.ug || u.user || u.login || u.n)) || "").trim();
      if(!label || label === agent) return "";
      if((({ "Sale Agent": true, "Chatbot Contact Center": true })[agent] || ({ "Sale Agent": true, "Chatbot Contact Center": true })[label])) return label;
      return "";
    },
    USER_ACCOUNTS: [
      { a: "Sale Agent", ug: "Sale Agent" },
      { a: "Sale Agent", ug: "Tuấn NV" },
      { a: "Chatbot Contact Center", ug: "Chatbot Contact Center" },
      { a: "Chatbot Contact Center", ug: "Lan NV" },
      { a: "Trợ Lý Ảo Hợp Đồng", ug: "Hai NV" },
      { a: "Trợ Lý Ảo Hợp Đồng", ug: "Trợ Lý Ảo Hợp Đồng" }
    ]
  };

  vm.runInNewContext(match[0] + "\n; this.userList = (USER_ACCOUNTS || []).map(userFilterLabel).filter(Boolean);", sandbox);
  assert.deepEqual(sandbox.userList.sort(), ["Lan NV", "Tuấn NV"].sort());
  assert.ok(!sandbox.userList.includes("Sale Agent"));
  assert.ok(!sandbox.userList.includes("Chatbot Contact Center"));
  assert.ok(!sandbox.userList.includes("Hai NV"));
});
