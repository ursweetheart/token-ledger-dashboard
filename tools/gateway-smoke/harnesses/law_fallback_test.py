"""Isolated real-SDK LB fault test; direct SDK is MOCK, SMTP disabled.

Run with D:/law_insight/.venv-gateway/Scripts/python.exe; set SMOKE_STATE_FILE.
Use --self-check for offline guard checks (no app imports, sockets or Docker).
This script also switches to a temporary no-env cwd before application imports.
Exit 0=PASS, 1=FAIL, 2=BLOCKED (implementation/dependency not ready).
Owns only this script and law-fallback-*.json evidence. No app DB writes.
"""
from __future__ import annotations

import asyncio
import base64
from collections import Counter
import hashlib
import re
import contextlib
import inspect
import io
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts' / 'current'
BASE = 'http://127.0.0.1:4101'
LB = 'tla-gateway-smoke-gateway-lb-1'
SECOND = 'tla-gateway-smoke-gateway2-1'
FIRST = 'tla-gateway-smoke-gateway-1'
DB = 'tla-gateway-smoke-db-1'
CONTAINERS = (LB, SECOND, FIRST, DB)
SQL_PREFIX = ('exec', DB, 'psql', '-U', 'smoke', '-d', 'litellm_smoke', '-tAc')
SELECTS = set()
TRACE_COMMAND = ('exec', LB, 'cat', '/var/log/nginx/attribution.jsonl')
RELOAD_COMMAND = ('exec', LB, 'nginx', '-s', 'reload')
HELPERS = ('call_llm', 'call_llm_chat', 'ocr_pdf_with_gemini')
HEALTH_FORMAT = '{{json .State}}'
DIRECT_SENTINEL = 'MOCK-DIRECT-CREDENTIAL-NEVER-SEND'
SMTP_SENTINEL = 'MOCK-SMTP-CREDENTIAL-NEVER-SEND'
CONTENT_SENTINEL = 'MOCK-CONTENT-NEVER-RECORD'
SAFE_REASONS = {'connection_error', 'timeout', 'connection_timeout', '502', '503', '504'}


class Blocked(RuntimeError):
    pass


class CheckFailed(AssertionError):
    pass


def require(condition, code):
    if not condition:
        raise CheckFailed(code)


def docker_allowed(args):
    args = tuple(args)
    return (args in {('inspect', c, '--format', HEALTH_FORMAT) for c in CONTAINERS}
            or args in {('start', c) for c in (LB, FIRST, SECOND)}
            or args in {('stop', '--time', '2', c) for c in (LB, FIRST, SECOND)}
            or args in (TRACE_COMMAND, RELOAD_COMMAND)
            or (len(args) == len(SQL_PREFIX) + 1 and args[:-1] == SQL_PREFIX
                and args[-1] in SELECTS))


def install_guards(report):
    # Do not inherit provider, SMTP, application DB, proxy, or cloud credentials.
    keep = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP',
            'TMPDIR', 'SMOKE_STATE_FILE',
            'LOCALAPPDATA', 'APPDATA', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH',
            'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'OS',
            'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS'}
    clean = {k: v for k, v in os.environ.items() if k.upper() in keep}
    os.environ.clear()
    os.environ.update(clean)
    os.environ.update(LLM_MODE='gateway', LITELLM_LOCAL_MODEL_COST_MAP='True',
                      LITELLM_TELEMETRY='False', DO_NOT_TRACK='1',
                      PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1',
                      DATABASE_URL='postgresql+asyncpg://mock:probe_local@127.0.0.1:9/mock')
    sys.dont_write_bytecode = True
    report['guards'] = {'dotenv_read_denial': True, 'dotenv_sources_disabled': True,
                        'only_application_egress': BASE, 'direct_boundary': 'MOCK',
                        'smtp_boundary': 'DISABLED; attempts forbidden', 'blocked_egress_count': 0}

    def wakeup(address):
        if not isinstance(address, tuple) or address[0] not in ('127.0.0.1', '::1'):
            return False
        frame = sys._getframe(1)
        while frame:
            if frame.f_code.co_name == '_fallback_socketpair' and frame.f_globals.get('__name__') == 'socket':
                return True
            frame = frame.f_back
        return False

    def allowed(address):
        return isinstance(address, tuple) and address[:2] == ('127.0.0.1', 4101)

    def audit(event, args):
        if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
            name = os.fsdecode(args[0]).replace('\\', '/').rsplit('/', 1)[-1].lower()
            if name == '.env' or name.startswith('.env.') or name.endswith('.env'):
                raise PermissionError('dotenv_read_denied')
        if event in ('socket.connect', 'socket.sendto'):
            address = args[-1]
            if not allowed(address) and not wakeup(address):
                report['guards']['blocked_egress_count'] += 1
                raise PermissionError('external_egress_denied')
        if event == 'socket.getaddrinfo':
            if not allowed((args[0], args[1])) and not wakeup((args[0], args[1])):
                report['guards']['blocked_egress_count'] += 1
                raise PermissionError('external_dns_denied')
        if event in ('socket.gethostbyname', 'socket.gethostbyaddr'):
            report['guards']['blocked_egress_count'] += 1
            raise PermissionError('external_dns_denied')
        if event == 'subprocess.Popen':
            if args[0] is not None and Path(str(args[0])).name.lower() not in ('docker', 'docker.exe'):
                raise PermissionError('subprocess_denied')
            raw = args[1]
            if isinstance(raw, str):
                # Windows audit exposes list2cmdline; do not parse SQL with POSIX shlex.
                commands = [('inspect', c, '--format', HEALTH_FORMAT) for c in CONTAINERS]
                commands += [('start', c) for c in (LB, FIRST, SECOND)]
                commands += [('stop', '--time', '2', c) for c in (LB, FIRST, SECOND)]
                commands += [TRACE_COMMAND, RELOAD_COMMAND] + [SQL_PREFIX + (sql,) for sql in SELECTS]
                if not any(raw == subprocess.list2cmdline([exe, *cmd])
                           for exe in ('docker', 'docker.exe') for cmd in commands):
                    raise PermissionError('subprocess_denied')
                return
            elif isinstance(raw, (tuple, list)):
                argv = list(raw)
            else:
                argv = []
            if (not argv
                    or str(argv[0]).lower() not in ('docker', 'docker.exe')
                    or not docker_allowed(argv[1:])):
                raise PermissionError('subprocess_denied')
        if event in ('os.system', 'os.posix_spawn'):
            raise PermissionError('subprocess_denied')

    sys.addaudithook(audit)
    import dotenv
    import dotenv.main
    dotenv.load_dotenv = dotenv.main.load_dotenv = lambda *a, **k: False
    dotenv.dotenv_values = dotenv.main.dotenv_values = lambda *a, **k: {}
    from pydantic_settings import BaseSettings

    def sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        return init_settings, env_settings

    BaseSettings.settings_customise_sources = classmethod(sources)


