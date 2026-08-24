import importlib
import io
import sys
import unittest
from contextlib import redirect_stdout
from types import ModuleType
from unittest.mock import patch

from backend import store
from scripts import audit_db


class FakeConnection:
    def __init__(self, *, execute_error=None, cursor_error=None,
                 rollback_error=None):
        self.session_calls = []
        self.execute_error = execute_error
        self.cursor_error = cursor_error
        self.rollback_error = rollback_error
        self.executed = []
        self.rollback_calls = 0
        self.commit_calls = 0
        self.pending_write = False
        self.persistent_write = False

    def set_session(self, **kwargs):
        self.session_calls.append(kwargs)

    def cursor(self):
        if self.cursor_error:
            raise self.cursor_error
        return FakeCursor(self)

    def rollback(self):
        self.rollback_calls += 1
        if self.rollback_error:
            raise self.rollback_error
        self.pending_write = False

    def commit(self):
        self.commit_calls += 1
        self.persistent_write = self.pending_write


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql):
        self.connection.executed.append(sql)
        if self.connection.execute_error:
            raise self.connection.execute_error
        self.connection.pending_write = True


class FakeOpenDb:
    def __init__(self, connection=None, open_error=None):
        self.connection = connection
        self.open_error = open_error

    def __enter__(self):
        if self.open_error:
            raise self.open_error
        return self.connection, "%s"

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def load_check_api():
    fake_main = ModuleType("backend.main")
    fake_main.DASHBOARD_KEY = "test-key"
    fake_main.DASHBOARD_OPEN = False
    import_connection = FakeConnection()

    with patch.dict(sys.modules, {"backend.main": fake_main}), \
            patch.object(store, "open_db", return_value=FakeOpenDb(import_connection)), \
            patch.object(
                audit_db.connect,
                "query_one",
                return_value=("2026-01-01", "2026-08-17"),
            ):
        sys.modules.pop("backend.check_api", None)
        return importlib.import_module("backend.check_api")


check_api = load_check_api()


class AcceptanceSafetyTests(unittest.TestCase):
    def run_api_probe(self, fake_open_db):
        check = check_api.Check()
        with patch.object(
                check_api.store,
                "open_db",
                return_value=fake_open_db,
        ), redirect_stdout(io.StringIO()):
            check_api.read_only(check)
        return check

    def test_audit_connection_is_readonly_and_preserves_return_contract(self):
        connection = FakeConnection()
        dsn = "postgresql://candidate"

        with patch.object(
                audit_db.connect,
                "open_db",
                return_value=(connection, "%s"),
        ) as open_db:
            result_connection, result_placeholder = audit_db.open_read_only(dsn)

        open_db.assert_called_once_with(dsn)
        self.assertEqual(connection.session_calls, [{"readonly": True}])
        self.assertIs(result_connection, connection)
        self.assertEqual(result_placeholder, "%s")

    def test_api_probe_rolls_back_an_unexpectedly_successful_write(self):
        connection = FakeConnection()
        check = self.run_api_probe(FakeOpenDb(connection))

        self.assertEqual(connection.rollback_calls, 1)
        self.assertEqual(connection.commit_calls, 0)
        self.assertTrue(connection.executed[0].lstrip().upper().startswith(
            "CREATE TEMP TABLE "))
        self.assertFalse(connection.pending_write)
        self.assertFalse(connection.persistent_write)
        self.assertEqual(check.passed, 0)
        self.assertEqual(len(check.failures), 1)

    def test_api_probe_rolls_back_a_rejected_write_and_records_success(self):
        connection = FakeConnection(execute_error=RuntimeError("read only"))
        check = self.run_api_probe(FakeOpenDb(connection))

        self.assertEqual(connection.rollback_calls, 1)
        self.assertEqual(connection.commit_calls, 0)
        self.assertTrue(connection.executed[0].lstrip().upper().startswith(
            "CREATE TEMP TABLE "))
        self.assertEqual(check.passed, 1)
        self.assertEqual(check.failures, [])

    def test_api_probe_connection_failure_is_not_readonly_success(self):
        check = self.run_api_probe(
            FakeOpenDb(open_error=RuntimeError("offline")))

        self.assertEqual(check.passed, 0)
        self.assertEqual(len(check.failures), 1)

    def test_api_probe_cursor_failure_is_not_readonly_success(self):
        connection = FakeConnection(cursor_error=RuntimeError("no cursor"))
        check = self.run_api_probe(FakeOpenDb(connection))

        self.assertEqual(check.passed, 0)
        self.assertEqual(len(check.failures), 1)

    def test_api_probe_rollback_failure_is_not_readonly_success(self):
        connection = FakeConnection(
            execute_error=RuntimeError("read only"),
            rollback_error=RuntimeError("rollback failed"),
        )
        check = self.run_api_probe(FakeOpenDb(connection))

        self.assertEqual(connection.rollback_calls, 1)
        self.assertEqual(connection.commit_calls, 0)
        self.assertEqual(check.passed, 0)
        self.assertEqual(len(check.failures), 1)


if __name__ == "__main__":
    unittest.main()
