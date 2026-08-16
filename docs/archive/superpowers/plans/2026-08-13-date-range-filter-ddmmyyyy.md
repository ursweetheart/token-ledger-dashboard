# Date Range Filter `dd/mm/yyyy` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Change only the two “Khoảng thời gian” text inputs to display and accept `dd/mm/yyyy` while preserving every other dashboard date format and all ISO state values.

**Architecture:** Add a dedicated `fmtRangeDateVI(iso)` formatter beside the existing typed-date parser and call it only from `renderRange()`. Update `parseTypedDate()` so its day-first branch returns ISO, while retaining its existing ISO branch; leave `fmtDateUS()` and all non-filter consumers unchanged.

**Tech Stack:** Browser JavaScript (ES5-style application code), HTML5, Node.js built-in `node:test`, `assert`, and `vm` modules.

## Global Constraints

- Only `range-start-text` and `range-end-text` change visible/input format.
- Internal range values and hidden calendar inputs remain `yyyy-mm-dd`.
- Header, “Kỳ dữ liệu”, account tables, “Ngày nhập liệu”, presets, filtering, and CSV behavior remain unchanged.
- Manual input accepts `dd/mm/yyyy` and retains ISO `yyyy-mm-dd` compatibility.
- Invalid calendar dates do not update the active range.

---

### Task 1: Range filter formatter and parser

**Files:**
- Create: `test/date-range-filter.test.js`
- Modify: `app.js:4689-4737`

**Interfaces:**
- Consumes: ISO date strings in `yyyy-mm-dd` from `state.range` and native date inputs.
- Produces: `fmtRangeDateVI(iso: string): string`; `parseTypedDate(text: string): string|null` with day-first manual input.

- [ ] **Step 1: Write the failing behavior tests**

Create `test/date-range-filter.test.js` with:

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const ROOT = path.resolve(__dirname, "..");
const APP_PATH = path.join(ROOT, "app.js");

function appSource() {
  return fs.readFileSync(APP_PATH, "utf8");
}

function loadDateRangeApi() {
  const bootstrap = /if\(document\.readyState==="loading"\) document\.addEventListener\("DOMContentLoaded", init\);\s*else init\(\);\s*\}\)\(\);\s*$/;
  let source = appSource();
  assert.match(source, bootstrap, "test harness must replace the dashboard bootstrap");
  source = source.replace(
    bootstrap,
    `globalThis.__dateRangeTestApi = {
      formatRangeDate: typeof fmtRangeDateVI === "function" ? fmtRangeDateVI : fmtDateUS,
      parseTypedDate: parseTypedDate
    };
    })();`
  );
  const sandbox = {};
  vm.runInNewContext(source, sandbox, { filename: APP_PATH });
  return sandbox.__dateRangeTestApi;
}

test("range filter formats ISO dates as dd/mm/yyyy", () => {
  const api = loadDateRangeApi();
  assert.equal(api.formatRangeDate("2026-08-09"), "09/08/2026");
});

test("manual range input interprets day before month", () => {
  const api = loadDateRangeApi();
  assert.equal(api.parseTypedDate("09/08/2026"), "2026-08-09");
});

test("manual range input retains ISO compatibility", () => {
  const api = loadDateRangeApi();
  assert.equal(api.parseTypedDate("2026-08-09"), "2026-08-09");
});

test("manual range input rejects a nonexistent calendar date", () => {
  const api = loadDateRangeApi();
  assert.equal(api.parseTypedDate("31/02/2026"), null);
});

test("only renderRange switches away from the shared US formatter", () => {
  const source = appSource();
  assert.match(source, /if\(st\) st\.value = fmtRangeDateVI\(state\.range\.start\);/);
  assert.match(source, /if\(et\) et\.value = fmtRangeDateVI\(state\.range\.end\);/);
  assert.match(source, /set\("status-period", esc\(fmtDateUS\(state\.range\.start\)\+" → "\+fmtDateUS\(state\.range\.end\)\)\);/);
  assert.match(source, /set\("header-data-date", esc\(fmtDateUS\(toISO\(maxDataDate\(\)\)\)\)\);/);
});
```

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```powershell
node --test test/date-range-filter.test.js
```

Expected: the formatting, day-first parsing, and `renderRange()` scoping tests fail because the current code uses `mm/dd/yyyy` and `fmtDateUS()`.

- [ ] **Step 3: Implement the minimal JavaScript change**

In `app.js`, replace the range-input comment and parser prefix with:

```javascript
/* ─── Ô ngày: gõ tay hoặc chọn lịch ───
   Riêng hai ô text của bộ lọc nhận dd/mm/yyyy và cũng chấp nhận yyyy-mm-dd.
   Nhập sai thì giữ nguyên khoảng đang xem và báo lỗi ngay tại chỗ. */