def docker(*args):
    require(docker_allowed(args), 'docker_scope_violation')
    result = subprocess.run(['docker', *args], capture_output=True, text=True, timeout=90)
    require(result.returncode == 0, 'docker_command_failed')
    return result.stdout


def state(container):
    return json.loads(docker('inspect', container, '--format', HEALTH_FORMAT))


def health(container):
    value = state(container)
    return value.get('Running') is True and value.get('Health', {}).get('Status') == 'healthy'


def http(path, key=None, payload=None):
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = 'Bearer ' + key
    request = urllib.request.Request(BASE + path, headers=headers,
        data=None if payload is None else json.dumps(payload).encode())
    # Explicit empty proxy handler also bypasses Windows registry proxy discovery.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=10) as response:
            body = response.read().decode()
            return response.status, json.loads(body) if body.startswith('{') else body
    except urllib.error.HTTPError as exc:
        return exc.code, None


async def ready(container):
    # Only recovery readiness, never waits for implementation files/other agents.
    deadline = time.monotonic() + 150
    while time.monotonic() < deadline:
        if health(container):
            if container != LB:
                return
            try:
                if http('/health/readiness')[0] == 200 and http('/lb-health') == (200, 'lb-ok\n'):
                    return
            except (OSError, urllib.error.URLError):
                pass
        await asyncio.sleep(1)
    raise CheckFailed('container_recovery_timeout')


def load_app():
    sys.path.insert(0, 'D:/law_insight/backend')
    from app.config import Settings
    from app.services import llm, token_logger, gemini_ocr
    from app.services import email_alerts
    require('gateway_fallback_enabled' in Settings.model_fields, 'fallback_settings_missing')
    require('gateway_fallback_enabled' in inspect.getsource(llm), 'routing_implementation_missing')
    require(all(name in inspect.signature(token_logger.build_token_usage_log).parameters
                for name in ('route', 'fallback_reason', 'operation_id')), 'ledger_metadata_missing')
    require(callable(email_alerts.schedule_gateway_alert), 'alert_schedule_missing')
    require(callable(email_alerts.drain_gateway_alerts), 'alert_drain_missing')
    return Settings, llm, token_logger, email_alerts, gemini_ocr


def spend_query(run_id, ids):
    require(re.fullmatch(r'law-fallback-[0-9a-f]{12}', run_id), 'unsafe_run_id')
    require(ids and all(re.fullmatch(r'[A-Za-z0-9._:/-]{1,200}', i) for i in ids), 'unsafe_response_id')
    quoted = ','.join("'" + i + "'" for i in sorted(ids))
    sql = ('SELECT COALESCE(json_agg(t), \'[]\'::json) FROM (SELECT '
           'request_id,end_user,prompt_tokens,completion_tokens,total_tokens,request_tags,model,status '
           'FROM "LiteLLM_SpendLogs" WHERE request_id IN (' + quoted + ') '
           "OR end_user LIKE '" + run_id + ".%') t;")
    SELECTS.add(sql)  # Only the exact generated read-only query is executable.
    return sql


