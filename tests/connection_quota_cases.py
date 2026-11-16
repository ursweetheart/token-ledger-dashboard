"""Hạn mức đi qua worker: worker giữ master key, `api` chỉ chuyển lời.

Change `move-the-master-key-out-of-the-portal-backend`. Cần FastAPI + psycopg2 nên
nằm ở tệp `*_cases.py` (job connection-contracts), không ở `test_*.py`.

CÁC TẦNG, MỖI TẦNG MỘT LỚP PHÉP KIỂM:

  WorkerQuotaTests   worker gọi Gateway: thân yêu cầu gửi đi, luật 409, phân trang.
  WorkerRpcTests     thực đơn RPC: khoá worker, tập trường chặt, mã lỗi.
  RpcClientTests     người gọi RPC của `api`: worker tắt là 503, không phải "bị từ chối".
  ApiQuotaTests      ba endpoint của `api`: cùng hình dạng dữ liệu như trước, và
                     không còn đường nào khác ngoài worker.

CA QUAN TRỌNG NHẤT vẫn là `test_the_request_body_carries_the_whole_metadata`:
`/key/update` của LiteLLM THAY THẾ cả cục metadata, nên gửi thiếu `tags` là xoá
tag định danh của khoá mà mọi lượt gọi vẫn trả 200 (xem tests/test_quota_gateway.py).
"""
import io
import os
import unittest
import urllib.error
import urllib.request
from unittest import mock

# Giá trị KHÁC RỖNG để `_read_env` không rơi xuống tệp `.env` của máy đang chạy.
os.environ.update(DASHBOARD_KEY='reader-only', DASHBOARD_OPEN='0',
                  CONNECTIONS_ENABLED='0', QUOTA_DISABLED='0')
os.environ.pop('LITELLM_MASTER_KEY', None)

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend import connection_api, gateway, main  # noqa: E402
from backend.connection_config import Conflict  # noqa: E402
from backend.connection_worker import Gateway, Worker, build_app  # noqa: E402

MASTER = 'sk-master-secret'
TAGGED = {'key_alias': 'dms-feedback-tagged', 'spend': 12.5,
          'metadata': {'tags': ['dms-feedback'], 'note': 'keep me'}}
MANAGED = {'key_alias': 'connection-abc', 'spend': 3.0,
           'metadata': {'tags': ['dms-tap'], 'quota_usd': 5}}
UNTAGGED = {'key_alias': 'dms-feedback', 'spend': 0.0, 'metadata': {}}
SIBLING = {'key_alias': 'dms-feedback-drill', 'spend': 40.0,
           'metadata': {'tags': ['dms-feedback'], 'quota_usd': 40}}


class FakeGateway:
    """Đứng thay lớp `Gateway` của worker. Ghi lại MỌI lượt gọi để soi thứ tự."""

    master = MASTER

    def __init__(self, keys=(), pages=None, fail=None):
        self.keys = {k['key_alias']: k for k in keys}
        self.pages, self.fail, self.calls = pages, fail, []

    def key(self, alias):
        self.calls.append(('key', alias))
        if self.fail:
            raise self.fail
        return self.keys.get(alias)

    def call(self, path, data=None, key=None, query=None):
        self.calls.append((path, data, query))
        if self.fail:
            raise self.fail
        if path == '/key/list':
            if self.pages:
                return {}, self.pages(query['page'])
            return {}, {'keys': list(self.keys.values()), 'total_pages': 1}
        return {}, {}

    def sent(self, path):
        return [data for called, data, *_ in self.calls if called == path]


def worker_with(*keys, **kwargs):
    worker = Worker.__new__(Worker)
    # Hai instance như thật; thao tác khoá chỉ được chạm instance đầu.
    worker.gateways = [FakeGateway(keys, **kwargs), FakeGateway()]
    return worker, worker.gateways[0]


