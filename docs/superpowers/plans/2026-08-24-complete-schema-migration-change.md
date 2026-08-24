# Complete Schema Migration Change Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hoàn tất OpenSpec change `change-the-schema-without-dropping-it`, chứng minh migration tại chỗ giữ nguyên dữ liệu, cắt chuyển an toàn từ `token_ledger_v2` về tên chuẩn `token_ledger`, rồi nghiệm thu 44/44 task.

**Architecture:** Alembic là nguồn schema duy nhất. `connect.rebuild()` vẫn là đường phá huỷ có chủ đích để dựng lại từ `data/`, còn `alembic upgrade` là đường thay đổi schema tại chỗ. Mọi thay đổi mã/tài liệu được làm trong worktree và qua TDD + review; mọi thay đổi database thật phải qua snapshot, rehearsal trên v2, review preflight, backup cùng server và kiểm tra sau thao tác.

**Tech Stack:** Python 3.11, Alembic, SQLAlchemy Core/DBAPI, psycopg2, PostgreSQL, Node.js built-in test runner, OpenSpec 1.3.1.

**Spec:** `openspec/changes/change-the-schema-without-dropping-it/specs/schema-migrations/spec.md`

## Global Constraints

- Mọi thay đổi schema phải áp dụng được lên database đang có dữ liệu và giữ nguyên dữ liệu; đường migration MUST NOT đòi `DROP SCHEMA`, `DROP DATABASE`, hoặc nạp lại từ `data/`.
- `connect.rebuild()` vẫn cố ý xoá schema vì đây là đường “dựng lại toàn bộ từ data/”; nó phải chạy migration trước khi nạp `db/02_catalog.sql`.
- Cấu trúc database chỉ được mô tả bởi chuỗi migration; `db/01_schema.sql` phải biến mất sau khi baseline được bảo toàn.
- Migration đã áp là bất biến. Không sửa nội dung `db/migrations/sql/001_baseline.sql` hoặc `db/migrations/versions/001_baseline_baseline.py`.
- Forward-only: gỡ thay đổi bằng migration tiến mới; không dùng `alembic downgrade`.
- Alembic lấy DSN từ `connect.DEFAULT_DSN`; `-x db=` chỉ là override một lần. Không thêm `sqlalchemy.url` vào `alembic.ini`.
- `db/02_catalog.sql` là seed data sinh bởi `db/gen_catalog.py`, không nằm trong migration.
- Định danh code, file, CLI và JSON dùng tiếng Anh; ghi chú có thể dùng tiếng Việt.
- Database cũ không được xoá trước khi candidate v2 qua baseline 23/23, audit/API/dashboard và rehearsal migration 002/003.
- `DROP DATABASE token_ledger` chỉ được chạy sau khi có backup `token_ledger_pre_cutover_20260824`, mọi kết nối đã đóng, và một reviewer độc lập xác nhận preflight.
- Các tài liệu/migration lịch sử được phép nhắc `01_schema.sql` và `_v2`; runtime code, config và tài liệu vận hành hiện hành thì không.
- Mỗi task phải được review spec + chất lượng; Critical/Important phải sửa và re-review đến khi sạch trước task kế tiếp.

---

### Task 1: Reconcile the OpenSpec execution contract

**Files:**
- Modify: `openspec/changes/change-the-schema-without-dropping-it/tasks.md`
- Modify: `openspec/changes/change-the-schema-without-dropping-it/specs/schema-migrations/spec.md`

**Interfaces:**
- Consumes: audit evidence from commits `5c213c5`, `aa5f7d0`, `8730656`, `7575ee6` and the user's explicit approval on 24/08/2026.
- Produces: a safe, unambiguous task order binding Tasks 2–8 below.

- [ ] **Step 1: Record the non-blocking backup task honestly**

  Change task 1.1 to checked with wording that it was explicitly waived for this change: this checkout contains only the tracked catalog input, not the historical 2.3 GB source tree; no backup is claimed to have happened.

- [ ] **Step 2: Correct stale task state**

  Mark 7.2 complete and cite commit `aa5f7d0`, which already deleted `scripts/copy_to_postgres.py`. Do not claim a new deletion.

