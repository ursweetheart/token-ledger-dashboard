"""Run only the isolated mock stack; credentials stay outside the repo."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ['LOCALAPPDATA']) / 'Temp' / 'tla-gateway-smoke-state.json'
COMPOSE = ['docker', 'compose', '-f', str(ROOT / 'compose.yaml')]

def state():
    if not STATE.exists():
        data = {'SMOKE_DB_PASSWORD': secrets.token_hex(24), 'SMOKE_MASTER_KEY': 'sk-' + secrets.token_hex(24), 'SMOKE_SALT_KEY': secrets.token_hex(24)}
        with STATE.open('x', encoding='utf-8') as f:
            json.dump(data, f)
    return json.loads(STATE.read_text(encoding='utf-8'))

def http(path, key, payload=None, user=None):
    headers = {'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'}
    if user:
        headers['X-User'] = user
    request = urllib.request.Request('http://127.0.0.1:4100' + path, headers=headers, data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        return exc.code, {}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['up', 'test', 'ps'])
    args = parser.parse_args()
    env = {**os.environ, **state()}
    if args.action in ['up', 'ps']:
        command = ['up', '-d', '--no-build', '--wait', '--wait-timeout', '180'] if args.action == 'up' else ['ps']
        raise SystemExit(subprocess.call(COMPOSE + command, env=env))
    status, created = http('/key/generate', env['SMOKE_MASTER_KEY'], {'models': ['tla-hd-mock'], 'duration': '1h', 'key_alias': 'tla-hd-smoke-' + secrets.token_hex(5), 'metadata': {'tags': ['tla-hd']}, 'max_budget': 1})
    assert status == 200 and created.get('key'), f'key generate status={status}'
    key = created['key']
    status, info = http('/key/info?key=' + urllib.parse.quote(key, safe=''), env['SMOKE_MASTER_KEY'])
    assert status == 200 and info['info']['metadata']['tags'] == ['tla-hd'], 'Key read-back failed'
    run_id = 'smoke-' + secrets.token_hex(5)
    users = [run_id + '.user-a', run_id + '.user-b', run_id + '.user-c']
    def call(user):
        status, response = http('/v1/chat/completions', key, {'model': 'tla-hd-mock', 'messages': [{'role': 'user', 'content': 'CANARY-' + run_id}], 'max_tokens': 16}, user)
        assert status == 200, f'completion status={status}'
        assert response['choices'][0]['message']['content'] == 'gateway-smoke-ok'
        return {'user': user, 'response_id': response['id'], 'usage': response['usage']}
    with ThreadPoolExecutor(max_workers=3) as pool:
        calls = list(pool.map(call, users))
    bad_status, _ = http('/v1/chat/completions', 'sk-invalid-smoke', {'model': 'tla-hd-mock', 'messages': [{'role': 'user', 'content': 'auth-test'}], 'max_tokens': 1})
    assert bad_status in (401, 403), f'invalid key accepted: {bad_status}'
    sql = f'''SELECT COALESCE(json_agg(t), '[]'::json) FROM (SELECT request_id, end_user, total_tokens, prompt_tokens, completion_tokens, request_tags, model, status, (messages::text LIKE '%CANARY-%' OR response::text LIKE '%CANARY-%' OR proxy_server_request::text LIKE '%CANARY-%') AS canary_leaked FROM "LiteLLM_SpendLogs" WHERE end_user LIKE '{run_id}%') t;'''
    rows = []
    for _ in range(60):
        result = subprocess.run(COMPOSE + ['exec', '-T', 'db', 'psql', '-U', 'smoke', '-d', 'litellm_smoke', '-tAc', sql], env=env, capture_output=True, text=True)
        assert result.returncode == 0, 'SpendLogs query failed'
        rows = json.loads(result.stdout)
        if len(rows) >= len(calls):
            break
        time.sleep(2)
    assert len(rows) == len(calls), f'Expected {len(calls)} logs, got {len(rows)}'
    for call in calls:
        matches = [row for row in rows if row['end_user'] == call['user']]
        assert len(matches) == 1, 'Identity mismatch or duplicate'
        row = matches[0]
        assert row['request_id'] == call['response_id'], 'ID mismatch'
        assert row['total_tokens'] == call['usage']['total_tokens'], 'Usage mismatch'
        assert 'tla-hd' in row['request_tags'], 'Missing agent tag'
        assert not row['canary_leaked'], 'Prompt redaction failed'
    report = {'result': 'PASS', 'scope': 'single_proxy_mock_not_law_insight_or_ledger', 'run_id': run_id, 'invalid_key_status': bad_status, 'calls': calls, 'spend_logs': rows}
    (ROOT / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