class WorkerQuotaTests(unittest.TestCase):
    def test_the_request_body_carries_the_whole_metadata(self):
        worker, gw = worker_with(TAGGED)
        worker.quota_set('dms-feedback-tagged', 50, 'dashboard')
        (sent,) = gw.sent('/key/update')
        self.assertEqual(sent['key_alias'], 'dms-feedback-tagged')
        self.assertEqual(sent['metadata']['tags'], ['dms-feedback'])
        self.assertEqual(sent['metadata']['note'], 'keep me')
        self.assertEqual(sent['metadata'][gateway.QUOTA_FIELD], 50.0)

    def test_the_log_names_who_asked(self):
        worker, gw = worker_with(TAGGED)
        result = worker.quota_set('dms-feedback-tagged', '50', 'dashboard')
        entry = result['metadata'][gateway.LOG_FIELD][-1]
        self.assertEqual((entry['from'], entry['to'], entry['by']), (None, 50.0, 'dashboard'))

    def test_an_unknown_alias_is_an_error_not_a_silent_create(self):
        worker, gw = worker_with(TAGGED)
        with self.assertRaises(KeyError):
            worker.quota_set('does-not-exist', 50, 'dashboard')
        self.assertEqual(gw.sent('/key/update'), [])

    def test_setting_a_managed_key_is_refused_before_any_gateway_call(self):
        worker, gw = worker_with(MANAGED)
        with self.assertRaises(Conflict) as caught:
            worker.quota_set('connection-abc', 50, 'dashboard')
        self.assertEqual(gw.calls, [])
        # Câu lỗi hiện thẳng ở tab Setting, nên phải chỉ đường tới tab Kết nối.
        self.assertIn('Kết nối agent', str(caught.exception))  # vi-ok: tab name shown to the user

    def test_topping_up_a_managed_key_is_refused_before_any_gateway_call(self):
        worker, gw = worker_with(MANAGED)
        with self.assertRaises(Conflict):
            worker.quota_top_up('connection-abc', 5, 'dashboard')
        self.assertEqual(gw.calls, [])

    def test_only_the_prefix_counts_not_the_word_anywhere(self):
        worker, gw = worker_with({'key_alias': 'my-connection-key', 'metadata': {}})
        worker.quota_set('my-connection-key', 10, 'dashboard')
        self.assertEqual(len(gw.sent('/key/update')), 1)

    def test_a_top_up_adds_to_what_is_there(self):
        worker, gw = worker_with(SIBLING)
        result = worker.quota_top_up('dms-feedback-drill', 10, 'dashboard')
        self.assertEqual(result['metadata'][gateway.QUOTA_FIELD], 50.0)
        self.assertEqual(result['metadata']['tags'], ['dms-feedback'])

    def test_a_top_up_with_no_budget_yet_starts_from_zero(self):
        worker, gw = worker_with(TAGGED)
        result = worker.quota_top_up('dms-feedback-tagged', 10, 'dashboard')
        self.assertEqual(result['metadata'][gateway.QUOTA_FIELD], 10.0)

    def test_a_bad_amount_never_reaches_the_gateway(self):
        for bad in (-1, 'a lot', True, None, float('inf')):
            for write in ('quota_set', 'quota_top_up'):
                worker, gw = worker_with(TAGGED)
                with self.assertRaises(ValueError, msg=f'{write}({bad!r})'):
                    getattr(worker, write)('dms-feedback-tagged', bad, 'dashboard')
                self.assertEqual(gw.sent('/key/update'), [])

    def test_a_write_needs_a_named_actor(self):
        worker, gw = worker_with(TAGGED)
        with self.assertRaises(ValueError):
            worker.quota_set('dms-feedback-tagged', 50, '')
        self.assertEqual(gw.calls, [])

    def test_only_the_first_instance_is_touched(self):
        worker, gw = worker_with(TAGGED)
        worker.quota_list()
        worker.quota_set('dms-feedback-tagged', 50, 'dashboard')
        self.assertEqual(worker.gateways[1].calls, [])

    def test_the_list_walks_every_page_and_returns_raw_keys(self):
        pages = {1: {'keys': [TAGGED, 'broken-row'], 'total_pages': 2},
                 2: {'keys': [MANAGED], 'total_pages': 2}}
        worker, gw = worker_with(pages=pages.__getitem__)
        self.assertEqual(worker.quota_list(), {'keys': [TAGGED, MANAGED]})
        queries = [q for path, _, q in gw.calls if path == '/key/list']
        self.assertEqual([q['page'] for q in queries], [1, 2])
        self.assertTrue(all(q['return_full_object'] == 'true' for q in queries))

    def test_the_list_stops_when_the_gateway_lies_about_the_page_count(self):
        worker, gw = worker_with(pages=lambda page: {'keys': [TAGGED], 'total_pages': 10**9})
        self.assertEqual(len(worker.quota_list()['keys']), 50)


