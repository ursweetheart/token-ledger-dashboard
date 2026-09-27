"""Connection administration is disabled unless explicitly configured."""
import json
import secrets
import urllib.request
import urllib.error
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .connection_config import Conflict, validate_budget
from .connection_store import ConnectionStore


def router(settings):
    enabled = settings('CONNECTIONS_ENABLED') == '1'
    admin = settings('CONNECTION_ADMIN_KEY')
    worker_url = settings('CONNECTION_WORKER_URL')
    worker_key = settings('CONNECTION_WORKER_KEY')
    dsn = settings('CONNECTION_ADMIN_DSN')
    if enabled:
        if not all((admin, worker_url, worker_key, dsn)) or admin == settings('DASHBOARD_KEY'):
            raise SystemExit('Connection administration needs separate admin credential, DSN and worker configuration')
        parsed = urlsplit(worker_url)
        if parsed.scheme != 'https' and parsed.hostname not in {'127.0.0.1', 'localhost', '::1'}:
            raise SystemExit('Connection worker requires HTTPS outside loopback')
    api = APIRouter(prefix='/api/gateway-connections', tags=['Gateway connections'])
    bearer = HTTPBearer(auto_error=False)
    store = ConnectionStore(dsn) if enabled else None

    def authorize(cred: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if cred is None:
            raise HTTPException(401, 'Administration credential required')
        if not enabled:
            raise HTTPException(503, 'Connection administration is disabled')
        if cred.scheme.lower() != 'bearer' or not secrets.compare_digest(cred.credentials.encode(), admin.encode()):
            # Existing dashboard credential grants no connection authority.
            dashboard = settings('DASHBOARD_KEY')
            status = 403 if dashboard and secrets.compare_digest(cred.credentials.encode(), dashboard.encode()) else 401
            raise HTTPException(status, 'Connection administration credential required')
        return 'connection-admin'

    def execute(fn):
        try:
            return fn()
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from None
        except KeyError:
            raise HTTPException(404, 'Connection or operation not found') from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    def rpc(action, data):
        request = urllib.request.Request(worker_url.rstrip('/') + '/rpc/' + action,
            data=json.dumps(data).encode(), headers={'Authorization': 'Bearer ' + worker_key,
                                                    'Content-Type': 'application/json'})
        try:
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            with urllib.request.build_opener(NoRedirect).open(request, timeout=35) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            # Worker error bodies are already sanitized; never forward raw upstream responses.
            try:
                detail = json.load(exc).get('detail', 'Worker rejected operation')
            except (ValueError, TypeError):
                detail = 'Worker rejected operation'
            raise HTTPException(exc.code, detail) from None
        except (OSError, ValueError):
            raise HTTPException(503, 'Worker unavailable; inspect operation status before retrying') from None

    @api.get('')
    def listing(actor=Depends(authorize)):
        return execute(store.list_profiles)

    @api.post('/secrets')
    def secret(body: dict, actor=Depends(authorize)):
        if set(body) != {'value'}:
            raise HTTPException(422,'Provide only a provider secret value')
        result = execute(lambda: rpc('secret',body))
        with store.transaction() as cur:
            store.audit(cur,'__secrets__',actor,'import-secret',result)
        return result

    @api.post('')
    def save(body: dict, actor=Depends(authorize)):
        return execute(lambda: store.save(body.get('profile'), body.get('expected_revision'), actor))

    @api.get('/operations/{operation_id}')
    def operation(operation_id: str, actor=Depends(authorize)):
        return execute(lambda: store.operation(operation_id))

    @api.get('/{code}')
    def detail(code: str, actor=Depends(authorize)):
        return execute(lambda: store.detail(code))

    @api.post('/{code}/preview')
    def preview(code: str, body: dict, actor=Depends(authorize)):
        return execute(lambda: rpc('preview', {'code': code, 'revision': body.get('expected_revision')}))

    @api.post('/{code}/apply')
    def apply(code: str, body: dict, actor=Depends(authorize)):
        if set(body) - {'expected_revision','idempotency_key','preview_hash'}:
            raise HTTPException(422, 'Unknown apply fields')
        op = execute(lambda: store.enqueue(code, 'apply', body.get('expected_revision'),
                     body.get('idempotency_key'), actor, {'preview_hash': body.get('preview_hash')}))
        return {'operation': op}  # Worker consumes queued applies from PostgreSQL.

    @api.post('/{code}/keys')
    def issue(code: str, body: dict, actor=Depends(authorize)):
        budget = execute(lambda: validate_budget(body.get('budget')))
        op = execute(lambda: store.enqueue(code, 'issue', body.get('expected_revision'),
                     body.get('idempotency_key'), actor, {'budget': budget}))
        return execute(lambda: rpc('issue', {'operation_id': str(op['id'])}))

    @api.post('/{code}/revoke')
    def revoke(code: str, body: dict, actor=Depends(authorize)):
        aliases = body.get('key_aliases')
        if not isinstance(aliases, list) or not aliases or any(not isinstance(x, str) for x in aliases):
            raise HTTPException(422, 'Choose managed key aliases to revoke')
        op = execute(lambda: store.enqueue(code, 'revoke', body.get('expected_revision'),
                     body.get('idempotency_key'), actor, {'key_aliases': aliases}))
        return execute(lambda: rpc('revoke', {'operation_id': str(op['id'])}))

    @api.post('/{code}/verify')
    def verify(code: str, body: dict, actor=Depends(authorize)):
        if body.get('accept_cost') is not True or not isinstance(body.get('virtual_key'), str):
            raise HTTPException(422, 'Provide an agent Virtual Key and accept possible provider cost')
        op = execute(lambda: store.enqueue(code, 'verify', body.get('expected_revision'),
                     body.get('idempotency_key'), actor, {}))
        return execute(lambda: rpc('verify', {'operation_id': str(op['id']), 'virtual_key': body['virtual_key']}))

    @api.post('/{code}/external-verify')
    def external_verify(code: str, body: dict, actor=Depends(authorize)):
        request_id = body.get('request_id')
        if not isinstance(request_id,str) or not 1 <= len(request_id) <= 200:
            raise HTTPException(422,'Provide the request ID observed from the deployed agent')
        op = execute(lambda: store.enqueue(code,'verify',body.get('expected_revision'),
                    body.get('idempotency_key'),actor,{'external_request_id':request_id}))
        return execute(lambda: rpc('external-verify',{'operation_id':str(op['id'])}))

    @api.post('/{code}/template')
    def template(code: str, body: dict, actor=Depends(authorize)):
        if body.get('context') not in ('host','docker'):
            raise HTTPException(422, 'Select host or docker')
        return execute(lambda: rpc('template', {'code': code, 'context': body['context']}))

    @api.post('/{code}/budget')
    def budget(code: str, body: dict, actor=Depends(authorize)):
        value = execute(lambda: validate_budget(body.get('budget')))
        op = execute(lambda: store.enqueue(code,'budget',body.get('expected_revision'),
                     body.get('idempotency_key'),actor,{'budget':value,'key_alias':body.get('key_alias')}))
        return execute(lambda: rpc('budget',{'operation_id':str(op['id'])}))

    @api.post('/{code}/reconcile')
    def reconcile(code: str, body: dict, actor=Depends(authorize)):
        if set(body)-{'expected_revision','accept_hash'}:
            raise HTTPException(422,'Unknown reconciliation fields')
        return execute(lambda: rpc('reconcile',{'code':code,'revision':body.get('expected_revision'),
                                               'accept_hash':body.get('accept_hash')}))

    @api.post('/{code}/recover')
    def recover(code: str, body: dict, actor=Depends(authorize)):
        op = execute(lambda: store.enqueue(code,'recover',body.get('expected_revision'),
                    body.get('idempotency_key'),actor,{}))
        return execute(lambda: rpc('recover',{'operation_id':str(op['id'])}))

    return api