- [ ] **Step 3: Make rehearsal a pre-cutover gate**

  Amend 6.3 so 8.1–8.6, especially applying 002 then 003 on `token_ledger_v2`, must finish before 6.4. Record that the user explicitly waived the time-based “wait a few days” gate, but did not waive backup, live snapshot, or independent preflight review.

- [ ] **Step 4: Resolve historical-reference contradictions**

  Clarify task 7.3 and the final `_v2` requirement: zero matches applies to runtime code/config/live operating docs; immutable migrations, archived material, dated journals and OpenSpec history may retain historical names.

- [ ] **Step 5: Validate artifacts**

  Run:

  ```powershell
  openspec.cmd status --change "change-the-schema-without-dropping-it" --json
  openspec.cmd instructions apply --change "change-the-schema-without-dropping-it" --json
  git diff --check
  ```

  Expected: OpenSpec state `ready`, task count unchanged at 44, no whitespace errors.

- [ ] **Step 6: Commit**

  ```powershell
  git add openspec/changes/change-the-schema-without-dropping-it
  git commit -m "docs(schema-migration): correct execution gates"
  ```

---

### Task 2: Protect the rebuild and migration contracts with TDD

**Files:**
- Create: `tests/test_connect_migrations.py`
- Modify: `db/connect.py`
- Modify: `db/migrations/env.py`

**Interfaces:**
- Consumes: `connect.rebuild(dsn: str) -> tuple[connection, "%s"]`, `connect.apply_migrations(dsn: str) -> None`.
- Produces: fail-fast catalog validation and repeatable regression evidence for wipe → migrate → seed ordering and `ACTIVE_DSN` cleanup.

- [ ] **Step 1: Write failing tests**

  Use `unittest`, `unittest.mock`, and temporary paths. The tests must cover these observable breaks:

  ```python
  class RebuildTests(unittest.TestCase):
      def test_missing_catalog_fails_before_opening_or_wiping_database(self): ...
      def test_rebuild_wipes_then_migrates_then_seeds_and_preserves_return_contract(self): ...

  class ApplyMigrationsTests(unittest.TestCase):
      def test_active_dsn_is_reset_when_alembic_upgrade_fails(self): ...
  ```

  The first test patches `connect.DB_DIR` to an empty temporary directory and `connect.open_db`; it asserts `SystemExit` and `open_db.assert_not_called()`. The ordering test records literal events and expects:

  ```python
  ["open:wipe", "drop", "commit:wipe", "close:wipe",
   "migrate:postgresql://candidate", "open:seed",
   "seed:02_catalog.sql", "commit:seed"]
  ```

  It also asserts the returned object is the seed connection and the placeholder is `%s`. The `ACTIVE_DSN` test injects fake `alembic.command` and `alembic.config` modules, makes `upgrade()` raise `RuntimeError("upgrade failed")`, then asserts `connect.ACTIVE_DSN is None`.

- [ ] **Step 2: Verify RED**

  Run:

  ```powershell
  python -m unittest tests.test_connect_migrations -v
  ```

  Expected: the missing-catalog test fails because `open_db()` is called before the catalog check; the remaining characterization tests pass or expose a concrete contract defect.

- [ ] **Step 3: Implement the minimal safety fix**

  Resolve `catalog = DB_DIR / "02_catalog.sql"` and raise the existing `SystemExit` before the first `open_db(dsn)` call. Keep `DROP SCHEMA`, `apply_migrations(dsn)`, catalog execution, return signature and `ACTIVE_DSN` semantics unchanged.

  Correct `db/migrations/env.py` prose so it says baseline SQL executes through the raw DBAPI cursor and points to `db/migrations/README.md`.

- [ ] **Step 4: Verify GREEN and regression suite**

  ```powershell
  python -m unittest tests.test_connect_migrations -v
  node --test tests/*.test.js
  git diff --check
  ```

  Expected: all Python tests pass; 17 existing Node tests pass; no warnings/errors.

- [ ] **Step 5: Commit**

  ```powershell
  git add tests/test_connect_migrations.py db/connect.py db/migrations/env.py
  git commit -m "test(schema-migration): guard rebuild ordering"
  ```

---

### Task 3: Remove the duplicate schema source and repair live documentation

