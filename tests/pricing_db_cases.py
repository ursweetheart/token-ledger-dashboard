"""Opt-in isolated PostgreSQL only: PRICING_TEST_DSN, never the live DSN."""
import os
import unittest
from pathlib import Path
from datetime import datetime, timezone, date
import psycopg2
from db import model_pricing as p


@unittest.skipUnless(os.environ.get('PRICING_TEST_DSN'), 'isolated PostgreSQL DSN required')
class PersistenceTests(unittest.TestCase):
    def setUp(self):
        from psycopg2.extensions import parse_dsn
        config = parse_dsn(os.environ['PRICING_TEST_DSN'])
        assert config.get('host') == '127.0.0.1' and config.get('port') == '55439'
        assert config.get('dbname') == 'postgres', 'disposable pricing cluster only'
        self.cn = psycopg2.connect(os.environ['PRICING_TEST_DSN'])
        self.addCleanup(self.cn.close)
        with self.cn.cursor() as cur:
            cur.execute('SELECT host(inet_server_addr()),inet_server_port(),current_database()')
            assert cur.fetchone() == ('127.0.0.1',55439,'postgres')
        with self.cn.cursor() as cur:
            cur.execute('DROP SCHEMA IF EXISTS pricing_test CASCADE; CREATE SCHEMA pricing_test; SET search_path=pricing_test')
            cur.execute('CREATE TABLE dim_model(model_id INT PRIMARY KEY, name TEXT, provider TEXT); INSERT INTO dim_model VALUES (1,\'local-only\',\'custom\')')
            cur.execute('CREATE TABLE dim_model_alias(source TEXT,raw_name TEXT,model_id INT)')
            cur.execute('CREATE TABLE IF NOT EXISTS ref_price(model_id INT,effective_from DATE,price_input NUMERIC,price_output NUMERIC,price_cached NUMERIC,source TEXT)')
            sql = Path(__file__).resolve().parents[1] / 'db/migrations/sql/013_model_catalog_pricing.sql'
            self.assertTrue(sql.exists(), 'pricing migration must exist')
            cur.execute(sql.read_text(encoding='utf-8'))
        self.cn.commit()

    def test_mapping_save_and_sync_wait_before_locking_catalog(self):
        import threading
        import time
        from contextlib import contextmanager
        from types import SimpleNamespace
        from unittest.mock import patch
        from backend import pricing
        now = datetime.now(timezone.utc)
        rows = p.parse_catalogs({'data':[{'id':'google/test','pricing':{}}]})
        p.sync_catalog(self.cn, rows, now)
        with self.cn.cursor() as cur:
            cur.execute("INSERT INTO dim_model_alias VALUES ('gateway','gemini/test',1)")
        self.cn.commit()
        router = pricing.build_router(lambda: None)
        save = next(r.endpoint for r in router.routes if r.path.endswith('/versions'))
        for operation in ('mapping', 'save', 'sync'):
            with self.subTest(operation=operation):
                other = psycopg2.connect(os.environ['PRICING_TEST_DSN'])
                self.addCleanup(other.close)
                with other.cursor() as cur:
                    cur.execute("SET search_path=pricing_test; SET statement_timeout='4s'")
                other.commit()
                @contextmanager
                def writer():
                    with other:
                        yield other, '%s'
                with self.cn.cursor() as cur:
                    cur.execute("SELECT revision FROM ref_model_catalog WHERE catalog_key='local:1'")
                    revision = cur.fetchone()[0]
                self.cn.commit()
                errors = []
                def run():
                    try:
                        if operation == 'mapping': p.link_model(other,1,'google/test',True)
                        elif operation == 'sync': p.sync_catalog(other,rows,now)
                        else:
                            save(dict(mode='price',from_day='2099-01-01',reason='race',
                                      expected_revision=revision,input_per_million='1',output_per_million='1'),
                                 'local:1',SimpleNamespace(kind='shared_key'))
                        other.commit()
                    except Exception as exc:
                        other.rollback()
                        errors.append(exc)
                with self.cn.cursor() as cur:
                    cur.execute('SELECT singleton FROM ref_price_sync_state FOR UPDATE')
                with patch.object(pricing,'open_writer',writer):
                    thread = threading.Thread(target=run)
                    thread.start()
                    try:
                        deadline = time.monotonic()+2
                        while time.monotonic()<deadline:
                            with self.cn.cursor() as cur:
                                cur.execute('SELECT wait_event_type FROM pg_stat_activity WHERE pid=%s',(other.get_backend_pid(),))
                                if cur.fetchone()[0]=='Lock': break
                            time.sleep(.01)
                        else: self.fail('concurrent writer did not wait on state lock')
                        with self.cn.cursor() as cur:
                            cur.execute('SAVEPOINT probe')
                            try:
                                cur.execute('SELECT catalog_key FROM ref_model_catalog ORDER BY catalog_key FOR UPDATE NOWAIT')
                            except psycopg2.errors.LockNotAvailable:
                                cur.execute('ROLLBACK TO SAVEPOINT probe')
                                self.fail('writer locked catalog before sync state: deadlock order')
                    finally:
                        self.cn.rollback()
                        thread.join(5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                # Restore independent starting catalog/revision for the next writer.
                if operation == 'mapping':
                    with self.cn.cursor() as cur:
                        cur.execute("UPDATE ref_model_catalog SET openrouter_id=NULL,revision=0 WHERE catalog_key='local:1'")
                    p.sync_catalog(self.cn,rows,now)
                    self.cn.commit()

    def test_evidence_keeps_account_and_source_boundaries(self):
        from backend.pricing import usage_evidence
        with self.cn.cursor() as cur:
            cur.execute('CREATE TABLE fact_call(ts_local timestamp,agent_id int,model_id int,account_id int,source text,cached_tokens int,prompt_tokens int,completion_tokens int,cache_hit boolean,outcome text)')
            cur.execute('CREATE TABLE fact_app_daily(day date,agent_id int,model_id int,account_id int,prompt_tokens int,completion_tokens int)')
            cur.execute('CREATE TABLE fact_billing_daily(day date,agent_id int,model_id int,sku_name text,sku_id text,quantity int,kind text)')
            cur.execute('CREATE TABLE account(account_id int,unit_agent_id int,kind text)')
            cur.execute("INSERT INTO fact_call VALUES ('2026-09-22',1,1,10,'app',0,10,1,TRUE,NULL),('2026-09-22',1,1,11,'app',NULL,10,1,FALSE,NULL),('2026-09-22',1,1,10,'gateway',0,10,1,FALSE,'success'),('2026-09-22',1,1,10,'gateway',NULL,NULL,NULL,FALSE,'failure')")
            cur.execute("INSERT INTO fact_app_daily VALUES ('2026-09-22',1,1,12,10,1)")
            cur.execute("INSERT INTO account VALUES(20,1,'whole_agent')")
            cur.execute("INSERT INTO fact_billing_daily VALUES ('2026-09-22',1,1,'Input text','known',10,'input'),('2026-09-22',1,1,NULL,'unknown',NULL,'output')")
        ev=usage_evidence(self.cn,'2026-09-22','2026-09-22',[1])
        day=date(2026,9,22)
        self.assertIn((day,1,1,'app',10),ev)
        self.assertEqual(ev[(day,1,1,'app',10)]['source_rows'],1)
        self.assertEqual(ev[(day,1,1,'app',12)]['cache_missing_rows'],1)
        self.assertEqual(ev[(day,1,1,'app')]['cache_missing_rows'],2)
        self.assertEqual(ev[(day,1,1,'gateway',10)]['source_rows'],1)
        self.assertFalse(ev[(day,1,1,'billing')]['text_only'])
        self.assertFalse(p.adapt_usage(dict(token_source='billing'),ev[(day,1,1,'billing')])['cache_coverage'])
        self.assertIn((day,1,1,'billing',20),ev)
        self.assertNotIn((day,1,1,'billing',10),ev)

    def test_estimates_expose_catalog_freshness_without_changing_value(self):
        from backend import pricing
        from unittest.mock import patch
        from datetime import timedelta
        now=datetime.now(timezone.utc)
        rows=p.parse_catalogs({'data':[{'id':'google/test','pricing':{'prompt':'0.000001','completion':'0'}}]})
        p.sync_catalog(self.cn,rows,now-timedelta(days=5))
        with self.cn.cursor() as cur:
            cur.execute("INSERT INTO dim_model_alias VALUES ('gateway','gemini/test',1)")
        p.link_model(self.cn,1,'google/test',True)
        self.cn.commit()
        row=dict(day=now.date(),agent_id=1,model_id=1,token_source='billing',input_tokens=1000000,output_tokens=0,cached_tokens=0)
        ev={(now.date(),1,1,'billing'):dict(source_rows=1,cache_missing_rows=0,text_only=True,extra_billable=False,cache_write=0)}
        with patch.object(pricing,'usage_evidence',return_value=ev):
            pricing.attach_estimates(self.cn,[row],now.date(),now.date())
            self.assertEqual(row['estimated_cost_usd'],1)
            self.assertTrue(row.get('estimate_stale'))
            self.assertEqual(row.get('stale_priced_rows'),1)
            self.assertEqual(row.get('price_last_verified_at'),now-timedelta(days=5))
            with self.cn.cursor() as cur:
                cur.execute('UPDATE ref_model_catalog SET price_last_verified_at=%s,available=FALSE',(now,))
            pricing.attach_estimates(self.cn,[row],now.date(),now.date())
            self.assertFalse(row['estimate_stale'])
            self.assertFalse(row['price_available'])
            self.assertEqual(row['estimated_cost_usd'],1)

    def test_new_local_model_is_editable_without_catalog_sync(self):
        with self.cn.cursor() as cur:
            cur.execute("INSERT INTO dim_model VALUES (2,'new-local','custom')")
            cur.execute('SELECT catalog_key FROM ref_model_catalog WHERE local_model_id=2')
            self.assertEqual(cur.fetchone(), ('local:2',))

    def test_snapshot_history_preserves_manual_and_invalidates_missing(self):
        now = datetime(2026,9,22,10,tzinfo=timezone.utc)
        raw = {'id':'google/test','pricing':{'prompt':'0.000001','completion':'0.000002'}}
        rows = p.parse_catalogs({'data':[raw]}, {'data':[]})
        p.sync_catalog(self.cn, rows, now)
        self.cn.commit()
        with self.cn.cursor() as cur:
            cur.execute("SELECT valid_from FROM ref_model_price_version")
            self.assertEqual(cur.fetchone()[0], date(2026,9,23))
            cur.execute("INSERT INTO ref_model_price_version(catalog_key,source,mode,valid_from,pricing,status,principal,reason) VALUES ('or:google/test','manual','price','2026-09-22','{}','valid','shared_key','test') RETURNING id")
            manual_id = cur.fetchone()[0]
        self.cn.commit()
        p.sync_catalog(self.cn, rows, now)
        self.cn.commit()
        with self.cn.cursor() as cur:
            cur.execute('SELECT count(*) FROM ref_model_price_version')
            self.assertEqual(cur.fetchone()[0], 2)
        missing = p.parse_catalogs({'data':[dict(raw,pricing={})]}, {'data':[]})
        p.sync_catalog(self.cn, missing, now)
        self.cn.commit()
        with self.cn.cursor() as cur:
            cur.execute('SELECT source FROM ref_model_price_version WHERE id=%s',(manual_id,))
            self.assertEqual(cur.fetchone()[0], 'manual')
            cur.execute("SELECT status FROM ref_model_price_version WHERE source='openrouter' ORDER BY id DESC LIMIT 1")
            self.assertEqual(cur.fetchone()[0], 'missing')
            cur.execute('SELECT count(*) FROM dim_model')
            self.assertEqual(cur.fetchone()[0],1)
            cur.execute('SELECT enabled,interval_hours FROM ref_price_sync_state')
            self.assertEqual(cur.fetchone(),(False,24))

    def test_worker_disabled_queue_lease_and_failure_preserve_data(self):
        from scripts.sync_model_catalog import run_if_due
        from unittest.mock import Mock
        now=datetime(2026,9,22,10,tzinfo=timezone.utc)
        fetch=Mock(return_value=p.parse_catalogs({'data':[{'id':'v/test','pricing':{}}]}))
        self.assertEqual(run_if_due(self.cn,now,fetch),'disabled')
        fetch.assert_not_called()
        with self.cn.cursor() as cur:
            cur.execute("UPDATE ref_price_sync_state SET requested=TRUE,next_due=%s",(now,))
        self.cn.commit()
        self.assertEqual(run_if_due(self.cn,now,fetch),'success')
        self.assertEqual(fetch.call_count,1)
        with self.cn.cursor() as cur:
            cur.execute('SELECT last_worker_seen,last_success,requested,lease_token FROM ref_price_sync_state')
            self.assertEqual(cur.fetchone(),(now,now,False,None))
            cur.execute("UPDATE ref_price_sync_state SET requested=TRUE,next_due=%s,lease_token='other',lease_until=%s + interval '5 minutes'",(now,now))
        self.cn.commit()
        self.assertEqual(run_if_due(self.cn,now,fetch),'leased')
        self.assertEqual(fetch.call_count,1)
        with self.cn.cursor() as cur: cur.execute('UPDATE ref_price_sync_state SET lease_until=NULL')
        self.cn.commit()
        self.assertEqual(run_if_due(self.cn,now,Mock(side_effect=TimeoutError('secret not logged'))),'failed')
        with self.cn.cursor() as cur:
            cur.execute('SELECT last_error_class FROM ref_price_sync_state')
            self.assertEqual(cur.fetchone()[0],'TimeoutError')
            cur.execute('SELECT count(*) FROM ref_model_price_version')
            self.assertEqual(cur.fetchone()[0],1)

    def test_on_read_estimate_uses_dates_and_preserves_recorded_zero(self):
        from backend import pricing
        from unittest.mock import patch
        row=dict(day=date(2026,9,22),agent_id=1,model_id=1,token_source='billing',
                 input_tokens=1000000,output_tokens=0,cached_tokens=0,cost_usd=0)
        with self.cn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS ref_price(model_id INT,effective_from DATE,price_input NUMERIC,price_output NUMERIC,price_cached NUMERIC,source TEXT)')
            cur.execute("INSERT INTO ref_model_price_version(catalog_key,source,mode,valid_from,valid_to,pricing,status,principal,reason) VALUES ('local:1','manual','price','2026-09-22','2026-09-23','{\"input\":\"3\",\"output\":\"4\"}','valid','shared_key','test')")
        self.cn.commit()
        evidence={(date(2026,9,22),1,1,'billing'):dict(source_rows=1,cache_missing_rows=0,text_only=True,extra_billable=False,cache_write=0)}
        with patch.object(pricing,'usage_evidence',return_value=evidence):
            pricing.attach_estimates(self.cn,[row], '2026-09-21','2026-09-23')
            self.assertEqual(row['estimated_cost_usd'],3)
            self.assertEqual(row['estimate_source'],'manual')
            self.assertEqual(row['cost_usd'],0)
            account_row=dict(row,account_id=99)
            pricing.attach_estimates(self.cn,[account_row], '2026-09-21','2026-09-23')
            self.assertIsNone(account_row['estimated_cost_usd'], 'account must not borrow aggregate evidence')
            older=dict(row,day=date(2026,9,21))
            pricing.attach_estimates(self.cn,[older], '2026-09-21','2026-09-23')
            self.assertIsNone(older['estimated_cost_usd'])
            self.assertEqual(older['unpriced_rows'],1)

    def test_exact_link_preserves_local_manual_history(self):
        raw={'id':'google/test','pricing':{'prompt':'0.000001','completion':'0'}}
        p.sync_catalog(self.cn,p.parse_catalogs({'data':[raw]}),datetime.now(timezone.utc))
        with self.cn.cursor() as cur:
            cur.execute("INSERT INTO dim_model_alias VALUES ('gateway','gemini/test',1)")
            cur.execute("INSERT INTO ref_model_price_version(catalog_key,source,mode,valid_from,pricing,status,principal,reason) VALUES ('local:1','manual','price','2026-01-01','{}','valid','shared_key','test') RETURNING id")
            manual=cur.fetchone()[0]
        self.cn.commit()
        self.assertEqual(p.link_model(self.cn,1,'google/test',False),'local:1')
        with self.cn.cursor() as cur:
            cur.execute('SELECT count(*) FROM ref_model_catalog');self.assertEqual(cur.fetchone()[0],2)
        self.assertEqual(p.link_model(self.cn,1,'google/test',True),'local:1')
        self.cn.commit()
        with self.cn.cursor() as cur:
            cur.execute('SELECT catalog_key FROM ref_model_price_version WHERE id=%s',(manual,))
            self.assertEqual(cur.fetchone()[0],'local:1')
            cur.execute('SELECT count(*) FROM ref_model_catalog');self.assertEqual(cur.fetchone()[0],1)
            cur.execute('SELECT openrouter_id FROM ref_model_catalog');self.assertEqual(cur.fetchone()[0],'google/test')
        with self.assertRaises(ValueError): p.link_model(self.cn,1,'google/not-exact',True)

    def test_restricted_writer_and_readonly_reader_are_enforced_by_postgres(self):
        from backend import pricing,store
        from unittest.mock import patch
        with self.cn.cursor() as cur:
            cur.execute("DO $$ BEGIN IF NOT EXISTS(SELECT FROM pg_roles WHERE rolname='pricing_restricted_test') THEN CREATE ROLE pricing_restricted_test LOGIN; END IF; END $$")
            cur.execute('GRANT USAGE ON SCHEMA pricing_test TO pricing_restricted_test')
            cur.execute('GRANT SELECT ON ALL TABLES IN SCHEMA pricing_test TO pricing_restricted_test')
            cur.execute('GRANT INSERT,UPDATE ON ref_model_catalog,ref_model_price_version,ref_price_sync_state TO pricing_restricted_test')
            cur.execute('GRANT USAGE ON ALL SEQUENCES IN SCHEMA pricing_test TO pricing_restricted_test')
            cur.execute('CREATE TABLE fact_guard(value INT)')
        self.cn.commit()
        from psycopg2.extensions import parse_dsn,make_dsn
        config=parse_dsn(os.environ['PRICING_TEST_DSN']);config.update(user='pricing_restricted_test',options='-c search_path=pricing_test')
        dsn=make_dsn(**config)
        with patch.dict(os.environ,PRICING_WRITE_DSN=dsn):
            with pricing.open_writer() as (cn,_):
                with cn.cursor() as cur: cur.execute("UPDATE ref_price_sync_state SET status='verified'")
            with self.assertRaises(psycopg2.errors.InsufficientPrivilege),pricing.open_writer() as (cn,_):
                with cn.cursor() as cur: cur.execute('INSERT INTO fact_guard VALUES(1)')
        with patch.object(store,'DSN',dsn),self.assertRaises(psycopg2.errors.ReadOnlySqlTransaction),store.open_db() as (cn,_):
            with cn.cursor() as cur: cur.execute("UPDATE ref_price_sync_state SET status='bad'")

if __name__ == '__main__':
    unittest.main()
