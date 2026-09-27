"""Probe only the disposable pinned-image fixture; never reads project .env."""
import json
import time
import urllib.request
import urllib.error
import uuid
import psycopg2

MASTER = 'sk-isolated-connections-test-master'


def call(path, data=None, key=MASTER, port=4401):
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}',
        data=json.dumps(data).encode() if data is not None else None,
        headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=15) as response:
        return dict(response.headers), json.load(response)


if __name__ == '__main__':
    for port in (4401, 4402):
        for attempt in range(45):
            try:
                call('/health/liveliness', port=port)
                break
            except (OSError,urllib.error.URLError):
                if attempt==44:
                    raise
                time.sleep(1)
    alias = 'probe-' + uuid.uuid4().hex
    _, issued = call('/key/generate', {'key_alias': alias, 'models': ['connection-test'],
                     'metadata': {'tags': ['test-agent'], 'quota_usd': 1}})
    key = issued['key']
    try:
        headers, response = call('/v1/chat/completions', {
            'model': 'connection-test', 'messages': [{'role': 'user', 'content': 'OK'}],
            'user': 'svc.test-agent', 'metadata': {'connection_check_id': alias}, 'max_tokens': 8}, key)
        assert response['choices'][0]['message']['content'] == 'OK'
        assert headers.get('x-litellm-model-id')=='connection-aabe2d58d5783f63053c1dad', 'Wrong-tag route selected'
        request_id = headers.get('x-litellm-call-id')
        print(json.dumps({'response_header_names': list(headers), 'request_id_present': bool(request_id)}))
        with psycopg2.connect('postgresql://connection_test:isolated-test-only@127.0.0.1:55439/connection_test') as cn:
            with cn.cursor() as cur:
                row = None
                for _ in range(25):
                    cur.execute('SELECT request_id, model, request_tags, metadata FROM "LiteLLM_SpendLogs" '
                                "WHERE metadata->>'litellm_call_id'=%s", (request_id,))
                    row = cur.fetchone()
                    if row:
                        break
                    time.sleep(1)
                assert row and 'test-agent' in row[2]
                print(json.dumps({'model': row[1], 'metadata_keys': sorted(row[3]),
                    'call_id_matches': row[0] == request_id,
                    'route_header': headers.get('x-litellm-model-id'),
                    'routing_decision_keys': list((row[3].get('routing_decision') or {}).keys()),
                    'cost_present': 'cost_breakdown' in row[3]}, default=str))
        call('/key/update', {'key_alias': alias, 'metadata': {'tags': ['test-agent'], 'quota_usd': 0}})
        try:
            call('/v1/chat/completions', {'model': 'connection-test',
                 'messages': [{'role': 'user', 'content': 'OK'}]}, key, port=4402)
            raise AssertionError('Zero-budget key was not blocked')
        except urllib.error.HTTPError as exc:
            assert exc.code == 429, exc.code
        print('PASS: key generation, tagged route, quota update and 429 on second instance')
    finally:
        call('/key/delete', {'key_aliases': [alias]})
        print('PASS: key revocation by alias')
    chat_alias='chat-' + uuid.uuid4().hex
    _,chat_key=call('/key/generate',{'key_alias':chat_alias,'models':['connection-chat'],
                    'metadata':{'tags':['test-chat'],'quota_usd':0}})
    try:
        chat_headers,chat_response=call('/v1/chat/completions',{'model':'connection-chat',
                    'messages':[{'role':'user','content':'OK'}],'max_tokens':8},chat_key['key'])
        print(json.dumps({'chat_quota_http':200,'call_id_present':bool(chat_headers.get('x-litellm-call-id')),
                          'route_id_present':bool(chat_headers.get('x-litellm-model-id')),
                          'response_id':chat_response.get('id'),
                          'finish_reason':chat_response['choices'][0]['finish_reason']}))
    finally:
        call('/key/delete',{'key_aliases':[chat_alias]})
