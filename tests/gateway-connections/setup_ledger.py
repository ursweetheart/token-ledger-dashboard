"""Create/migrate only the explicitly named disposable ledger fixture."""
from pathlib import Path
import sys
import time
import psycopg2
from psycopg2 import sql
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from db import connect


def main():
    admin_dsn='postgresql://connection_test:isolated-test-only@127.0.0.1:55439/connection_test'
    admin=None
    for attempt in range(45):
        try:
            admin=psycopg2.connect(admin_dsn,connect_timeout=2); break
        except psycopg2.OperationalError:
            if attempt==44: raise
            time.sleep(1)
    admin.autocommit=True
    try:
        with admin.cursor() as cur:
            cur.execute('SELECT 1 FROM pg_database WHERE datname=%s',('connection_ledger_test',))
            if not cur.fetchone():
                cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier('connection_ledger_test')))
    finally:
        admin.close()
    connect.apply_migrations(admin_dsn.rsplit('/',1)[0]+'/connection_ledger_test')
    print('PASS: isolated ledger fixture is migrated')


if __name__=='__main__': main()
