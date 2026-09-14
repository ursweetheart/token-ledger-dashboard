"""Bounded real-helper/LB/two-proxy MOCK test for Ralli; no application DB/provider writes."""
import asyncio
from collections import Counter
import json
import math
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

import run as smoke

os.environ.update(LLM_MODE='gateway', GEMINI_API_KEY_1='', GEMINI_API_KEY_2='',
                  GEMINI_API_KEY_3='', LITELLM_LOCAL_MODEL_COST_MAP='True')
sys.path.insert(0, 'D:/rangdong-chatbot')  # branch api_gateway
from src.core.gateway_settings import Settings
from src.core import llm
from src.core.token_logger import token_usage_context, get_usage_context, build_token_usage_log

BASE = 'http://127.0.0.1:4101'
LB = 'tla-gateway-smoke-gateway-lb-1'
SECOND = 'tla-gateway-smoke-gateway2-1'
ROOT = Path(__file__).resolve().parent


def docker(*args):
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError('docker command failed: ' + ' '.join(args[:3]))
    return result.stdout


def http(path, key=None, payload=None):
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    req = urllib.request.Request(BASE + path, headers=headers,
        data=None if payload is None else json.dumps(payload).encode())
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = response.read().decode()
            return response.status, json.loads(data) if data.startswith('{') else data
    except urllib.error.HTTPError as exc:
        return exc.code, None


async def ready():
    for _ in range(60):
        try:
            if http('/health/readiness')[0] == 200:
                return
        except Exception:
            pass
        await asyncio.sleep(1)
    raise AssertionError('LB readiness timeout')


