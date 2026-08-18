const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const API_PATH = path.join(ROOT, "web", "js", "api.js");

function loadApi(protocol, search) {
  const window = {
    location: { protocol, search },
    URLSearchParams,
    console: { warn() {} },
  };
  const source = fs.readFileSync(API_PATH, "utf8");
  vm.runInNewContext(source, { window, URLSearchParams }, { filename: API_PATH });
  return window.TokenLedgerAPI;
}

test("hosted HTTPS uses the same-origin API", () => {
  assert.equal(loadApi("https:", "").base(), "");
});

test("file mode preserves the local API fallback", () => {
  assert.equal(loadApi("file:", "").base(), "http://127.0.0.1:8000");
});

test("api query parameter overrides hosted and file defaults", () => {
  const search = "?api=https%3A%2F%2Fapi.example.test%2F";
  assert.equal(loadApi("https:", search).base(), "https://api.example.test");
  assert.equal(loadApi("file:", search).base(), "https://api.example.test");
});