**Files:**
- Delete: `db/01_schema.sql`
- Delete: `db/migrations/README`
- Create: `db/migrations/README.md`
- Modify: `README.md`
- Modify: `backend/store.py`
- Modify: `db/connect.py`
- Modify: `db/load_org.py`
- Modify: `scripts/audit_db.py`
- Modify: `web/js/app.js`
- Modify: `tools/kiem_so_qua_api_js.js`
- Modify: `docs/reference/cay-thu-muc.md`
- Modify: `docs/reference/dong-bo-may-dong-nghiep-20-08.md`
- Modify: `docs/reference/huong-dan-cap-nhat-dashboard.md`
- Modify: `docs/reference/mo-ta-database.md`
- Modify: `docs/reference/toan-trinh-du-lieu.md`
- Modify: `docs/reference/tu-dien-database.md`
- Modify or move: `docs/reference/viec-can-lam-truoc-api-gateway.md`

**Interfaces:**
- Consumes: immutable baseline migration and the live-reference classification in Task 1.
- Produces: one schema source and current operating documentation that points to Alembic.

- [ ] **Step 1: Capture immutable hashes before cleanup**

  ```powershell
  Get-FileHash db/migrations/sql/001_baseline.sql -Algorithm SHA256
  Get-FileHash db/migrations/versions/001_baseline_baseline.py -Algorithm SHA256
  ```

  Save the two hashes in the implementer report; they must match after the task.

- [ ] **Step 2: Remove only obsolete live artifacts**

  Delete `db/01_schema.sql`. Replace the generated one-line `db/migrations/README` with `README.md`; do not leave both names.

- [ ] **Step 3: Write the migration runbook**

  `db/migrations/README.md` must document:

  - add a new Python revision plus SQL file; never edit an applied revision;
  - forward-only removal via another upgrade revision;
  - no `--autogenerate`, because this SQL-first project relies on hand-written views;
  - raw DBAPI cursor execution without an empty second argument, preserving `%` in SQL/comments;
  - catalog seed stays in `02_catalog.sql` and is loaded only by rebuild;
  - `alembic upgrade head` is in-place; `rebuild()` deliberately wipes;
  - DSN comes from `connect.DEFAULT_DSN`; never restore `sqlalchemy.url`.

- [ ] **Step 4: Update live references**

  Replace operational locators with `db/migrations/sql/001_baseline.sql` or the migration README. Preserve immutable migration provenance, OpenSpec history, archive files, decisions and dated journals. If `viec-can-lam-truoc-api-gateway.md` is intentionally a 20/08 snapshot, move it to `docs/archive/`; otherwise update every live locator.

- [ ] **Step 5: Verify references and immutable files**

  ```powershell
  rg -n -S "01_schema|copy_to_postgres" README.md backend db scripts tools web docs/reference
  git diff --exit-code ae8d9b3 -- db/migrations/sql/001_baseline.sql db/migrations/versions/001_baseline_baseline.py
  node --test tests/*.test.js
  python -m unittest discover -s tests -p "test_*.py" -v
  git diff --check
  ```

  Expected: remaining matches are explanatory history/provenance, not live pointers; immutable migration diff is empty; all tests pass.

- [ ] **Step 6: Commit**

  ```powershell
  git add -A
  git commit -m "docs(schema-migration): make migrations the schema source"
  ```

---

### Task 4: Make acceptance tools portable and non-polluting with TDD

**Files:**
- Create: `tests/dashboard-harness-path.test.js`
- Create: `tests/test_acceptance_safety.py`
- Modify: `tools/chay_dashboard_trong_node.js`
- Modify: `backend/check_api.py`
- Modify: `scripts/audit_db.py`
- Modify: `openspec/changes/change-the-schema-without-dropping-it/tasks.md`

**Interfaces:**
- Consumes: `node tools/chay_dashboard_trong_node.js`, backend read-only connection, `audit_db.py --db`.
- Produces: a cwd-independent dashboard harness, a rollback-only write probe, and DB-enforced read-only audit sessions.

