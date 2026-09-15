"""Isolated real-SDK LB fault test for Ralli; direct provider/SMTP are MOCK boundaries.

Run with D:/rangdong-chatbot/.venv-gateway-test/Scripts/python.exe.
Exit 0=PASS, 1=FAIL, 2=BLOCKED.
Owns only this script and ralli-fallback-*.json evidence. No app DB writes.
"""
from __future__ import annotations

import asyncio
from collections import Counter
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

ROOT = Path(__file__).resolve().parent
BASE = 'http://127.0.0.1:4101'
LB = 'tla-gateway-smoke-gateway-lb-1'
SECOND = 'tla-gateway-smoke-gateway2-1'
CONTAINERS = (LB, SECOND, 'tla-gateway-smoke-gateway-1', 'tla-gateway-smoke-db-1')
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
            or args in {('start', c) for c in (LB, SECOND)}
            or args in {('stop', '--time', '2', c) for c in (LB, SECOND)})


def install_guards(report):
    # Do not inherit provider, SMTP, application DB, proxy, or cloud credentials.
    keep = {'SYSTEMROOT', 'WINDIR', 'PATH', 'PATHEXT', 'COMSPEC', 'TEMP', 'TMP',
            'LOCALAPPDATA', 'APPDATA', 'USERPROFILE', 'HOMEDRIVE', 'HOMEPATH',
            'PROGRAMDATA', 'PROGRAMFILES', 'PROGRAMFILES(X86)', 'OS',
            'PROCESSOR_ARCHITECTURE', 'NUMBER_OF_PROCESSORS'}
    clean = {k: v for k, v in os.environ.items() if k.upper() in keep}
    os.environ.clear()
    os.environ.update(clean)
    os.environ.update(LLM_MODE='gateway', LITELLM_LOCAL_MODEL_COST_MAP='True',
                      LITELLM_TELEMETRY='False', DO_NOT_TRACK='1',
                      PYTHONDONTWRITEBYTECODE='1', PYTHON_DOTENV_DISABLED='1',
                      DATABASE_URL='postgresql+asyncpg://mock:mock@127.0.0.1:9/mock')
    sys.dont_write_bytecode = True
    report['guards'] = {'dotenv_read_denial': True, 'dotenv_sources_disabled': True,
                        'only_application_egress': BASE, 'direct_boundary': 'MOCK',
                        'smtp_boundary': 'MOCK', 'blocked_egress_count': 0}

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
            raw = args[1]
            if isinstance(raw, str):
                import shlex
                argv = shlex.split(raw)
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
    try:
        from pydantic_settings import BaseSettings

        def sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
            return init_settings, env_settings

        BaseSettings.settings_customise_sources = classmethod(sources)
    except ImportError:
        pass


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
    sys.path.insert(0, 'D:/rangdong-chatbot')
    from src.core.gateway_settings import Settings
    from src.core import llm, token_logger, email_alerts
    require('gateway_fallback_enabled' in Settings.model_fields, 'fallback_settings_missing')
    require('gateway_fallback_enabled' in inspect.getsource(llm), 'routing_implementation_missing')
    require(all(name in inspect.signature(token_logger.build_token_usage_log).parameters
                for name in ('route', 'fallback_reason', 'operation_id')), 'ledger_metadata_missing')
    require(callable(email_alerts.schedule_gateway_alert), 'alert_schedule_missing')
    require(callable(email_alerts.drain_gateway_alerts), 'alert_drain_missing')
    return Settings, llm, token_logger, email_alerts


