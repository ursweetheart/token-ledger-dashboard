"""Exercise real Law Insight helper, isolated proxy and read-only SpendLogs.
Run from C:/law_insight (not backend, so local provider .env is never loaded).
Application persistence is intercepted; no application DB is touched.
"""
import asyncio
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.parse

SMOKE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SMOKE_ROOT))
import run as smoke

os.environ.update(LLM_MODE='gateway', GEMINI_API_KEY_1='', GEMINI_API_KEY_2='',
                  GEMINI_API_KEY_3='', LITELLM_LOCAL_MODEL_COST_MAP='True')
sys.path.insert(0, 'C:/law_insight/backend')
from app.config import Settings
from app.services import llm
from app.services.token_logger import get_usage_context, token_usage_context, build_token_usage_log


async def main():
    credentials = json.loads(smoke.STATE.read_text(encoding='utf-8'))
    master = credentials['SMOKE_MASTER_KEY']
    run_id = 'law-core-' + secrets.token_hex(6)
    status, created = smoke.http('/key/generate', master, {
        'models': ['tla-hd-mock'], 'duration': '1h', 'key_alias': run_id,
        'metadata': {'tags': ['tla-hd']}, 'max_budget': 1})
    assert status == 200 and created.get('key'), 'key creation failed'
    key = created['key']
    status, info = smoke.http('/key/info?key=' + urllib.parse.quote(key, safe=''), master)
    assert status == 200 and info['info']['metadata']['tags'] == ['tla-hd']
    llm.settings = Settings(_env_file=None, llm_mode='gateway',
        gateway_base_url='http://127.0.0.1:4100/v1', gateway_virtual_key=key,
        gateway_model='tla-hd-mock', gateway_timeout_seconds=30)
    calls = []
    async def capture(**kwargs):
        ctx = get_usage_context()
        row = build_token_usage_log(context=ctx, **kwargs)
        calls.append({'user': ctx.username, 'response_id': row.call_id,
            'provider': row.provider, 'model': row.requested_model,
            'prompt_tokens': row.prompt_tokens, 'completion_tokens': row.completion_tokens,
            'total_tokens': row.total_tokens, 'pricing_status': row.pricing_status})
        return True
    llm.record_model_call = capture
    async def request(index):
        with token_usage_context(user_id='synthetic-' + str(index), username=run_id + '.user-' + str(index),
            company_id=None, unit_id=None, session_id=run_id, function_name='integration-smoke'):
            if index % 2:
                result = await llm.call_llm_chat('agent1', 'Synthetic test', [{'role': 'user', 'content': 'CANARY-' + run_id}], max_tokens=16)
            else:
                result = await llm.call_llm('agent2', 'Synthetic test', 'CANARY-' + run_id, max_tokens=16)
            assert result.text == 'gateway-smoke-ok'
    await asyncio.gather(*(request(i) for i in range(4)))
    sql = f'''SELECT COALESCE(json_agg(t), '[]'::json) FROM (SELECT request_id, end_user, prompt_tokens, completion_tokens, total_tokens, request_tags, model, status, (messages::text LIKE '%CANARY-%' OR response::text LIKE '%CANARY-%' OR proxy_server_request::text LIKE '%CANARY-%') AS canary_leaked FROM "LiteLLM_SpendLogs" WHERE end_user LIKE '{run_id}%') t;'''
    deadline = time.monotonic() + 120
    rows = []
    while time.monotonic() < deadline:
        query = subprocess.run(['docker', 'exec', 'tla-gateway-smoke-db-1', 'psql', '-U', 'smoke', '-d', 'litellm_smoke', '-tAc', sql], capture_output=True, text=True)
        assert query.returncode == 0, 'SpendLogs read failed'
        rows = json.loads(query.stdout)
        if len(rows) >= len(calls):
            break
        await asyncio.sleep(2)
    assert len(rows) == len(calls) == 4
    for call in calls:
        matches = [r for r in rows if r['request_id'] == call['response_id']]
        assert len(matches) == 1
        row = matches[0]
        assert row['end_user'] == call['user']
        for field in ['prompt_tokens', 'completion_tokens', 'total_tokens']:
            assert row[field] == call[field]
        assert 'tla-hd' in row['request_tags'] and not row['canary_leaked']
    report = {'result': 'PASS', 'scope': 'real_law_insight_helpers_single_mock_proxy_not_full_app_or_ledger',
        'application_logger': 'real row builder; persistence intercepted, no application DB writes',
        'run_id': run_id, 'calls': sorted(calls, key=lambda c: c['user']), 'spend_logs': rows}
    destination = Path(__file__).with_name('law-insight-result.json')
    destination.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    asyncio.run(main())