def scanned_pdf():
    import fitz
    with fitz.open() as source, fitz.open() as result:
        for number in (1, 2):
            page = source.new_page(width=300, height=400)
            page.insert_text((30, 60), 'SYNTHETIC SCAN PAGE ' + str(number))
            png = page.get_pixmap().tobytes('png')
            scan = result.new_page(width=300, height=400)
            scan.insert_image(scan.rect, stream=png)
        payload = result.tobytes()
    with fitz.open(stream=payload, filetype='pdf') as check:
        require(len(check) == 2 and all(not p.get_text().strip() for p in check), 'pdf_not_scanned')
    return payload


async def exercise(report, app):
    Settings, llm, ledger, alerts, ocr = app
    import smtplib
    sys.path.insert(0, str(ROOT))
    import run as smoke
    require(os.environ.get('SMOKE_STATE_FILE') and smoke.STATE == Path(os.environ['SMOKE_STATE_FILE']),
            'explicit_mock_state_required')
    require(smoke.STATE.is_file(), 'existing_mock_state_missing')
    master = smoke.state()['SMOKE_MASTER_KEY']
    key = None
    faulted = set()
    report.update(stages=[], attempts=[], ledger_rows=[], smtp=[], faults=[])
    original_completion = llm.litellm.acompletion
    expected = {}
    fail_operations = set()
    gateway_payloads = {}
    responses = {}
    wire = []
    pdf = scanned_pdf()
    page_hashes = {hashlib.sha256(image).hexdigest() for image in ocr._pdf_to_images(pdf)}
    require(len(page_hashes) == 2, 'ocr_pages_not_distinct')
    stage = 'preflight'
    defaults = Settings(_env_file=None, llm_mode='gateway')
    require(defaults.gateway_fallback_enabled is False, 'unsafe_fallback_default')
    require(defaults.gateway_fallback_max_attempts == 1, 'unsafe_attempt_default')
    require(defaults.gateway_fallback_timeout_seconds == 30, 'timeout_default_mismatch')
    require(defaults.alert_email_enabled is False, 'unsafe_email_default')

    def settings(enabled=False, credential=None):
        return Settings(_env_file=None, llm_mode='gateway', gateway_base_url=BASE + '/v1',
            gateway_virtual_key=credential if credential is not None else key,
            gateway_model='tla-hd-mock', gateway_timeout_seconds=3,
            gateway_fallback_enabled=enabled, gateway_fallback_max_attempts=1,
            gateway_fallback_timeout_seconds=5, gemini_api_key_1=DIRECT_SENTINEL,
            gemini_api_key_2='', gemini_api_key_3='', alert_email_enabled=False)

    def no_smtp(*args, **kwargs):
        report['smtp'].append({'stage': stage, 'unexpected_attempt': True})
        raise CheckFailed('smtp_forbidden')

    # Observe the real serialized SDK request, then delegate to the real HTTP send.
    import httpx
    original_send = httpx.AsyncClient.send

    async def wire_send(client, request, *args, **kwargs):
        if str(request.url) == BASE + '/v1/chat/completions':
            body = json.loads(request.content)
            ctx = ledger.get_usage_context()
            require(ctx and request.headers.get('X-User') == body.get('user') == ctx.username,
                    'wire_identity_mismatch')
            require(body.get('model') == 'tla-hd-mock', 'wire_alias_mismatch')
            entry = {'operation': ctx.session_id, 'user': ctx.username,
                     'body_user': body['user'], 'model': body['model'], 'status': None}
            wire.append(entry)
            response = await original_send(client, request, *args, **kwargs)
            entry['status'] = response.status_code
            return response
        return await original_send(client, request, *args, **kwargs)

    async def guarded_completion(**kwargs):
        ctx = ledger.get_usage_context()
        require(ctx is not None, 'transport_identity_missing')
        operation = ctx.session_id
        payload = {k: kwargs.get(k) for k in ('messages', 'temperature', 'max_tokens', 'response_format')}
        fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        page = None
        if ctx.function_name == 'ocr_pdf_with_gemini':
            url = kwargs['messages'][0]['content'][1]['image_url']['url']
            require(url.startswith('data:image/png;base64,'), 'ocr_image_missing')
            image = base64.b64decode(url.split(',', 1)[1], validate=True)
            page = hashlib.sha256(image).hexdigest()
            require(image.startswith(b'\x89PNG') and page in page_hashes, 'ocr_render_mismatch')
            require(kwargs['temperature'] == 0.1 and kwargs['max_tokens'] == 8192, 'ocr_options_changed')
        call_key = (operation, page)
        if kwargs.get('api_base') == BASE + '/v1':
            require(kwargs['model'] == 'openai/tla-hd-mock', 'gateway_model_mismatch')
            require(kwargs.get('extra_headers') == {'X-User': ctx.username}, 'gateway_identity_header_mismatch')
            require(kwargs.get('user') == ctx.username and kwargs.get('extra_body') == {'user': ctx.username},
                    'gateway_body_user_mismatch')
            require(kwargs.get('num_retries') == 0 and 0 < kwargs.get('timeout', 0) <= 3, 'gateway_unbounded')
            require(call_key not in gateway_payloads, 'duplicate_page_gateway_attempt')
            gateway_payloads[call_key] = fingerprint
            attempt = {'operation': operation, 'route': 'gateway', 'user': ctx.username, 'page': page}
            report['attempts'].append(attempt)
            try:
                response = await original_completion(**kwargs)
            except Exception as exc:
                attempt['failure_reason'] = llm.classify_gateway_failure(exc)
                chain, pending, seen = [], [exc], set()
                while pending and len(chain) < 32:
                    item = pending.pop()
                    if id(item) in seen:
                        continue
                    seen.add(id(item))
                    chain.append({'type': type(item).__name__, 'status': getattr(item, 'status_code', None)})
                    pending.extend(child for name in ('__cause__', '__context__', 'original_exception')
                                   if isinstance(child := getattr(item, name, None), BaseException))
                attempt['error_chain'] = chain
                raise
        else:
            require(kwargs.get('model') == 'gemini/' + llm.settings.gemini_pro_model, 'direct_model_mismatch')
            require(not any(k in kwargs for k in ('api_base', 'extra_headers', 'extra_body', 'headers', 'user', 'metadata')),
                    'direct_gateway_metadata_leaked')
            require(kwargs.get('api_key') == DIRECT_SENTINEL, 'direct_credential_mismatch')
            require(kwargs.get('num_retries') == 0 and 0 < kwargs.get('timeout', 0) <= 5, 'direct_unbounded')
            require(key not in json.dumps(kwargs), 'direct_virtual_credential_leaked')
            require(gateway_payloads.get(call_key) == fingerprint, 'fallback_payload_changed')
            report['attempts'].append({'operation': operation, 'route': 'direct_fallback',
                'user': ctx.username, 'page': page, 'boundary': 'MOCK litellm.acompletion (SDK only)'})
            await asyncio.sleep(0)
            if operation in fail_operations:
                raise RuntimeError('MOCK_DIRECT_FAILURE')
            response = llm.litellm.ModelResponse(id='mock-direct-' + secrets.token_hex(8),
                model=kwargs['model'], choices=[{'index': 0, 'message': {'role': 'assistant',
                'content': 'mock-direct-ok'}, 'finish_reason': 'stop'}],
                usage={'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18})
        require(response.id not in responses, 'duplicate_response_id')
        responses[response.id] = {'operation': operation, 'page': page,
                                 'usage': ledger.normalize_provider_usage(response.usage)}
        return response

    async def capture(**kwargs):
        ctx = ledger.get_usage_context()
        row = ledger.build_token_usage_log(context=ctx, **kwargs)
        identity = expected[ctx.session_id]
        fields = {'user_id': 'user_id', 'username': 'username_snapshot',
                  'company_id': 'company_id_snapshot', 'unit_id': 'unit_id_snapshot',
                  'session_id': 'session_id', 'function_name': 'function_name'}
        require(all(getattr(row, target) == identity[source] for source, target in fields.items()),
                'ledger_identity_mismatch')
        require(row.route in ('gateway', 'direct_fallback'), 'ledger_route_mismatch')
        require(bool(row.operation_id), 'ledger_operation_missing')
        received = responses[row.call_id]
        require(received['operation'] == ctx.session_id and all(
            getattr(row, field) == received['usage'][field]
            for field in ('prompt_tokens', 'completion_tokens', 'total_tokens')), 'response_usage_mismatch')
        require(row.fallback_reason in SAFE_REASONS if row.route == 'direct_fallback'
                else row.fallback_reason is None, 'ledger_reason_mismatch')
        report['ledger_rows'].append({name: getattr(row, name) for name in (
            'call_id', 'route', 'fallback_reason', 'operation_id', 'user_id', 'username_snapshot',
            'company_id_snapshot', 'unit_id_snapshot', 'session_id', 'function_name',
            'prompt_tokens', 'completion_tokens', 'total_tokens')})
        report['ledger_rows'][-1]['page'] = received['page']
        return True  # No application persistence; actual builder remains intact.

    async def drain():
        await asyncio.wait_for(alerts.drain_gateway_alerts(), timeout=10)

    async def invoke(label, helper, route=None, failure=False, missing=False, direct_failure=False):
        operation = report['run_id'] + '.' + label
        identity = dict(user_id='synthetic-' + label, username=report['run_id'] + '.user-' + label,
                        company_id='synthetic-company', unit_id='synthetic-unit-' + label,
                        session_id=operation, function_name=helper)
        expected[operation] = identity
        if direct_failure:
            fail_operations.add(operation)
        started = time.monotonic()
        error = reason = None
        pages = 2 if helper == 'ocr_pdf_with_gemini' else 1
        with contextlib.nullcontext() if missing else ledger.token_usage_context(**identity):
            try:
                if helper == 'call_llm':
                    result = await asyncio.wait_for(llm.call_llm('agent1', CONTENT_SENTINEL,
                        CONTENT_SENTINEL, max_tokens=16, json_mode=True), 20)
                elif helper == 'call_llm_chat':
                    result = await asyncio.wait_for(llm.call_llm_chat('agent2', CONTENT_SENTINEL,
                        [{'role': 'user', 'content': CONTENT_SENTINEL}], max_tokens=16), 20)
                else:
                    result = await asyncio.wait_for(ocr.ocr_pdf_with_gemini(pdf, 'synthetic-two-pages.pdf'), 20)
            except (CheckFailed, AssertionError):
                raise
            except Exception as exc:
                require(failure, 'unexpected_request_failure:' + label)
                error = type(exc).__name__
                reason = llm.classify_gateway_failure(exc)
                if missing:
                    require(isinstance(exc, ValueError), 'missing_identity_wrong_error')
                elif label.startswith('invalid'):
                    require(isinstance(exc, llm.litellm.AuthenticationError), 'invalid_credential_wrong_error')
                elif direct_failure:
                    require(type(exc) is RuntimeError and str(exc) == 'MOCK_DIRECT_FAILURE', 'direct_failure_wrong_error')
                else:
                    require(reason in SAFE_REASONS, 'outage_not_classified')
            else:
                require(not failure, 'unexpected_request_success')
                content = 'mock-direct-ok' if route == 'direct_fallback' else 'gateway-smoke-ok'
                if pages == 2:
                    markdown, count = result
                    require(count == 2 and markdown.count(content) == 2
                            and all('<!-- Page ' + str(i) + ' -->' in markdown for i in (1, 2)), 'ocr_incomplete')
                else:
                    require(result.text == content, 'response_mismatch')
        require(ledger.get_usage_context() is None, 'identity_context_leaked')
        attempts = [a for a in report['attempts'] if a['operation'] == operation]
        counts = Counter(a['route'] for a in attempts)
        require(counts['gateway'] == (0 if missing else pages), 'gateway_attempt_count')
        # A failed PDF cancels unfinished siblings; each started page still has at most one fallback.
        direct_count = counts['direct_fallback']
        if direct_failure:
            require(1 <= direct_count <= pages, 'fallback_attempt_count')
        else:
            require(direct_count == (pages if route == 'direct_fallback' else 0), 'fallback_attempt_count')
        require(all(n == 1 for n in Counter((a['route'], a['page']) for a in attempts).values()), 'page_retried')
        rows = [r for r in report['ledger_rows'] if r['session_id'] == operation]
        require(len(rows) == (0 if failure else pages), 'ledger_row_count')
        require(all(r['route'] == route for r in rows), 'result_route_mismatch')
        sent = [w for w in wire if w['operation'] == operation]
        require(len(sent) == counts['gateway'], 'http_attempt_count_mismatch')
        report['stages'].append({'name': label, 'helper': helper, 'expected_route': route,
            'fallback_enabled': llm.settings.gateway_fallback_enabled,
            'expected_failure': failure, 'error_type': error, 'failure_reason': reason,
            'pages': pages, 'sdk_attempts': dict(counts), 'gateway_http_attempts': len(sent),
            'elapsed_seconds': time.monotonic() - started, 'result': 'PASS'})

    async def batch(name, route=None, failure=False, direct_failure=False):
        # Sequential modalities; only the two synthetic OCR users run concurrently.
        for helper in HELPERS:
            calls = [invoke(name + '-' + helper + '-' + str(i), helper, route,
                            failure=failure, direct_failure=direct_failure)
                     for i in range(2 if helper == 'ocr_pdf_with_gemini' else 1)]
            outcomes = await asyncio.gather(*calls, return_exceptions=True)
            for outcome in outcomes:
                if isinstance(outcome, BaseException):
                    raise outcome
        await drain()
        require(not report['smtp'], 'unexpected_email_attempt')

    async def stop(container):
        faulted.add(container)  # Register BEFORE stopping for exception-safe cleanup.
        docker('stop', '--time', '2', container)
        require(state(container)['Running'] is False, 'fault_readback_failed')
        report['faults'].append({'stage': stage, 'container': container, 'running': False})

    async def restore(container):
        docker('start', container)
        await ready(container)
        faulted.discard(container)
        report['faults'].append({'stage': stage, 'container': container, 'running': True, 'health': 'healthy'})

    try:
        require(all(health(c) for c in CONTAINERS), 'initial_stack_not_healthy')
        require(http('/health/readiness')[0] == 200, 'lb_not_ready')
        report['initial_health'] = {c: 'healthy' for c in CONTAINERS}
        status, data = http('/key/generate', master, {'models': ['tla-hd-mock'], 'duration': '1h',
            'key_alias': report['run_id'], 'metadata': {'tags': ['tla-hd']}, 'max_budget': 1})
        if isinstance(data, dict):
            key = data.get('key')  # Retain for cleanup even if another assertion fails.
        require(status == 200 and bool(key), 'ephemeral_credential_create_failed')
        status, info = http('/key/info?key=' + urllib.parse.quote(key, safe=''), master)
        require(status == 200 and info['info']['metadata']['tags'] == ['tla-hd']
                and info['info']['models'] == ['tla-hd-mock']
                and info['info']['key_alias'] == report['run_id'], 'ephemeral_credential_readback_failed')
        report['credential_created_and_readback'] = True
        with patch.object(llm, 'record_model_call', capture), \
             patch.object(llm.litellm, 'acompletion', guarded_completion), \
             patch.object(httpx.AsyncClient, 'send', wire_send), \
             patch.object(smtplib, 'SMTP_SSL', no_smtp), \
             patch.object(smtplib, 'SMTP', no_smtp), \
             patch.object(llm, 'settings', settings()):
            report['gateway_http_trace'] = wire
            stage = 'baseline'
            await batch(stage, 'gateway')  # Fallback OFF cannot mask a broken baseline.
            for helper in HELPERS:
                await invoke('missing-' + helper, helper, failure=True, missing=True)
            llm.settings = settings(enabled=True, credential='invalid-test-credential')
            for helper in HELPERS[:2]:
                await invoke('invalid-' + helper, helper, failure=True)
            llm.settings = settings()
            stage = 'one_proxy_down'
            await stop(SECOND)
            await batch(stage, 'gateway')
            stage = 'both_proxies_down'
            await stop(FIRST)
            require(state(LB)['Running'] is True, 'lb_not_running_during_proxy_fault')
            await batch(stage + '-disabled', failure=True)
            llm.settings = settings(enabled=True)
            await batch(stage + '-enabled', 'direct_fallback')
            await restore(FIRST)
            await restore(SECOND)
            docker(*RELOAD_COMMAND)
            await ready(LB)
            stage = 'proxy_recovery'
            await batch(stage, 'gateway')
            stage = 'lb_down'
            await stop(LB)
            llm.settings = settings()
            await batch(stage + '-disabled', failure=True)
            llm.settings = settings(enabled=True)
            await batch(stage + '-enabled', 'direct_fallback')
            stage = 'direct_failure'
            await batch(stage, 'direct_fallback', failure=True, direct_failure=True)
            await restore(LB)
            stage = 'recovery'
            await batch(stage, 'gateway')
            stage = 'second_outage'
            await stop(LB)
            await batch(stage, 'direct_fallback')
            await restore(LB)
            stage = 'final_recovery'
            await batch(stage, 'gateway')
            require(report['guards']['blocked_egress_count'] == 0, 'unexpected_egress_attempted')
        rows = report['ledger_rows']
        require(len({r['operation_id'] for r in rows}) == len(rows), 'operation_ids_not_unique')
        require(len({r['call_id'] for r in rows}) == len(rows) == len(responses), 'response_ids_not_unique')
        gateway = {r['call_id']: r for r in rows if r['route'] == 'gateway'}
        direct_ids = {r['call_id'] for r in rows if r['route'] == 'direct_fallback'}
        sql = spend_query(report['run_id'], set(gateway) | direct_ids)
        deadline = time.monotonic() + 120
        while True:
            spend = json.loads(docker(*SQL_PREFIX, sql))
            if set(gateway) <= {r['request_id'] for r in spend} or time.monotonic() >= deadline:
                break
            await asyncio.sleep(2)
        report['spend_logs'] = spend
        require(len({r['request_id'] for r in spend}) == len(spend), 'duplicate_spend_ids')
        by_id = {r['request_id']: r for r in spend}
        require(set(gateway) <= by_id.keys(), 'spend_flush_timeout')
        require(not direct_ids & by_id.keys(), 'direct_response_in_gateway_spend')
        for response_id, row in gateway.items():
            log = by_id[response_id]
            require(log['end_user'] == row['username_snapshot'], 'spend_user_mismatch')
            require(all(log[f] == row[f] for f in ('prompt_tokens', 'completion_tokens', 'total_tokens')),
                    'spend_tokens_mismatch')
            require('tla-hd' in log['request_tags'], 'spend_agent_tag_missing')
        extra = [r for r in spend if r['request_id'] not in gateway]
        report['unmatched_gateway_spend'] = extra
        require(not any(r['status'] == 'success' or r['total_tokens'] for r in extra), 'unmatched_successful_spend')
        trace = [json.loads(line) for line in docker(*TRACE_COMMAND).splitlines() if line.strip()]
        trace = [r for r in trace if r.get('user', '').startswith(report['run_id'] + '.')
                 and r.get('path') == '/v1/chat/completions']
        report['lb_trace'] = trace
        received_counts = Counter((r['user'], int(r['status'])) for r in trace)
        answered_counts = Counter((r['user'], r['status']) for r in wire if r['status'] is not None)
        require(not answered_counts - received_counts, 'lb_wire_response_missing')
        unreturned = received_counts - answered_counts
        pending = Counter(r['user'] for r in wire if r['status'] is None)
        unreturned_users = Counter()
        for (user, status), count in unreturned.items():
            require(status in (499, 502, 503, 504), 'lb_unexpected_unreturned_status')
            unreturned_users[user] += count
        require(not unreturned_users - pending, 'lb_wire_count_mismatch')
        report['ambiguous_gateway_http'] = [r for r in wire if r['status'] is None]
        # Cancellation can reach LB as 499 after OCR cancels its failed-page sibling.
        report['lb_unreturned_requests'] = [dict(user=user, status=status, count=count)
            for (user, status), count in unreturned.items()]
        require(Counter(r['user'] for r in trace if int(r['status']) == 200) ==
                Counter(r['username_snapshot'] for r in gateway.values()), 'lb_success_count_mismatch')
        baseline = {r['upstream'].split(', ')[-1] for r in trace
                    if '.user-baseline-' in r['user'] and int(r['status']) == 200}
        single = {r['upstream'].split(', ')[-1] for r in trace
                  if '.user-one_proxy_down-' in r['user'] and int(r['status']) == 200}
        require(len(baseline) == 2 and len(single) == 1 and single <= baseline, 'proxy_distribution_mismatch')
        report['upstreams'] = {'baseline': sorted(baseline), 'one_proxy_down': sorted(single)}
        report['reconciliation'] = {'gateway_response_ids_matched': len(gateway),
            'synthetic_direct_ids_absent_at_readback': len(direct_ids),
            'unmatched_failed_spend': len(extra), 'gateway_http_attempts': len(wire),
            'lb_received_requests': len(trace), 'direct_http_count': 'NOT MEASURED: SDK mock boundary'}
        report['result'] = 'PASS'
    finally:
        # Attempt every restoration even if a previous restoration fails.
        cleanup_errors = []
        for container in (FIRST, SECOND, LB):
            if container not in faulted:
                continue
            try:
                await restore(container)
            except BaseException:
                cleanup_errors.append('restore_failed:' + container)
        if key:
            try:
                await ready(LB)
                status, _ = http('/key/delete', master, {'keys': [key]})
                read_status, _ = http('/key/info?key=' + urllib.parse.quote(key, safe=''), master)
                report['credential_cleanup'] = {'delete_status': status, 'readback_status': read_status}
                require(status == 200 and read_status == 404, 'credential_delete_not_verified')
            except BaseException:
                cleanup_errors.append('credential_cleanup_unverified_expires_1h')
        final_health = {}
        for container in CONTAINERS:
            try:
                final_health[container] = 'healthy' if health(container) else 'NOT_HEALTHY'
            except BaseException:
                final_health[container] = 'UNKNOWN'
        report['final_health'] = final_health
        if any(value != 'healthy' for value in final_health.values()):
            cleanup_errors.append('final_health_not_verified')
        report['cleanup_errors'] = cleanup_errors
        if cleanup_errors:
            report['result'] = 'FAIL'


def main():
    report = {'run_id': 'law-fallback-' + secrets.token_hex(6), 'result': 'BLOCKED',
        'endpoint': BASE, 'scope': 'analysis/chat + real two-page scanned-PDF OCR, two concurrent users; SDK/LB/two mock proxies',
        'limitations': ['Direct provider is MOCK at litellm.acompletion, not real Gemini',
            'SMTP disabled; any SMTP constructor attempt fails the harness',
            'Actual ledger builder only; no application DB persistence or ETL/dashboard verification',
            'No authenticated HTTP E2E; synthetic UsageContext is injected',
            'Direct HTTP attempts NOT measured: synthetic litellm.acompletion SDK boundary',
            'Gateway HTTP send counted; LB receipt trace lacks body/response IDs, joined by synthetic user/status',
            'No Marker/parser, provider-real, production traffic, or capacity coverage']}
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    destination = ARTIFACTS / (report['run_id'] + '.json')
    original_cwd = Path.cwd()
    try:
        scratch_root = Path(os.environ.get('TMPDIR', 'D:/Hermes/profiles/api-gateway/cache/scratch'))
        require(scratch_root.is_dir(), 'scratch_directory_missing')
        os.environ['TMPDIR'] = str(scratch_root)
        tempfile.tempdir = str(scratch_root)
        scratch = tempfile.mkdtemp(prefix='law-fallback-no-env-', dir=scratch_root)
        os.chdir(scratch)
        try:
            # Suppress dependency diagnostic text; evidence never includes raw exceptions.
            logging.disable(logging.CRITICAL)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                install_guards(report)
                try:
                    app = load_app()
                except Exception as exc:
                    report['blocker'] = {'phase': 'application_preflight', 'error_type': type(exc).__name__,
                        'code': str(exc) if isinstance(exc, CheckFailed) else 'imports_not_ready'}
                    app = None
                if app is not None:
                    report['result'] = 'RUNNING'
                    asyncio.run(exercise(report, app))
        finally:
            os.chdir(original_cwd)
            import shutil
            shutil.rmtree(scratch, ignore_errors=True)
    except BaseException as exc:
        report['result'] = 'FAIL'
        report['failure'] = {'error_type': type(exc).__name__,
                    'code': str(exc) if isinstance(exc, (CheckFailed, PermissionError)) else 'unexpected_failure_redacted'}
        import traceback
        report['failure']['frames'] = [dict(file=Path(f.filename).name, line=f.lineno, function=f.name)
                                               for f in traceback.extract_tb(exc.__traceback__)]
    finally:
        os.chdir(original_cwd)
        report['totals'] = {'stages': len(report.get('stages', [])),
            'sdk_attempts': dict(Counter(a['route'] for a in report.get('attempts', []))),
            'ledger_rows': len(report.get('ledger_rows', [])), 'smtp_attempts': len(report.get('smtp', []))}
        encoded = json.dumps(report, indent=2)
        require(all(sentinel not in encoded for sentinel in (DIRECT_SENTINEL, SMTP_SENTINEL, CONTENT_SENTINEL)),
                'evidence_sensitive_data')
        temporary = destination.with_suffix('.pending.json')
        temporary.write_text(encoded, encoding='utf-8')
        os.replace(temporary, destination)
        print(json.dumps({'result': report['result'], 'evidence': str(destination),
                          'totals': report['totals'], 'blocker': report.get('blocker'),
                          'failure': report.get('failure'), 'cleanup_errors': report.get('cleanup_errors')}))
    return {'PASS': 0, 'FAIL': 1, 'BLOCKED': 2}.get(report['result'], 1)


def self_check():
    """Exercise guards without app imports, connecting sockets or running Docker."""
    sql = spend_query('law-fallback-0123456789ab', {'chatcmpl-test', 'mock-direct-test'})
    allowed = [TRACE_COMMAND, RELOAD_COMMAND, SQL_PREFIX + (sql,),
               ('stop', '--time', '2', FIRST), ('start', SECOND)]
    denied = [('stop', '--time', '2', DB), ('start', 'dashboard'),
              ('exec', LB, 'sh', '-c', 'true'), SQL_PREFIX + ('SELECT 1;',),
              SQL_PREFIX + (sql + ' DROP TABLE x;',), ('compose', 'down')]
    for command in allowed:
        require(docker_allowed(command), 'self_check_allow')
    for command in denied:
        require(not docker_allowed(command), 'self_check_deny')
    try:
        spend_query('law-fallback-0123456789ab', {"id'); DELETE FROM x;--"})
    except CheckFailed:
        pass
    else:
        raise CheckFailed('self_check_sql_injection')
    os.environ['TMPDIR'] = 'D:/Hermes/profiles/api-gateway/cache/scratch'
    os.environ['SMOKE_STATE_FILE'] = os.environ['TMPDIR'] + '/tla-gateway-smoke-state.json'
    os.environ['GEMINI_API_KEY_1'] = 'discard-me'
    report = {}
    install_guards(report)
    require(os.environ['TMPDIR'].endswith('/scratch') and os.environ.get('SMOKE_STATE_FILE')
            and 'GEMINI_API_KEY_1' not in os.environ, 'self_check_env')
    for command in allowed:
        sys.audit('subprocess.Popen', 'docker', ['docker', *command], None, None)
        sys.audit('subprocess.Popen', 'docker', subprocess.list2cmdline(['docker', *command]), None, None)
        sys.audit('subprocess.Popen', None, subprocess.list2cmdline(['docker', *command]), None, None)
    for event, args in [
        ('open', ('D:/law_insight/.env', 'r', 0)),
        ('socket.connect', (None, ('8.8.8.8', 443))),
        ('socket.getaddrinfo', ('provider.invalid', 443, 0, 0, 0)),
        ('subprocess.Popen', ('docker', ['docker', 'compose', 'down'], None, None)),
    ]:
        try:
            sys.audit(event, *args)
        except PermissionError:
            pass
        else:
            raise CheckFailed('self_check_audit_denial')
    require(not any(name == 'app' or name.startswith('app.') for name in sys.modules), 'self_check_app_import')
    print(json.dumps({'result': 'PASS', 'scope': 'offline guard self-check; no runtime or app imports'}))
    return 0


if __name__ == '__main__':
    if sys.argv[1:] == ['--self-check']:
        raise SystemExit(self_check())
    require(not sys.argv[1:], 'unsupported_arguments')
    raise SystemExit(main())
