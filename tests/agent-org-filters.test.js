"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const root = path.join(__dirname, "..");
const source = name => fs.readFileSync(path.join(root, "web", "js", name), "utf8");

// Dữ liệu kiểm thử, không phải bản sao database hay mapping nghiệp vụ.
const catalog = {
  agents: [{agent_id: 1, name: "A"}, {agent_id: 2, name: "B"}, {agent_id: 3, name: "Service"}],
  models: [{model_id: 1, name: "Gemini test", price_input: 1, price_output: 2}],
  units: [
    {unit_id: "a-root", agent_id: 1, name: "Công ty", level: 1, is_report_aggregate: true},
    {unit_id: "a-dept", agent_id: 1, name: "Phòng chung", parent_id: "a-root", level: 2},
    {unit_id: "a-unit", agent_id: 1, name: "Đơn vị", parent_id: "a-dept", level: 3},
    {unit_id: "a-team", agent_id: 1, name: "Đội", parent_id: "a-unit", level: 4},
    {unit_id: "a-leaf", agent_id: 1, name: "Tổ", parent_id: "a-team", level: 5},
    {unit_id: "a-other", agent_id: 1, name: "Phòng chung", parent_id: "a-root", level: 2},
    {unit_id: "b-dept", agent_id: 2, name: "Phòng chung", level: 1, canonical_unit_id: "a-dept"},
    {unit_id: "b-team", agent_id: 2, name: "Đội", parent_id: "b-dept", level: 2},
    {unit_id: "svc", agent_id: 3, name: "Đơn vị sử dụng Service", level: 0, is_technical: true}
  ]
};
function api() {
  const s = {window: {location: {protocol: "http:"}}};
  vm.runInNewContext(source("api.js").replace("})(window);", "global.probe = {orgTree, buildState}; })(window);"), s);
  return s.window.probe;
}
function app() {
  const elements = {};
  const s = {
    console, Blob, URL: {createObjectURL(b) { s.blob = b; return "blob:test"; }, revokeObjectURL() {}},
    localStorage: {setItem() {}, getItem() {return null;}},
    document: {readyState: "loading", addEventListener() {},
      getElementById(id) { return elements[id] ||= {value: "", innerHTML: "", attrs: {},
        style:{}, classList:{add(){},remove(){},toggle(){},contains(){return false;}},
        closest(){return null;},querySelector(){return null;},querySelectorAll(){return [];},addEventListener(){},appendChild(){},
        getAttribute(k) {return this.attrs[k] ?? null;}, setAttribute(k,v) {this.attrs[k] = v;}}; },
      body:{classList:{contains(){return false;}}},querySelector(){return null;},querySelectorAll(){return [];},
      createElement() {return {click() {},style:{}};}}
  };
  vm.runInNewContext(source("app.js").replace(/\}\)\(\);\s*$/, "globalThis.run = code => eval(code); })();"), s);
  s.elements = elements;
  s.run("state = defaultState();");
  s.units = api().orgTree(catalog).units;
  s.run("adoptOrgUnits(globalThis.units);");
  return s;
}
const plain = x => JSON.parse(JSON.stringify(x));

test("catalog giữ cây, ID và cha gốc riêng cho từng agent, kể cả canonical liên agent", () => {
  const tree = api().orgTree(catalog);
  assert.equal(tree.units.length, catalog.units.length);
  assert.equal(tree.units.find(u => u.id === "b-dept").agentId, 2);
  assert.equal(tree.units.find(u => u.id === "b-team").parent, "b-dept");
  assert.equal(tree.units.find(u => u.id === "a-dept").agent, "A");
  assert.equal(tree.units.find(u => u.id === "svc").technical, true);
  assert.equal(tree.canonicalOf["b-dept"], "b-dept");
});

