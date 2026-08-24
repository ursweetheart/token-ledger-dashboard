# Task 4 report — portable, non-polluting acceptance tools

## Scope delivered

- The dashboard harness resolves the repository root from its own `__dirname`.
- `--check-files` reports the resolved paths for `web/index.html`,
  `web/js/api.js`, and `web/js/app.js`, then exits before the harness can make a
  backend request.
- `backend.check_api.read_only(c)` uses a temporary probe table, never commits,
  and rolls back after both a rejected write and an unexpectedly successful
  write.
- Connection-open, cursor-setup, and rollback failures record a failed `Check`;
  they do not count as evidence that the backend connection is read-only.
- The existing `audit_db.open_read_only()` behavior and test were preserved.
- OpenSpec task 8.5 now says `node tools/chay_dashboard_trong_node.js`; its
  checkbox remains unchecked.

## TDD evidence

### RED — dashboard portability

Command:

```powershell
node --test tests/dashboard-harness-path.test.js
```

Observed before production edits: exit 1, 1 test run, 0 passed, 1 failed. The
production harness raised `ENOENT` while opening the hard-coded path
`D:\RangDonk\token-ledger-dashboard\web\index.html`, so it did not satisfy the
temporary-cwd `--check-files` behavior.

### RED — API rollback safety

Command:

```powershell
python -m unittest tests.test_acceptance_safety -v
```

Observed before production edits: exit 1, 6 tests run, 5 failed, 1 passed. The
new tests observed zero rollback calls after both write outcomes, and observed
connection-open and cursor failures being counted as read-only successes. The
pre-existing audit read-only test remained green.

### Focused GREEN

Commands:

```powershell
node --test tests/dashboard-harness-path.test.js
python -m unittest tests.test_acceptance_safety -v
```

Observed after the minimal production changes and test cleanup: both commands
exited 0; Node passed 1/1 and Python passed 6/6.

## Full local validation

Commands and observed results:

- `node --test tests/*.test.js` — exit 0, 18/18 passed.
- `python -m unittest discover -s tests -p "test_*.py" -v` — exit 0, 9/9
  passed.
- `git diff --exit-code HEAD -- db/migrations/sql/001_baseline.sql
  db/migrations/versions/001_baseline_baseline.py` — exit 0, no immutable
  baseline diff.
- `Get-FileHash db/migrations/sql/001_baseline.sql -Algorithm SHA256` —
  `1B44C4BA007A0BBC772FAE61899EC161DCD13A236754F919AB806135F8ECAEBD`.
- `Get-FileHash db/migrations/versions/001_baseline_baseline.py -Algorithm
  SHA256` —
  `5EF4DBD92DB6F451D5978C28A6D7606E2CE0E7DEF970EFFD009845F84411A993`.
- `git diff --check` — exit 0, no whitespace errors. Git emitted its existing
  Windows LF-to-CRLF normalization warnings for modified tracked files.
- `openspec.cmd instructions apply --change
  "change-the-schema-without-dropping-it" --json` — state `ready`, progress
  33/44, 11 remaining; task 8.5 remains unchecked.

## Concerns and limits

- No live backend, candidate database, migration rehearsal, dashboard
  acceptance run, or other live acceptance task was executed or claimed.
- OpenSpec tasks 8.1–8.6 remain unchecked; this task supplies safer local tools
  and regression evidence only.
