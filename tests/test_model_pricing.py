"""Pricing contracts; synthetic evidence is explicit, never inferred from SUM."""
import unittest
from datetime import date
from decimal import Decimal
from db import model_pricing as p


class SelectorTests(unittest.TestCase):
    def test_both_store_read_paths_use_shared_estimator(self):
        from backend import store, pricing
        from unittest.mock import patch
        base=dict(day=date(2026,9,22),model_id=1,agent_id=1,cost_usd=0,token_estimated=False)
        with patch.object(store,'_rows',side_effect=lambda *a,**k:[dict(base)]),patch.object(pricing,'attach_estimates',side_effect=lambda cn,rows,*a: [r.update(estimated_cost_usd=7) or r for r in rows]) as attach:
            self.assertEqual(store.usage(None,'%s','2026-09-22','2026-09-22')[0]['estimated_cost_usd'],7)
            self.assertEqual(store.usage_by_account(None,'%s','2026-09-22','2026-09-22')[0]['estimated_cost_usd'],7)
            self.assertEqual(attach.call_count,2)

    def test_manual_reset_and_invalid_snapshot_block_old_price(self):
        day = date(2026, 9, 22)
        auto = dict(id=1, source='openrouter', mode='price', valid_from=day,
                    valid_to=None, status='valid', pricing={'input':'1','output':'2'})
        manual = dict(auto, id=2, source='manual')
        missing = dict(auto, id=3, status='missing', pricing={})
        self.assertEqual(p.select_price([auto, manual, missing], day), manual)
        reset = dict(manual, id=4, mode='auto', valid_to=date(2026, 9, 23))
        self.assertEqual(p.select_price([auto, manual, missing, reset], day), missing)
        self.assertEqual(p.select_price([auto, manual, missing, reset], date(2026,9,23)), manual)
        self.assertIsNone(p.select_price([auto], date(2026,9,21)))

    def test_rates_and_exact_identity(self):
        for bad in [True, -1, '-1', 'NaN', 'Infinity', '1e999', '1e-999', '', 0.1]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                p.parse_rate(bad)
        self.assertEqual(p.parse_rate('0'), Decimal(0))
        ids = {'google/gemini-3-flash-preview', 'google/gemini-embedding-001'}
        self.assertIsNone(p.match_model('gemini-3-flash', ids, {}))
        self.assertIsNone(p.match_model('google/gemini-3-flash-preview:free', ids, {}))
        self.assertEqual(p.match_model('gemini/gemini-3-flash-preview', ids, {}), 'google/gemini-3-flash-preview')
        self.assertEqual(p.match_model('gemini-embedding-1.0', ids,
                         {'gemini-embedding-1.0': ['google/gemini-embedding-001']}), 'google/gemini-embedding-001')
        self.assertIsNone(p.match_model('collision', ids, {'collision': list(ids)}))

    def test_usage_evidence_cache_and_recorded_cost(self):
        rates = {'input':'1','output':'2','cache_read':'0.5'}
        usage = dict(input=1000000, output=0, cache_read=2000000, cache_write=0,
                     input_includes_cache=False, cache_coverage=True,
                     text_only_evidence=True, extra_billable_evidence=False)
        self.assertEqual(p.estimate_text(usage, rates), (Decimal('2'), 'estimated'))
        self.assertEqual(p.estimate_text(dict(usage,input_includes_cache=True), rates)[1], 'invalid_usage')
        for key in ('cache_coverage','text_only_evidence','extra_billable_evidence','input_includes_cache'):
            self.assertIsNone(p.estimate_text(dict(usage, **{key:None}), rates)[0])
        self.assertIsNone(p.estimate_text(dict(usage,cache_read=None), rates)[0])
        self.assertEqual(p.estimate_text(dict(usage,cache_write=1), rates)[1], 'unsupported')
        self.assertEqual(p.estimate_text(usage,dict(rates,cache_read=None))[1], 'missing_rate')


class CatalogTests(unittest.TestCase):
    def test_adapter_preserves_unknown_and_billing_exclusive_cache(self):
        row=dict(input_tokens=100,output_tokens=20,cached_tokens=150,token_source='billing',cost_usd=0)
        evidence=dict(cache_missing_rows=0,source_rows=3,text_only=True,extra_billable=False,cache_write=0)
        adapted=p.adapt_usage(row,evidence)
        self.assertFalse(adapted['input_includes_cache'])
        self.assertEqual(p.estimate_text(adapted,{'input':'1','output':'2','cache_read':'1'})[0],Decimal('0.00029'))
        mixed=p.adapt_usage(dict(row,token_source='gateway'),dict(evidence,cache_missing_rows=1))
        self.assertEqual(p.estimate_text(mixed,{'input':'1','output':'2'})[1],'incomplete')
        self.assertIsNone(p.estimate_text(p.adapt_usage(dict(row,token_source='monitoring'),{}),{})[0])
        self.assertEqual(p.estimate_text(p.adapt_usage(row,dict(evidence,text_only=None)),{})[1],'unsupported')
        self.assertEqual(row['cost_usd'],0)

    def test_normalizes_both_catalogs_without_erasing_bad_prices(self):
        raw = {'id':'google/gemini-embedding-001', 'name':'Embedding',
               'pricing':{'prompt':'0.00000015','completion':'0'},
               'architecture':{'input_modalities':['text'], 'output_modalities':['embeddings']}}
        rows = p.parse_catalogs({'data':[raw]}, {'data':[dict(raw,id='google/gemini-embedding-2')]})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['pricing']['input'], '0.15000000')
        self.assertEqual(rows[0]['status'], 'valid')
        self.assertEqual(rows[0]['metadata'], raw)
        missing = p.parse_catalogs({'data':[dict(raw,pricing={})]}, {'data':[]})
        self.assertEqual(missing[0]['status'], 'missing')
        unsupported = p.parse_catalogs({'data':[dict(raw,pricing=dict(raw['pricing'],request='1'))]}, {'data':[]})
        self.assertEqual(unsupported[0]['status'], 'unsupported')
        for payload in ({}, {'data':None}, {'data':[raw,raw]}):
            with self.assertRaises(ValueError):
                p.parse_catalogs(payload, {'data':[]})
        with self.assertRaises(ValueError):
            p.parse_catalogs({'data':[]}, {'data':[]})


if __name__ == '__main__':
    unittest.main()