- [ ] **Step 1: Write the failing dashboard portability test**

  Spawn the harness from a temporary/arbitrary cwd with `--check-files` and expect exit 0 plus a line containing the resolved repository root. The current script must fail because it hard-codes `D:/RangDonk/token-ledger-dashboard` and has no preflight option.

  ```javascript
  test('dashboard harness resolves project files from its own location', () => {
    const result = spawnSync(process.execPath,
      [HARNESS, '--check-files'], { cwd: os.tmpdir(), encoding: 'utf8' });
    assert.equal(result.status, 0, result.stderr || result.stdout);
    assert.match(result.stdout, /web[\\/]index\.html/);
  });
  ```

- [ ] **Step 2: Write failing Python safety tests**

  Use fake connections to prove:

  - when a write probe unexpectedly succeeds, `check_api.read_only()` rolls back and reports failure without committing;
  - when PostgreSQL rejects the probe, it rolls back the aborted transaction and reports success;
  - `audit_db.open_read_only()` calls `set_session(readonly=True)` before yielding the connection.

- [ ] **Step 3: Verify RED**

  ```powershell
  node --test tests/dashboard-harness-path.test.js
  python -m unittest tests.test_acceptance_safety -v
  ```

  Expected: hard-coded root/preflight and commit/no-session behavior make the tests fail for the intended reasons.

- [ ] **Step 4: Implement minimal fixes**

  - Set `ROOT = path.resolve(__dirname, "..")` and add `--check-files`, which verifies the three required files then exits before network activity.
  - In `check_api.read_only()`, never commit the probe. Always rollback in success and exception branches; use a temporary probe table so an unexpected writable connection cannot leave a persistent artifact.
  - In `audit_db.open_read_only()`, call `cn.set_session(readonly=True)` before issuing checks.
  - Correct task 8.5 to use `node`, not `python`.

- [ ] **Step 5: Verify GREEN and full local suite**

  ```powershell
  node --test tests/*.test.js
  python -m unittest discover -s tests -p "test_*.py" -v
  git diff --check
  ```

- [ ] **Step 6: Commit**

  ```powershell
  git add tests tools/chay_dashboard_trong_node.js backend/check_api.py scripts/audit_db.py openspec/changes/change-the-schema-without-dropping-it/tasks.md
  git commit -m "test(schema-migration): harden acceptance tools"
  ```

---

### Task 5: Add the forward-only rehearsal migrations with TDD

**Files:**
- Create: `db/migrations/sql/002_rehearse_in_place.sql`
- Create: `db/migrations/sql/003_remove_rehearsal.sql`
- Create: `db/migrations/versions/002_rehearse_in_place.py`
- Create: `db/migrations/versions/003_remove_rehearsal.py`
- Create: `tests/test_rehearsal_migrations.py`
- Modify: `openspec/changes/change-the-schema-without-dropping-it/tasks.md`

**Interfaces:**
- Consumes: revision `001_baseline` and the raw-DBAPI execution convention.
- Produces: linear revisions `001_baseline -> 002_rehearse_in_place -> 003_remove_rehearsal`.

- [ ] **Step 1: Write failing migration contract tests**

  Load each revision module with a fake Alembic `op` boundary. Assert exact revision linkage, that `upgrade()` executes its UTF-8 SQL with no parameter tuple, and that both `downgrade()` functions raise `NotImplementedError` directing the caller to a forward migration.

- [ ] **Step 2: Verify RED**

  ```powershell
  python -m unittest tests.test_rehearsal_migrations -v
  ```

  Expected: imports fail because revisions 002/003 do not exist.

- [ ] **Step 3: Add minimal forward revisions**

  `002_rehearse_in_place.sql`:

  ```sql
  -- Dien tap migration tai cho: cot nullable nay khong mang nghia nghiep vu.
  ALTER TABLE account ADD COLUMN migration_rehearsal_marker TEXT NULL;
  ```

  `003_remove_rehearsal.sql`:

  ```sql
  -- Go cot dien tap bang mot migration TIEN, khong dung downgrade.
  ALTER TABLE account DROP COLUMN migration_rehearsal_marker;
  ```

  Use English filenames/revision identifiers despite the old task wording; update task 8.6 accordingly. Each Python revision reads its adjacent SQL file, executes through the DBAPI cursor without a second parameter, and rejects downgrade.

- [ ] **Step 4: Verify GREEN**

  ```powershell
  python -m unittest tests.test_rehearsal_migrations -v
  python -m unittest discover -s tests -p "test_*.py" -v
  git diff --check
  ```

