const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const APP_PATH = path.join(ROOT, "app.js");

function createDocument() {
  const ids = {};
  [
    "range-start",
    "range-end",
    "range-start-text",
    "range-end-text",
    "range-presets",
    "status-period",
    "header-data-date",
  ].forEach((id) => {
    ids[id] = {
      value: "",
      innerHTML: "",
      textContent: "",
      className: "",
      children: [],
      appendChild(child) {
        this.children.push(child);
      },
    };
  });
  return {
    ids,
    getElementById(id) {
      return ids[id] || null;
    },
    createElement() {
      return { className: "", textContent: "", onclick: null };
    },
  };
}

function loadDateRangeApp() {
  const bootstrap = /if\(document\.readyState==="loading"\) document\.addEventListener\("DOMContentLoaded", init\);\s*else init\(\);\s*\}\)\(\);\s*$/;
  let source = fs.readFileSync(APP_PATH, "utf8");
  assert.match(source, bootstrap, "test harness must replace the dashboard bootstrap");
  source = source.replace(
    bootstrap,
    `globalThis.__dateRangeTestApi = {
      formatRangeDate: typeof fmtRangeDateVI === "function" ? fmtRangeDateVI : fmtDateUS,
      parseTypedDate: parseTypedDate,
      renderRange: renderRange,
      renderStatus: renderStatus,
      setState: function(nextState) { state = nextState; }
    };
    })();`
  );
  const document = createDocument();
  const window = { RALLI_USERS: [] };
  const sandbox = { document, window, setTimeout, clearTimeout };
  vm.runInNewContext(source, sandbox, { filename: APP_PATH });
  return { api: sandbox.__dateRangeTestApi, document };
}

test("range filter formats ISO dates as dd/mm/yyyy", () => {
  const { api } = loadDateRangeApp();
  assert.equal(api.formatRangeDate("2026-08-09"), "09/08/2026");
});

test("manual range input interprets day before month", () => {
  const { api } = loadDateRangeApp();
  assert.equal(api.parseTypedDate("09/08/2026"), "2026-08-09");
});

test("manual range input retains ISO compatibility", () => {
  const { api } = loadDateRangeApp();
  assert.equal(api.parseTypedDate("2026-08-09"), "2026-08-09");
});

test("manual range input rejects a nonexistent calendar date", () => {
  const { api } = loadDateRangeApp();
  assert.equal(api.parseTypedDate("31/02/2026"), null);
});

test("range rendering changes without changing other dashboard dates", () => {
  const { api, document } = loadDateRangeApp();
  api.setState({
    range: { start: "2026-07-01", end: "2026-08-09" },
    dayOrder: ["2026-08-13"],
  });

  api.renderRange();
  assert.equal(document.ids["range-start-text"].value, "01/07/2026");
  assert.equal(document.ids["range-end-text"].value, "09/08/2026");

  api.renderStatus();
  assert.equal(document.ids["status-period"].innerHTML, "07/01/2026 → 08/09/2026");
  assert.equal(document.ids["header-data-date"].innerHTML, "08/13/2026");
});

test("both range text inputs advertise dd/mm/yyyy", () => {
  const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  for (const id of ["range-start-text", "range-end-text"]) {
    const tag = html.match(new RegExp(`<input[^>]+id=["']${id}["'][^>]*>`));
    assert.ok(tag, `missing ${id}`);
    assert.match(tag[0], /placeholder="dd\/mm\/yyyy"/);
    assert.match(tag[0], /aria-label="[^"]+\(dd\/mm\/yyyy\)"/);
  }
});