async def main():
    run_id = 'ralli-lb-' + secrets.token_hex(6)
    report = {'run_id': run_id, 'result': 'RUNNING', 'endpoint': BASE,
        'scope': 'real helpers + nginx LB + two mock LiteLLM proxies + isolated SpendLogs',
        'limitations': ['not authenticated router E2E', 'no application DB persistence',
            'no ETL/department/dashboard verification', 'no OCR/Marker',
            'no Redis/Sentinel', 'mock closed-loop load is not production capacity'],
        'stages': [], 'calls': [], 'negative': {}, 'transport_attempts': []}
    destination = ROOT / (run_id + '.json')
    key = None
    master = smoke.state()['SMOKE_MASTER_KEY']
    original_completion = llm.litellm.acompletion
    original_recorder = llm.record_model_call
    original_settings = llm.settings
    faulted = set()
    total_start = time.monotonic()

    def save():
        destination.write_text(json.dumps(report, indent=2), encoding='utf-8')

    async def guarded_completion(**kwargs):
        ctx = get_usage_context()
        assert kwargs['api_base'] == BASE + '/v1', 'provider/LB bypass'
        assert kwargs['model'] == 'openai/ralli-mock'
        assert kwargs['extra_headers'] == {'X-User': ctx.username}
        assert kwargs['user'] == ctx.username and kwargs['num_retries'] == 0
        report['transport_attempts'].append({'user': ctx.username, 'base': kwargs['api_base']})
        return await original_completion(**kwargs)

    async def capture(**kwargs):
        ctx = get_usage_context()
        row = build_token_usage_log(context=ctx, **kwargs)
        report['calls'].append({'user': ctx.username, 'operation': ctx.session_id,
            'response_id': row.call_id, 'prompt_tokens': row.prompt_tokens,
            'completion_tokens': row.completion_tokens, 'total_tokens': row.total_tokens})
        return True

    def settings(virtual_key, timeout=15):
        return Settings(_env_file=None, llm_mode='gateway', gateway_base_url=BASE+'/v1',
            gateway_virtual_key=virtual_key, gateway_model='ralli-mock',
            gateway_timeout_seconds=timeout)

    async def call(index, stage):
        user = run_id + '.user-' + str(index % 8)
        with token_usage_context(user_id='synthetic-' + str(index % 8), username=user,
                company_id=None, unit_id=None, session_id=stage+'-'+str(index), function_name=stage):
            started = time.monotonic()
            if index % 2:
                result = await llm.call_llm_chat('agent1', 'Synthetic system',
                    [{'role': 'user', 'content': 'CANARY-' + run_id}], max_tokens=16)
            else:
                result = await llm.call_llm('agent2', 'Synthetic system', 'CANARY-'+run_id, max_tokens=16)
            assert result.text == 'gateway-smoke-ok'
            return time.monotonic() - started

    async def stage(name, count, concurrency):
        assert time.monotonic() - total_start < 300, 'test time ceiling exceeded'
        start_index = len(report['calls'])
        sem = asyncio.Semaphore(concurrency)
        async def bounded(index):
            async with sem:
                return await call(index, name)
        start = time.monotonic()
        latencies = await asyncio.wait_for(asyncio.gather(
            *(bounded(start_index+i) for i in range(count))), timeout=90)
        elapsed = time.monotonic() - start
        ordered = sorted(latencies)
        report['stages'].append({'name': name, 'requests': count, 'concurrency': concurrency,
            'elapsed_seconds': elapsed, 'rps': count / elapsed,
            **{'p'+str(p)+'_ms': ordered[math.ceil(len(ordered)*p/100)-1]*1000 for p in (50,95,99)}})
        save()

    try:
        for _ in range(120):
            health = docker('inspect', SECOND, '--format', '{{.State.Health.Status}}').strip()
            if health == 'healthy':
                break
            await asyncio.sleep(1)
        assert health == 'healthy', 'second proxy not ready before load'
        docker('exec', LB, 'nginx', '-s', 'reload')
        await ready()
        assert http('/lb-health') == (200, 'lb-ok\n')
        assert docker('network', 'inspect', 'tla-gateway-smoke_isolated', '--format', '{{.Internal}}').strip() == 'true'
        report['resources_before'] = docker('stats', '--no-stream', '--format', '{{.Name}} {{.CPUPerc}} {{.MemUsage}}', LB, SECOND, 'tla-gateway-smoke-gateway-1', 'tla-gateway-smoke-db-1')
        status, data = http('/key/generate', master, {'models':['ralli-mock'], 'duration':'1h',
            'key_alias':run_id, 'metadata':{'tags':['ralli']}, 'max_budget':1})
        assert status == 200 and data.get('key'), 'key create failed'
        key = data['key']
        info_path = '/key/info?key=' + urllib.parse.quote(key, safe='')
        status, info = http(info_path, master)
        assert status == 200 and info['info']['metadata']['tags'] == ['ralli']
        llm.settings = settings(key)
        llm.record_model_call = capture
        llm.litellm.acompletion = guarded_completion
        for name, count, concurrency in [('baseline',1,1),('ramp2',8,2),('ramp4',24,4),('ramp8',48,8)]:
            await stage(name,count,concurrency)
        for helper in ('call_llm','call_llm_chat'):
            before = len(report['transport_attempts'])
            try:
                if helper == 'call_llm':
                    await llm.call_llm('agent1','synthetic','synthetic')
                else:
                    await llm.call_llm_chat('agent1','synthetic',[])
                raise AssertionError('missing identity accepted')
            except ValueError:
                assert len(report['transport_attempts']) == before
                report['negative']['missing_identity_'+helper] = 'rejected before network'
        llm.settings = settings('invalid-synthetic-key')
        before = len(report['transport_attempts'])
        try:
            await call(999,'invalid-key')
            raise AssertionError('invalid key accepted')
        except llm._LiteLLM.AuthenticationError:
            assert len(report['transport_attempts']) == before+1
            report['negative']['invalid_key'] = '401; one SDK attempt; no bypass'
        llm.settings = settings(key)
        faulted.add(SECOND)
        docker('stop','--time','2',SECOND)
        await stage('one_proxy_down',8,2)
        docker('start',SECOND)
        faulted.remove(SECOND)
        for _ in range(120):
            health = docker('inspect', SECOND, '--format', '{{.State.Health.Status}}').strip()
            if health == 'healthy':
                break
            await asyncio.sleep(1)
        assert health == 'healthy', 'second proxy did not recover'
        faulted.add(LB)
        docker('stop','--time','2',LB)
        llm.settings = settings(key,3)
        before = len(report['transport_attempts'])
        start = time.monotonic()
        try:
            await call(998,'lb-down')
            raise AssertionError('LB outage accepted')
        except Exception as exc:
            assert len(report['transport_attempts']) == before+1
            report['negative']['lb_outage'] = {'sdk_attempts':1,'elapsed_seconds':time.monotonic()-start,'bypass':False}
        docker('start',LB)
        faulted.remove(LB)
        await ready()
        llm.settings = settings(key)
        await stage('recovery',4,2)
        sql = f'''SELECT COALESCE(json_agg(t), '[]'::json) FROM (SELECT request_id,end_user,prompt_tokens,completion_tokens,total_tokens,request_tags,model,status,(messages::text LIKE '%CANARY-%' OR response::text LIKE '%CANARY-%' OR proxy_server_request::text LIKE '%CANARY-%') AS canary_leaked FROM "LiteLLM_SpendLogs" WHERE end_user LIKE '{run_id}%') t;'''
        deadline = time.monotonic()+120
        expected_ids = {c['response_id'] for c in report['calls']}
        while True:
            rows = json.loads(docker('exec','tla-gateway-smoke-db-1','psql','-U','smoke','-d','litellm_smoke','-tAc',sql))
            if expected_ids <= {r['request_id'] for r in rows} or time.monotonic() >= deadline:
                break
            await asyncio.sleep(2)
        assert len(expected_ids) == len(report['calls'])
        assert len(rows) == len(report['calls']), 'missing/extra SpendLogs'
        by_id = {r['request_id']: r for r in rows}
        for c in report['calls']:
            r = by_id[c['response_id']]
            assert r['end_user'] == c['user']
            assert all(r[f] == c[f] for f in ('prompt_tokens','completion_tokens','total_tokens'))
            assert 'ralli' in r['request_tags'] and not r['canary_leaked']
        trace = [json.loads(line) for line in docker('exec',LB,'cat','/var/log/nginx/attribution.jsonl').splitlines()]
        trace = [r for r in trace if r['user'].startswith(run_id) and r['path'] == '/v1/chat/completions']
        success_trace = [r for r in trace if r['status']==200]
        assert Counter(r['user'] for r in success_trace) == Counter(c['user'] for c in report['calls'])
        upstreams = {r['upstream'].split(', ')[-1] for r in success_trace}
        assert len(upstreams) == 2, 'did not traverse two upstreams'
        assert any(r['status']==401 for r in trace), 'invalid key not seen at LB'
        report.update(result='PASS',spend_logs=rows,lb_trace=trace,upstreams=sorted(upstreams),
            total_requests=len(report['calls']),total_tokens=sum(c['total_tokens'] for c in report['calls']))
        report['resources_after'] = docker('stats','--no-stream','--format','{{.Name}} {{.CPUPerc}} {{.MemUsage}}', LB, SECOND, 'tla-gateway-smoke-gateway-1','tla-gateway-smoke-db-1')
    except Exception as exc:
        report.update(result='FAIL',error_type=type(exc).__name__)
        raise
    finally:
        for container in faulted:
            docker('start',container)
        llm.settings = original_settings
        llm.record_model_call = original_recorder
        llm.litellm.acompletion = original_completion
        if key:
            try:
                status, _ = http('/key/delete', master, {'keys':[key]})
                read_status, _ = http('/key/info?key='+urllib.parse.quote(key,safe=''),master)
                report['key_cleanup'] = {'delete_status':status,'readback_status':read_status}
            except Exception:
                report['key_cleanup'] = 'cleanup failed; key expires after 1h'
        save()
        print(json.dumps({k:report[k] for k in ('result','run_id','stages','negative','key_cleanup') if k in report},indent=2))
        print('Evidence:',destination)


if __name__ == '__main__':
    asyncio.run(main())
