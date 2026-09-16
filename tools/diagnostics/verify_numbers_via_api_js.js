/* Chay CHINH web/js/api.js trong Node, noi vao backend THAT, roi doi chieu con
 * so ma app.js SE hien voi cac moc da chot.
 *
 * CAN: docker compose up -d  +  uvicorn dang chay o 127.0.0.1:8000
 *
 * Vi sao o tools/: phu thuoc backend va du lieu that.
 *
 *     node tools/diagnostics/verify_numbers_via_api_js.js
 */
"use strict";
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = "D:/RangDonk/token-ledger-dashboard";
const API = "http://127.0.0.1:8000";

/* MOC — con so api.js PHAI cho ra, khong phai SUM tho tren database.
 *
 * Hai cot khac SUM tho, va ca hai deu co ly do da chung minh:
 *
 * 1. cached = 224.609.584, KHONG phai 227.679.097.
 *    api.js:157 chi chuyen tiep `cached` khi nguon la billing:
 *        app         3.069.513  LA TAP CON cua prompt_tokens -> cong vao la
 *                               dem hai lan
 *        billing   224.609.584  nam NGOAI input -> phai cong
 *        monitoring         0   khong co phep do
 *    224.609.584 khop dung con so ghi trong
 *    db/migrations/sql/001_baseline.sql:525.
 *
 * 2. total = 851.897.150, KHONG phai SUM(total_tokens) = 851.897.312.
 *    Chenh 162 da khoanh vung: DUNG 23 dong, model gemini-2.5-flash-lite,
 *    nguon app - chinh app bao total khac prompt+completion. Buoc nap
 *    build_usage_daily cung bao chuyen nay. Day la thuoc tinh cua DU LIEU,
 *    khong phai loi cua lop dich, va giong nhau tren ca hai he quan tri.
 *
 *    GHIM thanh phep kiem rieng (CHENH_DA_BIET) chu KHONG noi dung sai: neu
 *    con so nay doi thi phai biet ngay.
 */
const MOC = {
  input: 539827701, output: 87459865,
  cached: 224609584,          // chi billing
  total: 851897150,           // = input + output + cached(billing)
  cost: 285.181995, dong: 1161,
  ngayDau: "2026-01-01", ngayCuoi: "2026-08-13", soAgent: 8,
};

const CHENH_DA_BIET = {
  sumTotalTrongDb: 851897312,  // SUM(total_tokens) tren usage_resolved
  chenh: 162,                  // 23 dong gemini-2.5-flash-lite nguon app
};

// api.js chi can `window` co location.search va fetch toan cuc.
const sandbox = {
  window: { location: { search: "" } },
  fetch, URLSearchParams, console, Promise,
};
sandbox.global = sandbox;
vm.runInNewContext(
  fs.readFileSync(path.join(ROOT, "web/js/api.js"), "utf8"),
  sandbox, { filename: "api.js" });

const A = sandbox.window.TokenLedgerAPI;
if (!A) { console.error("api.js khong gan TokenLedgerAPI vao window"); process.exit(1); }

A.load().then((kt) => {
  /* Hop dong MOI (17/08/2026): load() tra ve {ok:true,data} hoac {ok:false,error}.
     Truoc day no tra ve state truc tiep, hoac null khi hong - va `null` la ly do
     bon tinh huong that bai khac nhau deu trong y het nhau o phia goi. */
  if (!kt || typeof kt.ok !== "boolean") {
    console.error("LOI: load() khong tra ve {ok,...} - hop dong bi pha");
    process.exit(1);
  }
  if (!kt.ok) {
    console.error("LOI: nap that bai - " + kt.error.kind + ": " + kt.error.message);
    process.exit(1);
  }
  const s = kt.data;

  let ti = 0, to = 0, cached = 0, cost = 0, dong = 0;
  const agents = new Set(), models = new Set();
  for (const d of s.dayOrder) {
    for (const r of s.days[d]) {
      ti += r.ti; to += r.to; cached += r.cached;
      cost += (r.cost || 0);
      dong++; agents.add(r.a); models.add(r.m);
    }
  }
  const total = ti + to + cached;   // dung phep cong ma app.js dung

  const ok = [];
  const fail = [];
  const kiem = (ten, duoc, mong, dungSai = 0) => {
    const khop = dungSai ? Math.abs(duoc - mong) <= dungSai : duoc === mong;
    (khop ? ok : fail).push(
      `${ten.padEnd(16)} duoc ${String(duoc).padStart(14)}  mong ${String(mong).padStart(14)}`);
  };

  kiem("input", ti, MOC.input);
  kiem("output", to, MOC.output);
  kiem("cached", cached, MOC.cached);
  kiem("total (i+o+c)", total, MOC.total);
  kiem("so dong", dong, MOC.dong);
  kiem("ngay dau", s.dayOrder[0], MOC.ngayDau);
  kiem("ngay cuoi", s.dayOrder[s.dayOrder.length - 1], MOC.ngayCuoi);
  kiem("so agent", agents.size, MOC.soAgent);
  kiem("cost", Number(cost.toFixed(6)), MOC.cost, 0.000001);
  // Ghim chenh da biet: KHONG noi dung sai cho phep kiem tren, ma khang dinh
  // chenh dung bang 162. Doi so nay la co gi da thay doi trong du lieu nguon.
  kiem("chenh da biet", CHENH_DA_BIET.sumTotalTrongDb - total, CHENH_DA_BIET.chenh);

  console.log("=".repeat(70));
  console.log("api.js nap tu backend Postgres — con so app.js SE hien thi");
  console.log("=".repeat(70));
  for (const l of ok) console.log("  KHOP  " + l);
  for (const l of fail) console.log("  LECH  " + l);

  console.log("");
  console.log("  kieu du lieu (bi noi chuoi thi day la 'string'):");
  for (const [k, v] of Object.entries({ ti, to, cached, total, cost }))
    console.log(`    ${k.padEnd(8)} ${typeof v}`);

  console.log("");
  console.log(`  so agent : ${agents.size}  ${[...agents].sort().join(" | ")}`);
  console.log(`  so model : ${models.size}`);
  console.log(`  bang gia : ${Object.keys(s.pricing || {}).length} model co gia`);
  console.log(`  ngan sach: ${(s.budgets || []).length} agent co han muc`);
  console.log(`  ty gia   : ${s.fxRate ? s.fxRate.vnd_per_usd : "(khong co)"}`);
  console.log(`  adoption : ${(s.adoption || []).length} dong`);
  console.log(`  accounts : ${(s.accounts || []).length} dong`);
  console.log(`  byAccount: ${(s.byAccount || []).length} dong`);
  console.log(`  canh bao : ${(s.health && s.health.warnings || []).length} muc`);

  console.log("");
  console.log("=".repeat(70));
  console.log(fail.length === 0
    ? `DAT — ca ${ok.length}/${ok.length} phep kiem khop`
    : `KHONG DAT — ${fail.length} phep lech`);
  process.exit(fail.length === 0 ? 0 : 1);
}).catch((e) => { console.error("NEM LOI:", e); process.exit(1); });