class GatewayClientTests(unittest.TestCase):
    """Lớp `Gateway` của worker: lỗi không mang master key, và không có đường pass-through."""

    def setUp(self):
        self.gw = Gateway('http://gateway.invalid', MASTER)

    def failing(self, error):
        return mock.patch.object(urllib.request.OpenerDirector, 'open', side_effect=error)

    def test_an_http_error_never_carries_the_master_key(self):
        error = urllib.error.HTTPError('http://gateway.invalid/key/list', 403, MASTER, {}, None)
        with self.failing(error), self.assertRaises(RuntimeError) as caught:
            self.gw.key('dms-feedback-tagged')
        self.assertNotIn(MASTER, str(caught.exception))

    def test_an_unreachable_gateway_never_carries_the_master_key(self):
        with self.failing(urllib.error.URLError('timed out ' + MASTER)), \
                self.assertRaises(RuntimeError) as caught:
            self.gw.key('dms-feedback-tagged')
        self.assertNotIn(MASTER, str(caught.exception))

    def test_the_worker_cannot_be_talked_into_a_pass_through(self):
        # Đây là đường rò khoá Google đã chứng minh 03/11/2026. Worker giữ master
        # key nhưng lớp gọi của nó chỉ biết một danh sách đường dẫn cố định.
        with mock.patch.object(urllib.request.OpenerDirector, 'open') as opened:
            for path in ('/config/pass_through_endpoint', '/config/update', '/key/regenerate'):
                with self.assertRaises(ValueError, msg=path):
                    self.gw.call(path, {'anything': 1})
        opened.assert_not_called()


