"""Migration from 014 with existing financial history on a disposable database."""
import os
from pathlib import Path
import uuid
from urllib.parse import urlsplit
import pytest
import psycopg2
from psycopg2 import sql
from alembic import command
from alembic.config import Config
from db import gateway_registry


def test_additive_upgrade_preserves_facts_and_prices():
    dsn=os.environ.get('CONNECTION_TEST_DSN','')
    if not dsn: pytest.skip('Disposable fixture DSN required')
    parsed=urlsplit(dsn)
    assert parsed.hostname=='127.0.0.1' and parsed.port==55439 and parsed.path=='/connection_ledger_test'
    name='connection_migration_test_'+uuid.uuid4().hex[:10]
    admin=psycopg2.connect(dsn); admin.autocommit=True
    with admin.cursor() as cur: cur.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    target=dsn.rsplit('/',1)[0]+'/'+name
    try:
        config=Config(str(Path(__file__).resolve().parents[1]/'alembic.ini'))
        config.attributes['explicit_dsn']=target
        command.upgrade(config,'014_gateway_agent_registry')
        with psycopg2.connect(target) as cn:
            rows=gateway_registry.parse_config('version: 1\nagents:\n  - code: preserved\n    name: Preserved\n    user_mode: single\n    reporting_start_date: "2026-09-26"\n')
            gateway_registry.apply_config(cn,rows)
            with cn.cursor() as cur:
                cur.execute("INSERT INTO fact_call(call_id,agent_id,ts_raw,tz_confirmed,total_tokens,source,cost_usd) "
                            "SELECT 'financial-history',agent_id,'2026-09-26',true,4,'gateway',0.0000049999999999999996 "
                            "FROM dim_agent WHERE code='preserved'")
                cur.execute("INSERT INTO ref_model_catalog(catalog_key,provider,display_name) VALUES('preserved-price','Google','Preserved')")
                cur.execute("INSERT INTO ref_model_price_version(catalog_key,source,mode,valid_from,pricing,status,principal,reason) "
                            "VALUES('preserved-price','manual','price','2026-09-26','{}','missing','test','historical fixture')")
                cur.execute('SELECT row_to_json(f) FROM fact_call f'); before_fact=cur.fetchall()
                cur.execute('SELECT row_to_json(p) FROM ref_model_price_version p'); before_price=cur.fetchall()
        command.upgrade(config,'head')
        with psycopg2.connect(target) as cn:
            with cn.cursor() as cur:
                cur.execute('SELECT row_to_json(f) FROM fact_call f'); assert cur.fetchall()==before_fact
                cur.execute('SELECT row_to_json(p) FROM ref_model_price_version p'); assert cur.fetchall()==before_price
                cur.execute("SELECT has_table_privilege('connection_admin','gateway_connection_profile','UPDATE'),"
                            "has_table_privilege('connection_admin','fact_call','UPDATE')")
                assert cur.fetchone()==(True,False)
    finally:
        with admin.cursor() as cur:
            cur.execute('SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname=%s AND pid<>pg_backend_pid()',(name,))
            cur.execute(sql.SQL('DROP DATABASE {}').format(sql.Identifier(name)))
        admin.close()
