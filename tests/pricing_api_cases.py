import os
import unittest
from unittest.mock import patch
from contextlib import contextmanager
from datetime import date
from fastapi.testclient import TestClient

# Prevent backend's dotenv fallback, including unused Gateway settings.
os.environ.update(DASHBOARD_KEY='pricing-test-only', DASHBOARD_OPEN='0',
                  LITELLM_MASTER_KEY='unused-test', GATEWAY_BASE_URL='http://127.0.0.1:1', QUOTA_DISABLED='1')
from backend import main
from pricing_db_cases import PersistenceTests


class PricingCorsTests(unittest.TestCase):
    def test_schedule_put_preflight(self):
        client = TestClient(main.app)
        response = client.options('/api/pricing/sync', headers={
            'Origin': main.ALLOWED_ORIGINS[0],
            'Access-Control-Request-Method': 'PUT',
            'Access-Control-Request-Headers': 'authorization,content-type'})
        self.assertEqual(response.status_code, 200, response.text)


class PricingAPITests(PersistenceTests):
    def test_catalog_and_sync_settings_are_persisted_revision_guarded(self):
        from backend import pricing
        @contextmanager
        def connection():
            yield self.cn, '%s'
        with patch.object(pricing,'open_writer',connection), patch.object(pricing.store,'open_db',connection), patch.dict(os.environ,PRICING_WRITE_ENABLED='1'):
            client=TestClient(main.app,headers={'Authorization':'Bearer pricing-test-only'})
            rows=client.get('/api/pricing/models').json()['rows']
            self.assertEqual(rows[0]['catalog_key'],'local:1')
            self.assertIsNone(rows[0]['applied'])
            settings=dict(enabled=True,interval_hours=12,expected_revision=0)
            self.assertEqual(client.put('/api/pricing/sync',json=settings).status_code,200)
            self.assertEqual(client.put('/api/pricing/sync',json=settings).status_code,409)
            self.assertEqual(client.put('/api/pricing/sync',json=dict(settings,interval_hours=0)).status_code,422)
            self.assertEqual(client.get('/api/pricing/sync').json()['interval_hours'],12)
            self.assertEqual(client.post('/api/pricing/sync').status_code,202)
            self.assertTrue(client.get('/api/pricing/sync').json()['requested'])

    def test_http_auth_save_readback_conflict_and_reset(self):
        from backend import pricing
        @contextmanager
        def connection():
            yield self.cn, '%s'
        with patch.object(pricing,'open_writer',connection), patch.object(pricing.store,'open_db',connection), patch.dict(os.environ,PRICING_WRITE_ENABLED='1'):
            client = TestClient(main.app)
            url = '/api/pricing/versions?catalog_key=local%3A1'
            body = dict(mode='price',input_per_million='1.25',output_per_million='2',cache_read_per_million=None,
                        from_day='2026-01-01',to_day=None,reason='contract',expected_revision=0,confirm_retroactive=True)
            self.assertEqual(client.post(url,json=body).status_code,401)
            client.headers['Authorization']='Bearer pricing-test-only'
            with patch.object(main,'DASHBOARD_OPEN',True):
                self.assertEqual(client.post(url,json=body).status_code,403)
            with patch.dict(os.environ,PRICING_WRITE_ENABLED='0'):
                self.assertEqual(client.post(url,json=body).status_code,403)
            self.assertEqual(client.post(url,json=dict(body,input_per_million=True)).status_code,422)
            self.assertEqual(client.post(url,json=dict(body,confirm_retroactive=False)).status_code,409)
            saved=client.post(url,json=body)
            self.assertEqual(saved.status_code,200,saved.text)
            self.assertEqual(saved.json()['principal'],'shared_key')
            self.assertEqual(client.post(url,json=body).status_code,409)
            history=client.get('/api/pricing/history',params={'catalog_key':'local:1'}).json()['rows']
            self.assertEqual(history[0]['id'],saved.json()['id'])
            reset=dict(body,mode='auto',expected_revision=1)
            for k in ('input_per_million','output_per_million','cache_read_per_million'): reset.pop(k)
            self.assertEqual(client.post(url,json=reset).status_code,200)
            # Query key retains slash, colon, space and plus through actual HTTP.
            with self.cn.cursor() as cur:
                cur.execute("INSERT INTO ref_model_catalog(catalog_key,provider,display_name) VALUES ('or:vendor/a+b c','vendor','raw')")
            self.cn.commit()
            r=client.post('/api/pricing/versions',params={'catalog_key':'or:vendor/a+b c'},json=body)
            self.assertEqual(r.status_code,200,r.text)
            self.assertEqual(r.json()['catalog_key'],'or:vendor/a+b c')

    def test_preview_uses_same_estimator_and_is_read_only(self):
        from backend import pricing
        @contextmanager
        def connection(): yield self.cn,'%s'
        with self.cn.cursor() as cur:
            cur.execute('CREATE TABLE IF NOT EXISTS ref_price(model_id INT,effective_from DATE,price_input NUMERIC,price_output NUMERIC,price_cached NUMERIC,source TEXT)')
            cur.execute('CREATE TABLE usage_resolved(day DATE,agent_id INT,model_id INT,token_source TEXT,input_tokens BIGINT,output_tokens BIGINT,cached_tokens BIGINT)')
            cur.execute("INSERT INTO usage_resolved VALUES ('2026-09-22',1,1,'billing',1000000,0,0)")
        self.cn.commit()
        ev={(date(2026,9,22),1,1,'billing'):dict(source_rows=1,cache_missing_rows=0,text_only=True,extra_billable=False,cache_write=0)}
        with patch.object(pricing.store,'open_db',connection),patch.object(pricing,'usage_evidence',return_value=ev):
            client=TestClient(main.app,headers={'Authorization':'Bearer pricing-test-only'})
            body=dict(mode='price',from_day='2026-09-22',reason='preview',input_per_million='3',output_per_million='4')
            res=client.post('/api/pricing/preview?catalog_key=local%3A1',json=body)
            self.assertEqual(res.status_code,200,res.text)
            self.assertEqual(res.json()['rows_affected'],1)
            self.assertEqual(res.json()['new_known_subtotal'],3)
            self.assertEqual(res.json()['old_unknown_rows'],1)
            self.assertEqual(res.json()['revision'],0)
            with self.cn.cursor() as cur:
                cur.execute('SELECT count(*) FROM ref_model_price_version')
                self.assertEqual(cur.fetchone()[0],0)

if __name__ == '__main__': unittest.main()