class WorkerRpcTests(unittest.TestCase):
    KEY = {'Authorization': 'Bearer worker-only'}

    def client(self, *keys, **kwargs):
        worker, gw = worker_with(*keys, **kwargs)
        return TestClient(build_app(worker, 'worker-only')), gw

    def post(self, client, action, body, headers=None):
        return client.post('/rpc/' + action, json=body, headers=self.KEY if headers is None else headers)

    def test_the_menu_needs_the_worker_key(self):
        client, gw = self.client(TAGGED)
        self.assertEqual(self.post(client, 'quota-list', {}, {}).status_code, 401)
        wrong = {'Authorization': 'Bearer reader-only'}
        self.assertEqual(self.post(client, 'quota-list', {}, wrong).status_code, 401)
        self.assertEqual(gw.calls, [])

    def test_quota_list_returns_the_raw_keys(self):
        client, gw = self.client(TAGGED, MANAGED)
        response = self.post(client, 'quota-list', {})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), {'keys': [TAGGED, MANAGED]})

    def test_quota_set_writes_and_returns_the_new_metadata(self):
        client, gw = self.client(TAGGED)
        response = self.post(client, 'quota-set',
                             {'key_alias': 'dms-feedback-tagged', 'amount': 50, 'actor': 'dashboard'})
        self.assertEqual(response.status_code, 200, response.text)
        metadata = response.json()['metadata']
        self.assertEqual(metadata[gateway.QUOTA_FIELD], 50.0)
        self.assertEqual(metadata[gateway.LOG_FIELD][-1]['by'], 'dashboard')
        self.assertEqual(gw.sent('/key/update')[0]['metadata'], metadata)

    def test_quota_top_up_adds(self):
        client, gw = self.client(SIBLING)
        response = self.post(client, 'quota-top-up',
                             {'key_alias': 'dms-feedback-drill', 'amount': 10, 'actor': 'dashboard'})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['metadata'][gateway.QUOTA_FIELD], 50.0)

    def test_a_managed_key_is_409_on_both_writes(self):
        for action in ('quota-set', 'quota-top-up'):
            client, gw = self.client(MANAGED)
            response = self.post(client, action,
                                 {'key_alias': 'connection-abc', 'amount': 50, 'actor': 'dashboard'})
            self.assertEqual(response.status_code, 409, action)
            self.assertEqual(gw.calls, [], action)

    def test_a_bad_amount_is_422_and_an_unknown_key_is_404(self):
        client, gw = self.client(TAGGED)
        body = {'key_alias': 'dms-feedback-tagged', 'amount': -1, 'actor': 'dashboard'}
        self.assertEqual(self.post(client, 'quota-set', body).status_code, 422)
        body = {'key_alias': 'does-not-exist', 'amount': 5, 'actor': 'dashboard'}
        for action in ('quota-set', 'quota-top-up'):
            response = self.post(client, action, body)
            self.assertEqual(response.status_code, 404, action)
            # Hiện nguyên văn ở tab Setting: phải nói về KHOÁ, không nói "profile" của tab Kết nối.
            self.assertIn('key', response.json()['detail'].lower())
            self.assertNotIn('profile', response.json()['detail'].lower())
        self.assertEqual(gw.sent('/key/update'), [])

    def test_the_field_sets_are_exact(self):
        client, gw = self.client(TAGGED)
        ok = {'key_alias': 'dms-feedback-tagged', 'amount': 5, 'actor': 'dashboard'}
        for action, body in (('quota-list', {'page': 1}),
                             ('quota-set', {**ok, 'metadata': {'tags': ['forged']}}),
                             ('quota-set', {'key_alias': 'dms-feedback-tagged', 'amount': 5}),
                             ('quota-top-up', {**ok, 'tags': ['forged']}),
                             ('pass-through', {'path': '/x', 'target': 'http://attacker.invalid'})):
            self.assertEqual(self.post(client, action, body).status_code, 422, (action, body))
        self.assertEqual(gw.calls, [])

    def test_a_gateway_failure_is_503_without_the_master_key(self):
        client, gw = self.client(TAGGED, fail=RuntimeError('Gateway HTTP 500 ' + MASTER))
        for action, body in (('quota-list', {}),
                             ('quota-set', {'key_alias': 'dms-feedback-tagged', 'amount': 5,
                                            'actor': 'dashboard'})):
            response = self.post(client, action, body)
            self.assertEqual(response.status_code, 503, action)
            self.assertNotIn(MASTER, response.text)


