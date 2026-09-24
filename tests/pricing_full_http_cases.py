"""Opt-in real HTTP gate; only the user-approved disposable seeded database."""
import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
import psycopg2
from psycopg2.extensions import parse_dsn


@unittest.skipUnless(os.environ.get('PRICING_FULL_HTTP') == '1', 'local HTTP server required')
class FullHTTPTests(unittest.TestCase):
    def setUp(self):
        dsn = 'host=127.0.0.1 port=55439 dbname=pricing_full_test user=pricing_test'
        assert parse_dsn(dsn) == dict(host='127.0.0.1', port='55439', dbname='pricing_full_test', user='pricing_test')
        self.cn = psycopg2.connect(dsn)
        self.addCleanup(self.cn.close)
        with self.cn.cursor() as cur:
            cur.execute('SELECT host(inet_server_addr()),inet_server_port(),current_database()')
            assert cur.fetchone() == ('127.0.0.1', 55439, 'pricing_full_test')

    def request(self, endpoint, body=None, key=None, method=None):
        url = 'http://127.0.0.1:55440/api/pricing/' + endpoint
        if key:
            url += '?' + urllib.parse.urlencode({'catalog_key': key})
        request = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
            headers={'Authorization': 'Bearer pricing-test-only', 'Content-Type': 'application/json'}, method=method)
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    def test_ingestion_role_trigger_minimum_grant(self):
        with self.cn.cursor() as cur:
            cur.execute('GRANT USAGE ON SCHEMA public TO pricing_restricted_test')
            cur.execute('GRANT INSERT ON dim_model TO pricing_restricted_test')
            cur.execute('SAVEPOINT before_insert')
            cur.execute('SET LOCAL ROLE pricing_restricted_test')
            with self.assertRaises(psycopg2.errors.InsufficientPrivilege):
                cur.execute("INSERT INTO dim_model(model_id,name,family,provider) VALUES (990002,'isolated-trigger','isolated','test')")
            cur.execute('ROLLBACK TO SAVEPOINT before_insert')
            cur.execute('GRANT INSERT ON ref_model_catalog TO pricing_restricted_test')
            cur.execute('SET LOCAL ROLE pricing_restricted_test')
            cur.execute("INSERT INTO dim_model(model_id,name,family,provider) VALUES (990002,'isolated-trigger','isolated','test')")
            cur.execute('RESET ROLE')
            cur.execute("SELECT catalog_key FROM ref_model_catalog WHERE local_model_id=990002")
            self.assertEqual(cur.fetchone(), ('local:990002',))
        self.cn.rollback()  # probe grants/model do not persist

    def test_rebuild_refuses_without_changing_facts(self):
        from db.connect import rebuild
        with self.assertRaisesRegex(RuntimeError, 'pricing history'):
            rebuild('postgresql://pricing_test@127.0.0.1:55439/pricing_full_test')
        with self.cn.cursor() as cur:
            cur.execute('SELECT count(*) FROM dim_model')
            self.assertEqual(cur.fetchone(), (13,))

    def test_catalog_exposes_official_applied_price(self):
        status, data = self.request('models')
        self.assertEqual(status, 200)
        row = next(r for r in data['rows'] if r['catalog_key'] == 'local:1')
        self.assertIsNotNone(row['applied'])
        self.assertEqual(row['applied']['source'], 'official')

    def test_preview_save_conflict_reset_and_immutable_facts(self):
        with self.cn.cursor() as cur:
            cur.execute("INSERT INTO fact_billing_daily(day,agent_id,project,sku_id,sku_name,model_id,kind,quantity,cost_usd) VALUES ('2026-09-22',1,'isolated-pricing-http','isolated-input','Input text',1,'input',1000000,0.1) ON CONFLICT DO NOTHING")
            cur.execute("INSERT INTO dim_unit(unit_id,agent_id,name,is_technical,is_report_aggregate) VALUES (990001,1,'isolated HTTP',TRUE,FALSE) ON CONFLICT DO NOTHING")
            cur.execute("INSERT INTO account(account_id,username,kind,unit_id,is_shared,unit_agent_id,unit_conflict) VALUES (990001,'isolated-pricing-http','technical',990001,1,1,0) ON CONFLICT DO NOTHING")
            cur.execute("INSERT INTO fact_usage_daily(day,agent_id,model_id,account_id,total_tokens,input_tokens,output_tokens,cached_tokens,cost_usd,source) VALUES ('2026-09-22',1,1,990001,1000000,1000000,0,0,0.1,'billing') ON CONFLICT DO NOTHING")
        self.cn.commit()
        def facts():
            with self.cn.cursor() as cur:
                cur.execute('SELECT count(*),sum(quantity),sum(cost_usd) FROM fact_billing_daily')
                billing = cur.fetchone()
                cur.execute('SELECT count(*),sum(total_tokens),sum(input_tokens),sum(output_tokens),sum(cached_tokens),sum(calls),sum(cost_usd) FROM fact_usage_daily')
                usage = cur.fetchone()
                cur.execute('SELECT count(*),sum(cached_tokens),sum(cost_usd) FROM fact_call')
                return billing, usage, cur.fetchone()
        before = facts()
        body = dict(mode='price', from_day='2026-09-22', to_day='2026-09-23', reason='isolated HTTP gate',
                    input_per_million='3', output_per_million='4', confirm_retroactive=True)
        status, preview = self.request('preview', body, 'local:1')
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview['rows_affected'], 1)
        self.assertEqual(preview['new_known_subtotal'], 3)
        body['expected_revision'] = preview['revision']
        status, saved = self.request('versions', body, 'local:1')
        self.assertEqual(status, 200, saved)
        self.assertEqual(self.request('versions', body, 'local:1')[0], 409)
        self.assertEqual(self.request('history', key='local:1')[1]['rows'][0]['id'], saved['id'])
        reset = dict(mode='auto', from_day='2026-09-22', to_day='2026-09-23', reason='isolated reset', confirm_retroactive=True)
        status, preview = self.request('preview', reset, 'local:1')
        self.assertEqual(status, 200, preview)
        self.assertEqual(preview['new_known_subtotal'], 0.1)
        reset['expected_revision'] = preview['revision']
        status, saved = self.request('versions', reset, 'local:1')
        self.assertEqual(status, 200, saved)
        self.assertEqual(self.request('history', key='local:1')[1]['rows'][0]['id'], saved['id'])
        self.assertEqual(before, facts())


if __name__ == '__main__':
    unittest.main()