function fmtRangeDateVI(iso){
  var p=String(iso==null?"":iso).split("-");
  return p.length===3 ? (p[2]+"/"+p[1]+"/"+p[0]) : String(iso);
}
function parseTypedDate(text){
  var t=String(text==null?"":text).trim();
  if(!t) return null;
  var m=t.match(/^(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{4})$/);      // dd/mm/yyyy
  var y,mo,d;
  if(m){ d=+m[1]; mo=+m[2]; y=+m[3]; }
  else {
    m=t.match(/^(\d{4})[\/\-.](\d{1,2})[\/\-.](\d{1,2})$/);        // yyyy-mm-dd
    if(!m) return null;
    y=+m[1]; mo=+m[2]; d=+m[3];
  }
```

Keep the existing bounds/UTC validation and ISO return below that prefix. Change the invalid-input message in `bindRangeField()` to:

```javascript
else { rangeHint("Ngày không hợp lệ — nhập theo dd/mm/yyyy."); renderRange(); }
```

Change only the two text assignments in `renderRange()` to:

```javascript
if(st) st.value = fmtRangeDateVI(state.range.start);
if(et) et.value = fmtRangeDateVI(state.range.end);
```

Update the wiring comment near `bindRangeField("start")` to name `dd/mm/yyyy`; do not modify `renderStatus()` or `fmtDateUS()`.

- [ ] **Step 4: Run the targeted test and verify GREEN**

Run:

```powershell
node --test test/date-range-filter.test.js
```

Expected: 5 tests pass with no errors or warnings.

- [ ] **Step 5: Commit the behavior change**

```powershell
git add -- app.js test/date-range-filter.test.js
git -c user.name="Codex" -c user.email="codex@localhost" commit -m "fix: use day-first dates in range filter"
```

### Task 2: Range filter copy and accessibility metadata

**Files:**
- Modify: `test/date-range-filter.test.js`
- Modify: `index.html:286-296`

**Interfaces:**
- Consumes: The `dd/mm/yyyy` input contract from Task 1.
- Produces: Matching placeholder and `aria-label` text on both filter text inputs.

- [ ] **Step 1: Add the failing HTML contract test**

Append to `test/date-range-filter.test.js`:

```javascript
test("both range text inputs advertise dd/mm/yyyy", () => {
  const html = fs.readFileSync(path.join(ROOT, "index.html"), "utf8");
  for (const id of ["range-start-text", "range-end-text"]) {
    const tag = html.match(new RegExp(`<input[^>]+id=["']${id}["'][^>]*>`));
    assert.ok(tag, `missing ${id}`);
    assert.match(tag[0], /placeholder="dd\/mm\/yyyy"/);
    assert.match(tag[0], /aria-label="[^"]+\(dd\/mm\/yyyy\)"/);
  }
  assert.match(html, /Gõ tay theo dd\/mm\/yyyy hoặc bấm/);
});
```

- [ ] **Step 2: Run the targeted test and verify RED**

Run:

```powershell
node --test test/date-range-filter.test.js
```

Expected: the new HTML contract test fails because both inputs still advertise `mm/dd/yyyy`.

- [ ] **Step 3: Update only the two filter inputs**

In `index.html`, change the toolbar comment, both `placeholder` attributes, and both manual-input `aria-label` attributes from `mm/dd/yyyy` to `dd/mm/yyyy`. Leave `type="date"` inputs and all other dashboard markup unchanged.

- [ ] **Step 4: Run targeted and regression verification**

Run:

```powershell
node --test test/date-range-filter.test.js
python -m unittest discover -s test -p "test*.py"
git diff --check
```

Expected: 6 Node tests pass; Python discovery exits successfully; `git diff --check` reports no whitespace errors.

- [ ] **Step 5: Confirm the diff is limited and commit**

Run:

```powershell
git diff -- app.js index.html test/date-range-filter.test.js
git add -- index.html test/date-range-filter.test.js
git -c user.name="Codex" -c user.email="codex@localhost" commit -m "fix: label range dates as day first"
```

Expected: the diff contains only the dedicated range formatter/parser, two `renderRange()` calls, range-specific copy, and the new regression test; the pre-existing deleted files remain unstaged and uncommitted.