test("Agent → Phòng ban → Đơn vị → Đội: khóa, ID nguồn, reset và nhãn HTML", () => {
  const s = app();
  s.run("renderFilters();");
  for (const key of ["dept", "unit", "team"]) assert.equal(s.elements["f-" + key].disabled, true);
  s.run('state.filters.agent="A"; renderFilters();');
  assert.match(s.elements["f-dept"].innerHTML, /value="a-dept"/);
  assert.match(s.elements["f-dept"].innerHTML, /value="a-other"/);
  assert.doesNotMatch(s.elements["f-dept"].innerHTML, /b-dept|a-team|a-root/);
  s.elements["f-dept"].value = "a-dept";
  s.run('renderAll = renderFilters; state.filters.user="cũ";');
  s.elements["f-dept"].onchange();
  assert.equal(s.run("state.filters.user"), "");
  assert.match(s.elements["f-unit"].innerHTML, /value="a-unit"/);
  s.elements["f-unit"].value = "a-unit";
  s.elements["f-unit"].onchange();
  assert.match(s.elements["f-team"].innerHTML, /value="a-team"/);
  s.run('state.filters.team="a-team"; state.filters.user="cũ";');
  s.elements["f-dept"].value = "a-other";
  s.elements["f-dept"].onchange();
  assert.deepEqual(plain(s.run('[state.filters.unit,state.filters.team,state.filters.user]')), ["", "", ""]);
  s.run('state.filters.dept="a-dept"; state.filters.unit="a-unit"; state.filters.team="a-team"; state.filters.user="cũ";');
  s.elements["f-agent"].value = "B";
  s.elements["f-agent"].onchange();
  assert.deepEqual(plain(s.run('[state.filters.dept,state.filters.unit,state.filters.team,state.filters.user]')), ["", "", "", ""]);
  assert.match(s.elements["f-dept"].innerHTML, /b-dept/);
  s.elements["f-agent"].value = "Service";
  s.elements["f-agent"].onchange();
  assert.equal(s.elements["f-dept"].disabled, true);
  s.run('state.filters.agent=""; state.filters.dept="a-dept"; renderFilters();');
  assert.equal(s.run("state.filters.dept"), "");
  const html = fs.readFileSync(path.join(root, "web/index.html"), "utf8");
  const ids = [...html.matchAll(/id="f-(agent|dept|unit|team|user)"/g)].map(m => m[1]);
  assert.deepEqual(ids, ["agent", "dept", "unit", "team", "user"]);
  assert.match(html, /<label for="f-dept">Phòng ban<\/label>/);
});

test("usage và account cùng scope hậu duệ; CSV giữ cùng số, ngày/model/provider không mất", async () => {
  const s = app();
  s.run(`
    state.range={start:"2026-09-01",end:"2026-09-01"};
    state.dayOrder=["2026-09-01","2026-09-02"];
    state.days={"2026-09-01":[{a:"A",unitId:"a-root",m:"Gemini test",r:99,day:"2026-09-01"}],
                "2026-09-02":[{a:"A",unitId:"a-root",m:"Gemini test",r:200,day:"2026-09-02"}]};
    state.modelNameById={1:"Gemini test",2:"GPT test"};
    state.pricing={"Gemini test":{i:1,o:2}}; state.pricingById={1:{i:1,o:2}};
    USER_ACCOUNTS=[{id:1,a:"A",unitId:"a-leaf",ug:"An",login:"an"},
      {id:2,a:"B",unitId:"b-team",ug:"An",login:"an"},
      {id:3,a:"A",unitId:"a-other",ug:"Bình",login:"binh"}];
    REAL_BY_ACCOUNT=[
      {day:"2026-09-01",account_id:1,agent:"A",unit_id:"a-leaf",model_id:1,full_name:"An",calls:3,input_tokens:10,output_tokens:2},
      {day:"2026-09-01",account_id:2,agent:"B",unit_id:"b-team",model_id:1,full_name:"An",calls:70},
      {day:"2026-09-01",account_id:3,agent:"A",unit_id:"a-other",model_id:1,full_name:"Bình",calls:20},
      {day:"2026-09-02",account_id:1,agent:"A",unit_id:"a-leaf",model_id:1,full_name:"An",calls:200},
      {day:"2026-09-01",account_id:1,agent:"A",unit_id:"a-leaf",model_id:2,full_name:"An",calls:4}];
    state.filters={agent:"A",dept:"a-dept",unit:"a-unit",team:"a-team",user:"",model:"Gemini test",provider:"Google AI Studio"};
    applyRealAccountUsage(scopeBase());
  `);
  assert.deepEqual(plain(s.run("filterAccounts().map(u=>u.id)")), [1]);
  assert.equal(s.run("filterAccounts()[0].req"), 3);
  assert.equal(s.run("aggregate(scopedRows()).r"), 3);
  assert.equal(s.run("scopedRows()[0].unitId"), "a-leaf");
  s.run("exportCSV();");
  assert.match(await s.blob.text(), /,10,2,3,/);
  s.run('state.filters.team=""; state.filters.unit=""; state.filters.dept="a-other";');
  assert.equal(s.run("aggregate(scopedRows()).r"), 20);
  s.run('state.filters={agent:"A"};');
  assert.equal(s.run("aggregate(scopedRows()).r"), 99, "không lọc tổ chức vẫn dùng tổng nguồn, không cộng thêm account");
  s.run('state.filters.user="1";');
  assert.equal(s.run("aggregate(scopedRows()).r"), 7, "User dùng ID tài khoản, không gộp nhãn trùng");
  s.run('state.filters.user=""; renderFilters();');
  assert.match(s.elements["f-user"].innerHTML, /value="1"/);
  assert.doesNotMatch(s.elements["f-user"].innerHTML, /value="2"/);
  s.run('state.filters.dept="a-dept"; renderAll();');
  assert.equal(s.run("aggregate(scopedRows()).r"), 7);
});
