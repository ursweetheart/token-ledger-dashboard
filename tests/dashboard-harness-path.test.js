"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const test = require("node:test");

const ROOT = path.resolve(__dirname, "..");
const HARNESS = path.join(ROOT, "tools", "diagnostics", "chay_dashboard_trong_node.js");

test("dashboard harness resolves project files from its own location", () => {
  const cwd = fs.mkdtempSync(path.join(os.tmpdir(), "dashboard-harness-"));
  try {
    const result = spawnSync(process.execPath, [HARNESS, "--check-files"], {
      cwd,
      encoding: "utf8",
      env: { ...process.env, DASHBOARD_BASE: "http://127.0.0.1:1" },
      timeout: 5000,
    });

    assert.equal(result.status, 0, result.error?.message || result.stderr || result.stdout);
    for (const file of ["web/index.html", "web/js/api.js", "web/js/app.js"]) {
      assert.ok(result.stdout.includes(path.join(ROOT, file)), result.stdout);
    }
  } finally {
    fs.rmSync(cwd, { recursive: true, force: true });
  }
});