class RpcClientTests(unittest.TestCase):
    """Người gọi RPC của `api`: phân biệt "worker từ chối" với "không có worker".

    Đo 16/11/2026 trên stack thật: worker tắt mà proxy TLS của nó còn chạy thì nginx
    trả 502 kèm HTML. Bản trước chuyển nguyên thành "502 Worker rejected operation" -
    sai nghĩa, và spec đòi 503 nói rõ là cần worker.
    """

    def call(self, error):
        rpc = connection_api._make_rpc('https://connection-worker-proxy:8767', 'worker-only')
        with mock.patch.object(urllib.request.OpenerDirector, 'open', side_effect=error), \
                self.assertRaises(HTTPException) as caught:
            rpc('quota-list', {})
        return caught.exception

    def http_error(self, code, body):
        return urllib.error.HTTPError('https://connection-worker-proxy:8767/rpc/quota-list',
                                      code, 'error', {}, io.BytesIO(body))

    def test_a_dead_worker_behind_a_live_proxy_is_503(self):
        for code in (502, 504):
            error = self.call(self.http_error(code, b'<html><h1>502 Bad Gateway</h1></html>'))
            self.assertEqual(error.status_code, 503, code)
            self.assertIn('worker unavailable', error.detail.lower())

    def test_an_unreachable_worker_is_503(self):
        error = self.call(urllib.error.URLError('connection refused'))
        self.assertEqual(error.status_code, 503)

    def test_the_workers_own_refusal_keeps_its_code_and_words(self):
        error = self.call(self.http_error(409, b'{"detail": "managed key"}'))
        self.assertEqual((error.status_code, error.detail), (409, 'managed key'))

    def test_an_answer_that_is_not_the_workers_is_never_forwarded(self):
        for body in (b'{"error": "sk-leaked-upstream"}', b'["sk-leaked-upstream"]', b'sk-leaked-upstream'):
            error = self.call(self.http_error(500, body))
            self.assertEqual(error.status_code, 503, body)
            self.assertNotIn('sk-leaked-upstream', error.detail)