async def exercise(report, app):
    Settings, llm, ledger, alerts = app
    import smtplib
    import run as smoke
    require(smoke.STATE.is_file(), 'existing_mock_state_missing')
    master = smoke.state()['SMOKE_MASTER_KEY']
    key = None
    faulted = set()
    report.update(stages=[], attempts=[], ledger_rows=[], smtp=[])
    original_completion = llm.litellm.acompletion
    expected = {}
    fail_operations = set()
    messages = []
    stage = 'preflight'
    defaults = Settings(_env_file=None, llm_mode='gateway')
    require(defaults.gateway_fallback_enabled is False, 'unsafe_fallback_default')
    require(defaults.gateway_fallback_max_attempts == 1, 'unsafe_attempt_default')
    require(defaults.gateway_fallback_timeout_seconds == 30, 'timeout_default_mismatch')
    require(defaults.alert_email_enabled is False, 'unsafe_email_default')

    def settings(enabled=True, credential=None):
        return Settings(_env_file=None, llm_mode='gateway', gateway_base_url=BASE + '/v1',
            gateway_virtual_key=credential if credential is not None else key,
            gateway_model='ralli-mock', gateway_timeout_seconds=3,
            gateway_fallback_enabled=enabled, gateway_fallback_max_attempts=1,
            gateway_fallback_timeout_seconds=5, gemini_api_key_1=DIRECT_SENTINEL,
            gemini_api_key_2='', gemini_api_key_3='', alert_email_enabled=True,
            alert_smtp_host='smtp.mock.invalid', alert_smtp_port=465,
            alert_smtp_user='mock-sender@example.invalid', alert_smtp_password=SMTP_SENTINEL,
            alert_email_from='mock-sender@example.invalid', alert_email_to='mock-ops@example.invalid',
            alert_email_cooldown_seconds=86400, alert_smtp_timeout_seconds=2)

    class MockSMTP:
        def __init__(self, host, port, *args, **kwargs):
            require(host == 'smtp.mock.invalid' and port == 465, 'smtp_destination_mismatch')
            require(0 < kwargs.get('timeout', 0) <= 2, 'smtp_timeout_unbounded')
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def login(self, user, password):
            require(user == 'mock-sender@example.invalid' and password == SMTP_SENTINEL, 'smtp_credential_mismatch')
        def send_message(self, message, *args, **kwargs):
            raw = message.as_string()
            for forbidden in (CONTENT_SENTINEL, DIRECT_SENTINEL, SMTP_SENTINEL, master, key,
                              'Authorization', 'Bearer ', 'Traceback', 'X-User'):
                require(not forbidden or forbidden.lower() not in raw.lower(), 'email_sensitive_data')
            require('ralli' in raw.lower(), 'email_application_name_mismatch')
            body = message.get_body(preferencelist=('plain',)) if message.is_multipart() else message
            text = body.get_content()
            require(any(reason in text for reason in SAFE_REASONS), 'email_reason_missing')
            messages.append(text)
            report['smtp'].append({'boundary': 'MOCK SMTP_SSL.send_message',
                                   'sanitized_actual_message': True, 'stage': stage})
            return {}
        def quit(self):
            return 221, b'MOCK'

    async def guarded_completion(**kwargs):
        ctx = ledger.get_usage_context()
        require(ctx is not None, 'transport_identity_missing')
        operation = ctx.session_id
        if kwargs.get('api_base') == BASE + '/v1':
            require(kwargs['model'] == 'openai/ralli-mock', 'gateway_model_mismatch')
            require(kwargs.get('extra_headers') == {'X-User': ctx.username}, 'gateway_identity_header_mismatch')
            require(kwargs.get('user') == ctx.username and kwargs.get('num_retries') == 0, 'gateway_retry_or_user_mismatch')
            report['attempts'].append({'operation': operation, 'route': 'gateway', 'user': ctx.username})
            return await original_completion(**kwargs)  # REAL SDK and REAL LB socket.
        require(kwargs.get('model', '').startswith('gemini/'), 'direct_model_mismatch')
        require(not any(k in kwargs for k in ('api_base', 'extra_headers', 'headers', 'user', 'metadata')),
                'direct_gateway_metadata_leaked')
        require(kwargs.get('api_key') == DIRECT_SENTINEL, 'direct_credential_mismatch')
        require(kwargs.get('num_retries') == 0 and 0 < kwargs.get('timeout', 0) <= 5, 'direct_unbounded')
        require(key not in json.dumps(kwargs), 'direct_virtual_credential_leaked')
        report['attempts'].append({'operation': operation, 'route': 'direct_fallback',
                                   'user': ctx.username, 'boundary': 'MOCK litellm.acompletion'})
        await asyncio.sleep(0)
        if operation in fail_operations:
            raise RuntimeError('MOCK_DIRECT_FAILURE')
        return llm._LiteLLM.ModelResponse(id='mock-direct-' + secrets.token_hex(8),
            model=kwargs['model'], choices=[{'index': 0, 'message': {'role': 'assistant',
            'content': 'mock-direct-ok'}, 'finish_reason': 'stop'}],
            usage={'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18})

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
        require(row.fallback_reason in SAFE_REASONS if row.route == 'direct_fallback'
                else row.fallback_reason is None, 'ledger_reason_mismatch')
        report['ledger_rows'].append({name: getattr(row, name) for name in (
            'call_id', 'route', 'fallback_reason', 'operation_id', 'user_id', 'username_snapshot',
            'company_id_snapshot', 'unit_id_snapshot', 'session_id', 'function_name',
            'prompt_tokens', 'completion_tokens', 'total_tokens')})
        return True

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
        error = None
        with contextlib.nullcontext() if missing else ledger.token_usage_context(**identity):
            try:
                if helper == 'call_llm':
                    result = await asyncio.wait_for(llm.call_llm('agent1', CONTENT_SENTINEL,
                                                                CONTENT_SENTINEL, max_tokens=16), 20)
                else:
                    result = await asyncio.wait_for(llm.call_llm_chat('agent2', CONTENT_SENTINEL,
                        [{'role': 'user', 'content': CONTENT_SENTINEL}], max_tokens=16), 20)
                require(not failure, 'unexpected_request_success')
                require(result.text == ('mock-direct-ok' if route == 'direct_fallback' else 'gateway-smoke-ok'),
                        'response_mismatch')
            except CheckFailed:
                raise
            except Exception as exc:
                require(failure, 'unexpected_request_failure')
                error = type(exc).__name__
                if missing:
                    require(isinstance(exc, ValueError), 'missing_identity_wrong_error')
                if label.startswith('invalid'):
                    require(isinstance(exc, llm._LiteLLM.AuthenticationError), 'invalid_credential_wrong_error')
        attempts = [a for a in report['attempts'] if a['operation'] == operation]
        counts = Counter(a['route'] for a in attempts)
        require(counts['gateway'] == (0 if missing else 1), 'gateway_attempt_count')
        require(counts['direct_fallback'] == (1 if route == 'direct_fallback' else 0), 'fallback_attempt_count')
        rows = [r for r in report['ledger_rows'] if r['session_id'] == operation]
        require(len(rows) == (0 if failure else 1), 'ledger_row_count')
        if rows:
            require(rows[0]['route'] == route, 'result_route_mismatch')
        report['stages'].append({'name': label, 'helper': helper, 'expected_route': route,
            'expected_failure': failure, 'error_type': error, 'sdk_attempts': dict(counts),
            'elapsed_seconds': time.monotonic() - started, 'result': 'PASS'})

    async def stop(container):
        faulted.add(container)
        docker('stop', '--time', '2', container)
        require(state(container)['Running'] is False, 'fault_readback_failed')

    async def restore(container):
        docker('start', container)
        await ready(container)
        faulted.discard(container)

    try:
        require(all(health(c) for c in CONTAINERS), 'initial_stack_not_healthy')
        require(http('/health/readiness')[0] == 200, 'lb_not_ready')
        report['initial_health'] = {c: 'healthy' for c in CONTAINERS}
        status, data = http('/key/generate', master, {'models': ['ralli-mock'], 'duration': '1h',
            'key_alias': report['run_id'], 'metadata': {'tags': ['ralli']}, 'max_budget': 1})
        if isinstance(data, dict):
            key = data.get('key')
        require(status == 200 and bool(key), 'ephemeral_credential_create_failed')
        status, info = http('/key/info?key=' + urllib.parse.quote(key, safe=''), master)
        require(status == 200 and info['info']['metadata']['tags'] == ['ralli']
                and info['info']['models'] == ['ralli-mock']
                and info['info']['key_alias'] == report['run_id'], 'ephemeral_credential_readback_failed')
        report['credential_created_and_readback'] = True
        with patch.object(llm, 'record_model_call', capture), \
             patch.object(llm.litellm, 'acompletion', guarded_completion), \
             patch.object(smtplib, 'SMTP_SSL', MockSMTP), \
             patch.object(smtplib, 'SMTP', side_effect=CheckFailed('unexpected_smtp_mode')), \
             patch.object(llm, 'settings', settings()):
            stage = 'healthy'
            await invoke('healthy-standard', 'call_llm', 'gateway')
            await invoke('healthy-chat', 'call_llm_chat', 'gateway')
            await drain()
            require(len(messages) == 0, 'healthy_alert_unexpected')
            for helper in ('call_llm', 'call_llm_chat'):
                await invoke('missing-' + helper, helper, failure=True, missing=True)
            llm.settings = settings(credential='invalid-sk-key')
            for helper in ('call_llm', 'call_llm_chat'):
                await invoke('invalid-' + helper, helper, failure=True)
            llm.settings = settings()
            await drain()
            require(len(messages) == 0, 'identity_or_auth_alert_unexpected')
            stage = 'second_proxy_down'
            await stop(SECOND)
            await invoke('second-proxy-down', 'call_llm_chat', 'gateway')
            await restore(SECOND)
            await drain()
            require(len(messages) == 0, 'proxy_failover_alert_unexpected')
            stage = 'lb_down_disabled'
            await stop(LB)
            llm.settings = settings(enabled=False)
            for helper in ('call_llm', 'call_llm_chat'):
                await invoke('disabled-' + helper, helper, failure=True)
            await drain()
            require(len(messages) == 0, 'disabled_alert_unexpected')
            stage = 'lb_down_enabled'
            llm.settings = settings()
            # Three sequential calls AND three concurrent calls prove per-call budget.
            for index in range(3):
                await invoke('successive-' + str(index), 'call_llm' if index % 2 == 0 else 'call_llm_chat',
                             'direct_fallback')
            await asyncio.gather(*(invoke('concurrent-' + str(index),
                'call_llm' if index % 2 == 0 else 'call_llm_chat', 'direct_fallback') for index in range(3)))
            await drain()
            require(len(messages) == 1, 'outage_mail_dedup_failed')
            for helper in ('call_llm', 'call_llm_chat'):
                await invoke('direct-failure-' + helper, helper, 'direct_fallback', failure=True,
                             direct_failure=True)
            await drain()
            require(len(messages) == 1, 'direct_failure_mail_storm')
            stage = 'recovery'
            await restore(LB)
            await invoke('recovery-standard', 'call_llm', 'gateway')
            await invoke('recovery-chat', 'call_llm_chat', 'gateway')
            stage = 'second_outage'
            await stop(LB)
            await invoke('second-outage', 'call_llm_chat', 'direct_fallback')
            await drain()
            require(len(messages) == 1, 'cooldown_did_not_suppress_second_outage')
            fallback_ids = {r['operation_id'] for r in report['ledger_rows'] if r['route'] == 'direct_fallback'}
            require(len(fallback_ids) == sum(r['route'] == 'direct_fallback' for r in report['ledger_rows']),
                    'fallback_operation_ids_not_unique')
            require(any(str(operation) in messages[0] for operation in fallback_ids), 'email_correlation_missing')
            require(report['guards']['blocked_egress_count'] == 0, 'unexpected_egress_attempted')
            await restore(LB)
        report['result'] = 'PASS'
    finally:
        cleanup_errors = []
        for container in tuple(faulted):
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
                require(status == 200 and read_status in (400, 404), 'credential_delete_not_verified')
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
    report = {'run_id': 'ralli-fallback-' + secrets.token_hex(6), 'result': 'BLOCKED',
        'endpoint': BASE, 'scope': 'real core helpers + real SDK + isolated LB/two mock proxies',
        'limitations': ['Direct provider is MOCK at litellm.acompletion, not real Gemini',
            'SMTP is MOCK at SMTP_SSL.send_message, no real email delivered',
            'Actual ledger builder only; no application DB persistence or ETL/dashboard verification',
            'No authenticated HTTP E2E; synthetic UsageContext is injected',
            'No SpendLogs reconciliation; direct absence from SpendLogs is not verified',
            'No OCR/Marker/parser, production traffic, or capacity coverage']}
    destination = ROOT / (report['run_id'] + '.json')
    original_cwd = Path.cwd()
    try:
        scratch = tempfile.mkdtemp(prefix='ralli-fallback-no-env-')
        os.chdir(scratch)
        try:
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
            'code': str(exc) if isinstance(exc, CheckFailed) else 'unexpected_failure_redacted'}
    finally:
        os.chdir(original_cwd)
        report['totals'] = {'stages': len(report.get('stages', [])),
            'sdk_attempts': dict(Counter(a['route'] for a in report.get('attempts', []))),
            'ledger_rows': len(report.get('ledger_rows', [])), 'mock_emails': len(report.get('smtp', []))}
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


if __name__ == '__main__':
    raise SystemExit(main())