- [ ] **Step 5: Commit**

  ```powershell
  git add db/migrations tests/test_rehearsal_migrations.py openspec/changes/change-the-schema-without-dropping-it/tasks.md
  git commit -m "feat(schema-migration): add forward rehearsal revisions"
  ```

---

### Task 6: Prove the candidate database before cutover

**Files:**
- Runtime artifact only: `.superpowers/sdd/2026-08-24-complete-schema-migration-change/baseline-live.json`
- Modify after evidence: `openspec/changes/change-the-schema-without-dropping-it/tasks.md`

**Interfaces:**
- Consumes: accessible PostgreSQL databases `token_ledger` and `token_ledger_v2`, revisions 001–003, acceptance tools.
- Produces: fresh evidence for tasks 8.1–8.6 while the old database remains intact.

- [ ] **Step 1: Prepare the Python environment**

  ```powershell
  python -m venv .venv
  .venv\Scripts\python.exe -m pip install -r backend/requirements.txt
  .venv\Scripts\python.exe -c "import alembic, psycopg2, sqlalchemy; print(alembic.__version__, psycopg2.__version__, sqlalchemy.__version__)"
  ```

  Record exact versions. Do not modify dependency constraints merely to match the environment.

- [ ] **Step 2: Require live connectivity and capture the old database**

  Verify port 5432, both database names, active connections and free space using read-only queries. Then:

  ```powershell
  .venv\Scripts\python.exe tools/baseline_db.py --db $OLD_DSN --save .superpowers/sdd/2026-08-24-complete-schema-migration-change/baseline-live.json
  .venv\Scripts\python.exe tools/baseline_db.py --db $V2_DSN --compare .superpowers/sdd/2026-08-24-complete-schema-migration-change/baseline-live.json
  ```

  Expected: 23/23 match, exit 0.

- [ ] **Step 3: Run acceptance on an explicitly named scratch database**

  Create `token_ledger_acceptance_20260824` only after asserting it does not exist. Run `alembic -x db=$SCRATCH_DSN upgrade head`, `scripts/rebuild_db.py --db $SCRATCH_DSN`, baseline comparison, audit and API/dashboard checks. Never use the default DSN for scratch operations. Drop only the exact scratch name after evidence is saved.

- [ ] **Step 4: Rehearse in-place migration on v2**

  ```powershell
  .venv\Scripts\alembic.exe -x "db=$V2_DSN" upgrade 002_rehearse_in_place
  .venv\Scripts\python.exe tools/baseline_db.py --db $V2_DSN --compare .superpowers/sdd/2026-08-24-complete-schema-migration-change/baseline-live.json
  .venv\Scripts\alembic.exe -x "db=$V2_DSN" upgrade head
  .venv\Scripts\python.exe tools/baseline_db.py --db $V2_DSN --compare .superpowers/sdd/2026-08-24-complete-schema-migration-change/baseline-live.json
  ```

  Expected: both comparisons 23/23, head is `003_remove_rehearsal`, and `account.migration_rehearsal_marker` is absent after 003.

- [ ] **Step 5: Run full candidate acceptance**

  Run `audit_db.py`, start uvicorn hidden against v2 with a one-time `DASHBOARD_KEY`, then run `check_api.py`, `node tools/chay_dashboard_trong_node.js`, and `node --test tests/*.test.js`. Stop uvicorn by captured PID in `finally`-equivalent cleanup.

  Expected historical floors: audit 36 checks / 0 failures, API 19/19, dashboard exit 0, Node tests all pass.

- [ ] **Step 6: Mark only evidence-backed tasks and commit**

  Update 6.3 and 8.1–8.6 with exact commands, versions, counts and timestamps. Do not mark 6.4–6.7.

  ```powershell
  git add openspec/changes/change-the-schema-without-dropping-it/tasks.md
  git commit -m "test(schema-migration): prove in-place upgrade on v2"
  ```

---

### Task 7: Cut over the live database with independent preflight review

**Files:**
- Modify after successful cutover: `db/connect.py`
- Modify: `README.md`
- Modify: live operating docs that still instruct `_v2`
- Modify: `openspec/changes/change-the-schema-without-dropping-it/tasks.md`