class ApiQuotaTests(unittest.TestCase):
    """Ba endpoint hạn mức của `api`, với worker là một hàm giả."""

    READER = {'Authorization': 'Bearer reader-only'}

    def setUp(self):
        self.calls = []
        self.keys = [TAGGED, MANAGED, UNTAGGED, SIBLING]
        self.error = None
        patches = [mock.patch.object(main, 'QUOTA_RPC', self.rpc),
                   mock.patch.object(main, 'QUOTA_DISABLED', False)]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        self.client = TestClient(main.app)

    def rpc(self, action, data):
        self.calls.append((action, data))
        if self.error:
            raise self.error
        if action == 'quota-list':
            return {'keys': self.keys}
        metadata = {gateway.QUOTA_FIELD: 50.0, 'tags': ['dms-feedback'],
                    gateway.LOG_FIELD: [{'at': 'now', 'from': None, 'to': 50.0, 'by': data['actor']}]}
        return {'key_alias': data['key_alias'], 'metadata': metadata}

    def write(self, path, body, alias='dms-feedback-tagged', headers=None):
        return self.client.post(path, params={'key_alias': alias}, json=body,
                                headers=self.READER if headers is None else headers)

    def test_the_list_keeps_the_shape_the_setting_tab_reads(self):
        response = self.client.get('/api/quota', headers=self.READER)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.calls, [('quota-list', {})])
        data = response.json()
        self.assertEqual(data['count'], 4)
        rows = {r['key_alias']: r for r in data['rows']}
        self.assertEqual(set(rows['dms-feedback-drill']),
                         {'key_alias', 'agent', 'untagged', 'quota_usd', 'spent_usd', 'ratio',
                          'blocked', 'enforceable', 'topups', 'sibling_keys'})
        drill = rows['dms-feedback-drill']
        self.assertEqual((drill['agent'], drill['quota_usd'], drill['spent_usd'], drill['ratio'],
                          drill['blocked'], drill['sibling_keys']),
                         ('dms-feedback', 40.0, 40.0, 1.0, True, 2))
        # Đếm theo TAG chứ không theo tên: khoá `dms-feedback` không mang tag nào.
        self.assertEqual((rows['dms-feedback']['untagged'], rows['dms-feedback']['sibling_keys']),
                         (True, 1))
        self.assertIsNone(rows['dms-feedback-tagged']['quota_usd'])

    def test_the_list_still_shows_managed_keys(self):
        rows = self.client.get('/api/quota', headers=self.READER).json()['rows']
        managed = next(r for r in rows if r['key_alias'] == 'connection-abc')
        self.assertEqual((managed['quota_usd'], managed['spent_usd']), (5.0, 3.0))

    def test_setting_hands_the_worker_the_amount_and_the_caller(self):
        response = self.write('/api/quota', {'quota_usd': '50', 'tags': ['forged'], 'spend': 0})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.calls, [('quota-set', {'key_alias': 'dms-feedback-tagged',
                                                     'amount': 50.0, 'actor': 'dashboard'})])
        data = response.json()
        self.assertEqual((data['key_alias'], data['quota_usd']), ('dms-feedback-tagged', 50.0))
        self.assertEqual(data['topups'][-1]['by'], 'dashboard')

    def test_topping_up_uses_its_own_rpc(self):
        response = self.write('/api/quota/top-up', {'quota_usd': 10})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.calls, [('quota-top-up', {'key_alias': 'dms-feedback-tagged',
                                                        'amount': 10.0, 'actor': 'dashboard'})])

    def test_the_workers_refusal_reaches_the_caller_as_409(self):
        self.error = HTTPException(409, 'Key này do tab Kết nối agent quản lý.')  # vi-ok: worker's own message
        for path in ('/api/quota', '/api/quota/top-up'):
            response = self.write(path, {'quota_usd': 50}, alias='connection-abc')
            self.assertEqual(response.status_code, 409, path)
            self.assertIn('Kết nối agent', response.json()['detail'])  # vi-ok: tab name shown to the user

    def test_a_worker_that_is_down_is_503_everywhere(self):
        self.error = HTTPException(503, 'Worker unavailable; inspect operation status before retrying')
        self.assertEqual(self.client.get('/api/quota', headers=self.READER).status_code, 503)
        self.assertEqual(self.write('/api/quota', {'quota_usd': 50}).status_code, 503)
        self.assertEqual(self.write('/api/quota/top-up', {'quota_usd': 50}).status_code, 503)

    def test_no_worker_configured_is_503_that_says_so(self):
        with mock.patch.object(main, 'QUOTA_RPC', None):
            responses = [self.client.get('/api/quota', headers=self.READER),
                         self.write('/api/quota', {'quota_usd': 50}),
                         self.write('/api/quota/top-up', {'quota_usd': 50})]
        for response in responses:
            self.assertEqual(response.status_code, 503)
            self.assertIn('worker', response.json()['detail'].lower())
        self.assertEqual(self.calls, [])

    def test_quota_can_still_be_switched_off(self):
        with mock.patch.object(main, 'QUOTA_DISABLED', True):
            response = self.client.get('/api/quota', headers=self.READER)
            self.assertEqual(response.status_code, 503)
            # Tắt có chủ ý thì nói là tắt, đừng bảo người ta đi bật worker.
            self.assertIn('QUOTA_DISABLED', response.json()['detail'])
            self.assertEqual(self.write('/api/quota', {'quota_usd': 50}).status_code, 503)
        self.assertEqual(self.calls, [])

    def test_a_bad_amount_is_400_before_the_worker_is_asked(self):
        for body in ({'quota_usd': -1}, {'quota_usd': 'a lot'}, {}, {'tags': ['forged']}):
            for path in ('/api/quota', '/api/quota/top-up'):
                self.assertEqual(self.write(path, body).status_code, 400, (path, body))
        self.assertEqual(self.calls, [])

    def test_every_quota_route_needs_the_dashboard_key(self):
        self.assertEqual(self.client.get('/api/quota').status_code, 401)
        for path in ('/api/quota', '/api/quota/top-up'):
            self.assertEqual(self.write(path, {'quota_usd': 50}, headers={}).status_code, 401)
            wrong = {'Authorization': 'Bearer worker-only'}
            self.assertEqual(self.write(path, {'quota_usd': 50}, headers=wrong).status_code, 401)
        self.assertEqual(self.calls, [])

    def test_the_api_started_without_a_master_key(self):
        # Tệp này đã xoá LITELLM_MASTER_KEY khỏi môi trường TRƯỚC khi nạp `main`.
        self.assertNotIn('LITELLM_MASTER_KEY', os.environ)
        self.assertFalse([name for name in vars(main) if 'MASTER' in name.upper()])
        self.assertFalse([name for name in vars(gateway) if 'master' in name.lower()])


if __name__ == '__main__':
    unittest.main()
