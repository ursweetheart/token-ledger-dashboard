import unittest
from unittest.mock import patch

from scripts import audit_db


class FakeConnection:
    def __init__(self):
        self.session_calls = []

    def set_session(self, **kwargs):
        self.session_calls.append(kwargs)


class AcceptanceSafetyTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
