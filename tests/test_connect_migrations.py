import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from db import connect


class FakeCursor:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql):
        if sql != "DROP SCHEMA public CASCADE; CREATE SCHEMA public;":
            raise AssertionError(f"unexpected wipe SQL: {sql}")
        self.events.append("drop")


class FakeConnection:
    def __init__(self, name, events):
        self.name = name
        self.events = events

    def cursor(self):
        return FakeCursor(self.events)

    def commit(self):
        self.events.append(f"commit:{self.name}")

    def close(self):
        self.events.append(f"close:{self.name}")


class RebuildTests(unittest.TestCase):
    def test_missing_catalog_fails_before_opening_or_wiping_database(self):
        self.fail("CO Y LAM HONG de kiem CI co do khong -- se hoan tac ngay")
        """Moving the catalog guard below open_db() would destroy before failing."""
        events = []
        connection = FakeConnection("wipe", events)

        with tempfile.TemporaryDirectory() as empty_db_dir:
            with patch.object(connect, "DB_DIR", Path(empty_db_dir)), \
                    patch.object(connect, "open_db", return_value=(connection, "%s")) as open_db, \
                    patch.object(connect, "apply_migrations"):
                with self.assertRaises(SystemExit):
                    connect.rebuild("postgresql://candidate")

        open_db.assert_not_called()

    def test_rebuild_wipes_then_migrates_then_seeds_and_preserves_return_contract(self):
        """Removing a rebuild step or returning the wipe connection breaks callers."""
        events = []
        wipe_connection = FakeConnection("wipe", events)
        seed_connection = FakeConnection("seed", events)
        catalog = connect.DB_DIR / "02_catalog.sql"

        def open_db(dsn):
            if not events:
                events.append("open:wipe")
                return wipe_connection, "%s"
            events.append("open:seed")
            return seed_connection, "%s"

        def apply_migrations(dsn):
            events.append(f"migrate:{dsn}")

        def run_sql_file(connection, placeholder, path):
            self.assertIs(connection, seed_connection)
            self.assertEqual(placeholder, "%s")
            self.assertEqual(path, catalog)
            events.append("seed:02_catalog.sql")

        with patch.object(connect, "open_db", side_effect=open_db), \
                patch.object(connect, "apply_migrations", side_effect=apply_migrations), \
                patch.object(connect, "run_sql_file", side_effect=run_sql_file):
            result_connection, result_placeholder = connect.rebuild("postgresql://candidate")

        self.assertEqual(
            events,
            ["open:wipe", "drop", "commit:wipe", "close:wipe",
             "migrate:postgresql://candidate", "open:seed",
             "seed:02_catalog.sql", "commit:seed"],
        )
        self.assertIs(result_connection, seed_connection)
        self.assertEqual(result_placeholder, "%s")


class ApplyMigrationsTests(unittest.TestCase):
    def test_active_dsn_is_reset_when_alembic_upgrade_fails(self):
        """Omitting the finally reset leaks a candidate DSN into later migrations."""
        alembic_module = types.ModuleType("alembic")
        command_module = types.ModuleType("alembic.command")
        config_module = types.ModuleType("alembic.config")

        def upgrade(config, revision):
            self.assertEqual(connect.ACTIVE_DSN, "postgresql://candidate")
            raise RuntimeError("upgrade failed")

        class Config:
            def __init__(self, path):
                self.path = path

        command_module.upgrade = upgrade
        config_module.Config = Config
        alembic_module.command = command_module
        alembic_module.config = config_module

        with patch.dict(sys.modules, {
            "alembic": alembic_module,
            "alembic.command": command_module,
            "alembic.config": config_module,
        }):
            with self.assertRaisesRegex(RuntimeError, "upgrade failed"):
                connect.apply_migrations("postgresql://candidate")

        self.assertIsNone(connect.ACTIVE_DSN)