**Interfaces:**
- Consumes: Task 6 evidence and user authorization to drop the old database.
- Produces: database `token_ledger` at revision `003_remove_rehearsal`, same 23-key baseline, and no runtime dependency on `_v2`.

- [ ] **Step 1: Generate a preflight package and request independent review**

  Package exact read-only evidence: both database names, revisions, 23/23 comparisons, active sessions, candidate audit/API/dashboard results, proposed SQL and backup name. Reviewer must return no Critical/Important finding before execution.

- [ ] **Step 2: Stop clients and create a recoverable backup**

  Stop backend, pgAdmin and scripts. From the `postgres` maintenance database, assert `token_ledger_pre_cutover_20260824` does not exist, terminate only sessions whose `datname` is exactly `token_ledger`, then create:

  ```sql
  CREATE DATABASE token_ledger_pre_cutover_20260824 WITH TEMPLATE token_ledger;
  ```

  Compare the backup to `baseline-live.json` before proceeding.

- [ ] **Step 3: Execute the exact destructive cutover**

  Re-check there are no sessions on either target. In autocommit mode, execute exactly:

  ```sql
  DROP DATABASE token_ledger;
  ALTER DATABASE token_ledger_v2 RENAME TO token_ledger;
  ```

  Never interpolate database names from unchecked input.

- [ ] **Step 4: Return runtime configuration to the canonical name**

  Change the default `PG_DATABASE` to `token_ledger`, remove temporary v2 comments/instructions, and update live operating docs. Historical OpenSpec and immutable migrations may retain `_v2`.

- [ ] **Step 5: Verify post-cutover before commit**

  Run baseline compare, `alembic current`, audit, API, dashboard and both local test suites against the canonical default DSN. Expected: 23/23, head 003, audit/API/dashboard pass, all local tests pass.

- [ ] **Step 6: Mark 6.4–6.7 and commit**

  Record the backup name, exact cutover time and verification counts.

  ```powershell
  git add db/connect.py README.md docs openspec/changes/change-the-schema-without-dropping-it/tasks.md
  git commit -m "feat(schema-migration): cut over to canonical database"
  ```

---

### Task 8: Final acceptance, whole-change review, and task closure

**Files:**
- Modify: `openspec/changes/change-the-schema-without-dropping-it/tasks.md`
- Modify only if verification finds a real documentation gap: relevant live docs

**Interfaces:**
- Consumes: all prior task commits and live evidence.
- Produces: OpenSpec `all_done`, one reviewed change commit on the feature branch, and handoff options.

- [ ] **Step 1: Run the complete verification matrix fresh**

  ```powershell
  openspec.cmd instructions apply --change "change-the-schema-without-dropping-it" --json
  python -m unittest discover -s tests -p "test_*.py" -v
  node --test tests/*.test.js
  .venv\Scripts\python.exe tools/baseline_db.py --compare .superpowers/sdd/2026-08-24-complete-schema-migration-change/baseline-live.json
  .venv\Scripts\python.exe scripts/audit_db.py
  .venv\Scripts\alembic.exe current
  git diff --check
  git status --short
  ```

  Also run API/dashboard acceptance with a hidden uvicorn process and guaranteed cleanup.

- [ ] **Step 2: Re-read every OpenSpec checkbox against evidence**

  Mark a task complete only when its implementation/evidence exists. Task 1.1 must say “waived/not performed,” not claim a backup. Task 7.2 must cite its earlier commit. Ensure final progress is 44/44.

- [ ] **Step 3: Request a most-capable whole-change review**

  Review the full range from `ae8d9b3` to HEAD against proposal, spec and this plan. Fix the complete findings list in one wave, then perform one scoped re-review. Do not leave Critical/Important findings open.

- [ ] **Step 4: Verify again after review fixes**

  Re-run the full local suite and all live acceptance commands affected by the fix wave. Re-run OpenSpec instructions and require `state: "all_done"`.

- [ ] **Step 5: Squash the feature branch as required by the OpenSpec task convention**

  After all review and verification evidence is clean:

  ```powershell
  git reset --soft ae8d9b3
  git commit -m "feat: complete forward-only schema migration"
  ```

  Then verify the final commit diff and tests once more. Do not merge or push without a separate explicit choice in the finishing workflow.
