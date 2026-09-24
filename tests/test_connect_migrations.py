import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from db import connect


class FakeCursor:
    """Records every statement; answers the pg_tables query with preset names."""

    def __init__(self, events, tables):
        self.events = events
        self.tables = tables

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params=None):
        self.events.append(f"sql:{sql}")

    def fetchall(self):
        return [(name,) for name in self.tables]

    def fetchone(self):
        # Legacy test database has no registry yet. Integration tests exercise
        # the populated-registry refusal against real PostgreSQL.
        return (None,)


class FakeConnection:
    def __init__(self, name, events, tables=()):
        self.name = name
        self.events = events
        self.tables = list(tables)

    def cursor(self):
        return FakeCursor(self.events, self.tables)

    def commit(self):
        self.events.append(f"commit:{self.name}")

    def close(self):
        self.events.append(f"close:{self.name}")


class RebuildTests(unittest.TestCase):
    def run_rebuild(self, tables):
        events = []
        connection = FakeConnection("main", events, tables)
        catalog = connect.DB_DIR / "02_catalog.sql"

        def open_db(dsn):
            events.append("open")
            return connection, "%s"

        def apply_migrations(dsn):
            events.append(f"migrate:{dsn}")

        def run_sql_file(conn, placeholder, path):
            self.assertIs(conn, connection)
            self.assertEqual(placeholder, "%s")
            self.assertEqual(path, catalog)
            events.append("seed:02_catalog.sql")

        with patch.object(connect, "open_db", side_effect=open_db), \
                patch.object(connect, "apply_migrations", side_effect=apply_migrations), \
                patch.object(connect, "run_sql_file", side_effect=run_sql_file):
            result = connect.rebuild("postgresql://candidate")
        return events, connection, result

    def test_missing_catalog_fails_before_migrating_opening_or_emptying(self):
        """Moving the catalog guard below the migration or open_db() would change a database before failing."""
        with tempfile.TemporaryDirectory() as empty_db_dir:
            with patch.object(connect, "DB_DIR", Path(empty_db_dir)), \
                    patch.object(connect, "open_db") as open_db, \
                    patch.object(connect, "apply_migrations") as apply_migrations:
                with self.assertRaises(SystemExit):
                    connect.rebuild("postgresql://candidate")

        open_db.assert_not_called()
        apply_migrations.assert_not_called()

    def test_rebuild_migrates_then_empties_rows_then_seeds_in_one_transaction(self):
        """Dropping the schema wipes every GRANT (02/09/2026); emptying rows keeps them."""
        events, connection, (result_connection, result_placeholder) = self.run_rebuild(
            ["alembic_version", "dim_agent", "fact_call", "ref_source"])

        self.assertEqual(events[:3], ["open", "sql:SELECT to_regclass('public.gateway_agent_registry')", "close:main"])
        self.assertEqual(events[3:5], ["migrate:postgresql://candidate", "open"])
        self.assertTrue(events[5].startswith("sql:SELECT") and "pg_tables" in events[5], events[5])
        self.assertEqual(
            events[6:],
            ['sql:TRUNCATE TABLE "dim_agent", "fact_call" RESTART IDENTITY CASCADE',
             "seed:02_catalog.sql", "commit:main"],
        )
        self.assertIs(result_connection, connection)
        self.assertEqual(result_placeholder, "%s")

    def test_rebuild_never_drops_a_schema_or_database(self):
        """The spec forbids DROP SCHEMA and DROP DATABASE on the rebuild path."""
        events, _, _ = self.run_rebuild(["alembic_version", "fact_monitoring"])
        statements = [e for e in events if e.startswith("sql:")]
        self.assertTrue(statements)
        for statement in statements:
            self.assertNotIn("DROP", statement.upper())

    def test_rebuild_refuses_to_cascade_delete_pricing_history(self):
        with self.assertRaisesRegex(RuntimeError, 'pricing history'):
            self.run_rebuild(['dim_model','ref_model_catalog','ref_model_price_version','ref_price_sync_state'])

    def test_rebuild_keeps_tables_whose_rows_come_from_migrations(self):
        """Emptying alembic_version replays 001 onto existing tables; emptying ref_source loses
        the rows 001 seeded, because an existing database never re-runs 001. Measured on the
        rehearsal database 14/09/2026: load_ralli died with fact_call_source_fkey."""
        events, _, _ = self.run_rebuild(["alembic_version", "fact_call", "ref_source"])
        truncates = [e for e in events if e.startswith("sql:TRUNCATE")]
        self.assertEqual(truncates, ['sql:TRUNCATE TABLE "fact_call" RESTART IDENTITY CASCADE'])

    def test_every_table_a_migration_writes_rows_into_is_kept_on_rebuild(self):
        """A new migration that seeds another table must fail here, not on a real rebuild."""
        root = connect.DB_DIR / "migrations"
        seeded = set()
        for path in sorted(root.glob("sql/*.sql")) + sorted(root.glob("versions/*.py")):
            text = path.read_text(encoding="utf-8")
            seeded |= {name.lower() for name in
                       re.findall(r"INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.IGNORECASE)}
        # Guards the scan itself: if it stops finding the one seed we know about, it is broken.
        self.assertIn("ref_source", seeded)
        self.assertLessEqual(seeded, set(connect.KEEP_ON_REBUILD))

    def test_rebuild_on_a_database_without_data_tables_skips_truncate(self):
        """TRUNCATE with an empty table list is a syntax error in PostgreSQL."""
        for tables in ([], ["alembic_version"]):
            with self.subTest(tables=tables):
                events, _, _ = self.run_rebuild(tables)
                self.assertFalse([e for e in events if e.startswith("sql:TRUNCATE")])
                self.assertEqual(events[-2:], ["seed:02_catalog.sql", "commit:main"])


class ApplyMigrationsTests(unittest.TestCase):
    def test_explicit_dsn_is_carried_in_alembic_config_across_import_aliases(self):
        from alembic import command
        def upgrade(config, revision):
            self.assertEqual(config.attributes.get('explicit_dsn'), 'postgresql://isolated')
        with patch.object(command, 'upgrade', side_effect=upgrade):
            connect.apply_migrations('postgresql://isolated')

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
                self.attributes = {}

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
