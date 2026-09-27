"""Trusted host worker. Run separately; never mount Docker socket into the API.

All paths and upstream endpoints are operator configuration, never HTTP input.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json
import importlib.util
import os
import re
import secrets
import stat
import shutil
import sys
import subprocess
import tempfile
import time
import urllib.request
import urllib.error
import urllib.parse
import uuid

import psycopg2
from psycopg2.extras import Json, RealDictCursor
import yaml
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from db import gateway_registry, connect
from .connection_store import ConnectionStore
from .connection_config import (Conflict, REF, digest, render_routes, render_registry,
    registry_row, quota_metadata, validate_budget, integration_template, route_id, load_yaml,
    deployment_env_digest)

LOCK = 74120926


def restricted_directory(path):
    if os.name != 'nt':
        if path.stat().st_mode & 0o077:
            raise ValueError('Secret directory must have mode 0700')
        return
    command = ("$current=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
               "$acl=Get-Acl -LiteralPath $env:CONNECTION_ACL_TARGET; "
               "$allowed=@($current,'S-1-5-18','S-1-5-32-544'); "
               "if($acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value -eq $current){$allowed += 'S-1-3-4'}; "
               "$bad=@($acl.Access | Where-Object { "
               "$_.AccessControlType -eq 'Allow' -and "
               "$allowed -notcontains $_.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value }); "
               "if($bad.Count -gt 0){exit 2}")
    result = subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',command],
        capture_output=True,timeout=10,env={**os.environ,'CONNECTION_ACL_TARGET':str(path)})
    if result.returncode:
        raise ValueError('Secret directory ACL must allow only worker, SYSTEM and Administrators')


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent)
    try:
        if os.name!='nt' and path.exists():
            os.chmod(temporary,stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(fd, 'wb') as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class Gateway:
    def __init__(self, url, master):
        self.url, self.master = url.rstrip('/'), master

    def call(self, path, data=None, key=None, query=None):
        if path not in {'/key/generate','/key/delete','/key/list','/key/update',
                        '/health/liveliness','/v1/chat/completions','/model/info'}:
            raise ValueError('Unsupported Gateway action')
        url = self.url + path
        if path == '/key/list':
            if query is None or set(query) != {'key_alias'}:
                raise ValueError('Key listing requires an exact alias filter')
            url += '?' + urllib.parse.urlencode({'return_full_object':'true','size':100,**query})
        request = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
            headers={'Authorization': 'Bearer ' + (key if key is not None else self.master),
                     'Content-Type': 'application/json'})
        try:
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, req, fp, code, msg, headers, newurl):
                    return None
            with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
                return {name.lower():value for name,value in response.headers.items()}, json.load(response)
        except urllib.error.HTTPError as exc:
            # Never include upstream body: LiteLLM can echo keys/provider params.
            raise RuntimeError(f'Gateway HTTP {exc.code}') from None
        except (OSError, ValueError):
            raise RuntimeError('Gateway unavailable or invalid response') from None

    def key(self, alias):
        _, result = self.call('/key/list',query={'key_alias':alias})
        keys = result.get('keys', []) if isinstance(result, dict) else result
        return next((k for k in keys if isinstance(k, dict) and k.get('key_alias') == alias), None)

    def revoke(self, alias):
        self.call('/key/delete', {'key_aliases': [alias]})
        if self.key(alias):
            raise RuntimeError('Key revocation is not confirmed')


class Worker:
    def __init__(self, root, state_dir, ledger_dsn, gateway_dsn, endpoints, master,
                 host_endpoint, docker_endpoint, network):
        self.root = Path(root).resolve()
        self.state = Path(state_dir).resolve()
        local_state = self.root / '.local' / 'connections'
        if self.state == self.root or (self.state.is_relative_to(self.root) and self.state != local_state):
            raise ValueError('CONNECTION_SECRET_DIR must be outside repository or .local/connections')
        if not self.state.is_dir():
            raise ValueError('Create the restricted secret directory before starting the worker')
        restricted_directory(self.state)
        self.store = ConnectionStore(ledger_dsn)
        self.ledger_dsn, self.gateway_dsn = ledger_dsn, gateway_dsn
        self.gateways = [Gateway(url, master) for url in endpoints]
        if len(self.gateways) != 2:
            raise ValueError('Configure exactly two Gateway endpoints')
        self.host_endpoint, self.docker_endpoint, self.network = host_endpoint, docker_endpoint, network
        self.paths = {'routes': self.root/'docker/gateway/config.gateway.yaml',
                      'registry': self.root/'config/gateway-agents.yaml',
                      'override': self.state/'compose.connections.yaml',
                      'environment': self.state/'managed.env',
                      'compose': self.root/'docker-compose.yml',
                      'deployment_env': self.root/'.env',
                      'preflight': self.root/'docker/gateway/entrypoint.sh'}

    @contextmanager
    def lock(self):
        cn = psycopg2.connect(self.ledger_dsn, connect_timeout=5)
        try:
            with cn.cursor() as cur:
                cur.execute('SELECT pg_try_advisory_lock(%s)', (LOCK,))
                if not cur.fetchone()[0]:
                    raise Conflict('Another deployment operation is running')
            yield
        finally:
            cn.close()

    def files(self):
        return {name: (deployment_env_digest(path.read_bytes()) if name == 'deployment_env'
                       else digest(path.read_bytes())) if path.exists() else None
                for name, path in self.paths.items()}

    def db_state(self, cn):
        with cn.cursor() as cur:
            cur.execute('SELECT g.code,g.name,g.is_running,r.user_mode,r.reporting_start_date '
                        'FROM dim_agent g JOIN gateway_agent_registry r ON r.agent_id=g.agent_id ORDER BY g.code')
            return digest(cur.fetchall())

    def baseline(self):
        with self.store.transaction() as cur:
            cur.execute('SELECT baseline FROM gateway_connection_deployment')
            return cur.fetchone()['baseline']

    def bootstrap(self):
        """Explicit operator command only: adopt file hashes, no route ownership."""
        with self.lock(), gateway_registry.operation_lock(self.ledger_dsn):
            with psycopg2.connect(self.ledger_dsn) as cn:
                baseline = {'files': self.files(), 'registry': self.db_state(cn), 'ownership': []}
            with self.store.transaction() as cur:
                cur.execute('SELECT baseline FROM gateway_connection_deployment FOR UPDATE')
                if cur.fetchone()['baseline']:
                    raise Conflict('Already bootstrapped; use reviewed drift reconciliation')
                cur.execute('UPDATE gateway_connection_deployment SET baseline=%s', (Json(baseline),))
        return {'bootstrapped': True}

    def secrets(self):
        values = {}
        path = self.paths['environment']
        if path.exists():
            for line in path.read_text(encoding='utf-8').splitlines():
                name, sep, value = line.partition('=')
                if not sep or not REF.fullmatch(name):
                    raise ValueError('Invalid managed secret file')
                # Values encoded as JSON-compatible quoted strings for Compose.
                values[name] = json.loads(value)
        return values

    def import_secret(self, value):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,4096}',value):
            raise ValueError('Invalid provider secret')
        with self.lock():
            baseline = self.baseline()
            if not baseline or self.files()['environment'] != baseline['files']['environment']:
                raise Conflict('Secret file drift; bootstrap or reconcile before importing a secret')
            reference = 'KEY_MANAGED_' + uuid.uuid4().hex.upper()
            values = self.secrets()
            values[reference] = value
            text = ''.join(name + '=' + json.dumps(secret) + '\n' for name, secret in sorted(values.items()))
            atomic_write(self.paths['environment'], text.encode())
            # Secret upload is deliberate state mutation; advance only this artifact hash.
            with self.store.transaction() as cur:
                cur.execute('SELECT baseline FROM gateway_connection_deployment FOR UPDATE')
                baseline = cur.fetchone()['baseline']
                if baseline:
                    baseline['files']['environment'] = self.files()['environment']
                    cur.execute('UPDATE gateway_connection_deployment SET baseline=%s', (Json(baseline),))
        return {'secret_ref': reference}

    def preview(self, code, revision, cn=None):
        profile = self.store.profile(code)
        if profile['revision'] != revision:
            raise Conflict('Profile revision changed')
        baseline = self.baseline()
        if not baseline:
            raise Conflict('Operator must bootstrap configuration ownership before preview')
        if self.files() != baseline['files']:
            raise Conflict('Configuration file drift; explicit reconciliation required')
        if cn is None:
            with psycopg2.connect(self.ledger_dsn) as read_cn:
                read_cn.set_session(readonly=True)
                return self.preview(code, revision, read_cn)
        if self.db_state(cn) != baseline['registry']:
            raise Conflict('Registry database drift; explicit reconciliation required')
        p = profile['draft']
        with self.store.transaction() as cur:
            cur.execute('SELECT applied FROM gateway_connection_profile WHERE code<>%s AND applied IS NOT NULL ORDER BY code', (code,))
            profiles = [r['applied'] for r in cur.fetchall()] + [p]
            cur.execute('SELECT catalog_key,openrouter_id FROM ref_model_catalog WHERE available=true')
            catalog = cur.fetchall()
        # New Gemini revisions may precede pricing catalog. Existing deployed upstream models are valid too.
        original = load_yaml(self.paths['routes'].read_text(encoding='utf-8-sig'))
        allowed = {r.get('litellm_params', {}).get('model') for r in original.get('model_list', [])}
        for row in catalog:
            for name in (row['catalog_key'], row['openrouter_id']):
                if name and name.startswith('google/'):
                    allowed.add('gemini/' + name.split('/',1)[1])
        if any(m['upstream'] not in allowed for m in p['models']):
            raise ValueError('Upstream model must be in the catalog or deployed model configuration')
        if p['secret_ref'] not in self.secrets():
            raise ValueError('Import provider secret before using its reference')
        routes, ownership = render_routes(original, profiles, baseline['ownership'])
        registry = render_registry(load_yaml(self.paths['registry'].read_text(encoding='utf-8-sig')), profiles)
        gateway_registry.apply_config(cn, gateway_registry.parse_config(yaml.safe_dump(registry)), True)
        # Include all applied profiles to invalidate previews after another agent is deployed.
        preview_hash = digest({'files': baseline['files'], 'registry': baseline['registry'],
                               'profiles': profiles, 'revision': revision})
        return {'preview_hash': preview_hash, 'revision': revision, 'profile': p,
                'routes': routes, 'registry': registry, 'ownership': ownership,
                'changes': {'agent': code, 'instances': ['litellm-1','litellm-2'],
                            'keys': 'issue separately after apply', 'shared_upstream':
                            sum(x['secret_ref'] == p['secret_ref'] for x in profiles) > 1}}

    def compose(self, *args):
        command = ['docker','compose','--project-directory',str(self.root),'-f',str(self.root/'docker-compose.yml')]
        if self.paths['override'].exists():
            command += ['-f',str(self.paths['override'])]
        command += list(args)
        result = subprocess.run(command, cwd=self.root, capture_output=True, timeout=180)
        if result.returncode:
            raise RuntimeError('Compose operation failed; inspect host logs privately')
        return result.stdout

    def rollout(self):
        for index, service in enumerate(('litellm-1','litellm-2')):
            self.compose('up','-d','--no-deps','--force-recreate',service)
            ready = False
            for _ in range(30):
                try:
                    self.gateways[index].call('/health/liveliness')
                    ready = True
                    break
                except RuntimeError:
                    time.sleep(1)
            if not ready:
                raise RuntimeError(f'{service} did not become healthy')
            # Confirm the recreated container reads the exact candidate file inode/content.
            content = self.compose('exec','-T',service,'cat','/app/config.yaml')
            if digest(content) != digest(self.paths['routes'].read_bytes()):
                raise RuntimeError('Gateway configuration revision mismatch')
            _, info = self.gateways[index].call('/model/info')
            loaded_ids = {str((r.get('model_info') or {}).get('id')) for r in info.get('data',[])}
            candidate = load_yaml(content.decode())
            expected_ids = {str((r.get('model_info') or {}).get('id')) for r in candidate.get('model_list',[])
                            if str((r.get('model_info') or {}).get('id','')).startswith('connection-')}
            if not expected_ids.issubset(loaded_ids):
                raise RuntimeError('Gateway has not loaded the managed route revision')
            required = self.secrets()
            # Values remain in memory and never become an exception or log body.
            raw = self.compose('exec','-T',service,'env').decode()
            effective = dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
            for reference in required:
                if effective.get(reference) != required[reference]:
                    raise RuntimeError('Gateway managed secret environment mismatch')

    def snapshot(self, operation_id):
        folder = self.state/'snapshots'/str(uuid.UUID(operation_id))
        if folder.exists():
            if not (folder/'manifest.json').exists() or not (folder/'baseline.json').exists():
                raise Conflict('Incomplete deployment snapshot; operator recovery required')
            return folder
        folder.mkdir(parents=True)
        manifest = {}
        for name, path in self.paths.items():
            manifest[name] = path.exists()
            if path.exists():
                atomic_write(folder/name, path.read_bytes())
        atomic_write(folder/'baseline.json', json.dumps(self.baseline()).encode())
        atomic_write(folder/'manifest.json', json.dumps(manifest).encode())
        return folder

    def restore(self, operation_id):
        folder = self.state/'snapshots'/str(uuid.UUID(operation_id))
        manifest = json.loads((folder/'manifest.json').read_text())
        baseline = json.loads((folder/'baseline.json').read_text())
        for name, existed in manifest.items():
            if name in {'compose','deployment_env','preflight'}:
                current = self.files()[name]
                if current != baseline['files'][name]:
                    raise Conflict('Unmanaged deployment files changed during apply; reconcile manually')
                continue
            if existed:
                atomic_write(self.paths[name], (folder/name).read_bytes())
            else:
                self.paths[name].unlink(missing_ok=True)
        self.rollout()

    def reconcile(self, code, revision, accept_hash=None):
        with self.lock(), gateway_registry.operation_lock(self.ledger_dsn):
            p = self.store.profile(code)
            if p['revision'] != revision:
                raise Conflict('Profile revision changed')
            baseline = self.baseline()
            with psycopg2.connect(self.ledger_dsn) as cn:
                observed = {'files':self.files(),'registry':self.db_state(cn),'ownership':baseline.get('ownership',[])}
                with cn.cursor() as cur:
                    cur.execute('SELECT g.code,g.name,g.is_running,r.user_mode,r.reporting_start_date '
                                'FROM dim_agent g JOIN gateway_agent_registry r ON r.agent_id=g.agent_id ORDER BY g.code')
                    registry = [list(row) for row in cur.fetchall()]
            review = {'previous':baseline,'observed':observed,'registry':registry,'draft':p['draft'],
                      'warning':'Acknowledging drift accepts the observed baseline. Next preview still proposes desired UI settings; review it before apply.'}
            fingerprint = digest(review)
            if accept_hash is not None:
                if accept_hash != fingerprint:
                    raise Conflict('Reconciliation review expired')
                with self.store.transaction() as cur:
                    cur.execute('UPDATE gateway_connection_deployment SET baseline=%s',(Json(observed),))
                    self.store.audit(cur,code,'connection-admin','reconcile',{'review_hash':fingerprint})
            return {'review_hash':fingerprint,'review':review,'accepted':accept_hash is not None}

    def recover(self, operation_id):
        with self.lock(), gateway_registry.operation_lock(self.ledger_dsn):
            op = self.store.operation(operation_id)
            if op['kind'] != 'recover':
                raise ValueError('Expected recovery operation')
            with self.store.transaction() as cur:
                cur.execute('SELECT recovery_operation FROM gateway_connection_deployment')
                target = cur.fetchone()['recovery_operation']
            if target is None:
                raise Conflict('No unresolved recovery')
            target_op = self.store.operation(str(target))
            if op['code'] != target_op['code']:
                raise ValueError('Recovery must target the affected profile')
            try:
                if target_op['kind']=='apply':
                    self.restore(str(target))
                    old = json.loads((self.state/'snapshots'/str(target)/'baseline.json').read_text())
                    with psycopg2.connect(self.ledger_dsn) as cn:
                        old['registry'] = self.db_state(cn)
                    old['files'] = self.files()
                    with self.store.transaction() as cur:
                        cur.execute('UPDATE gateway_connection_deployment SET baseline=%s',(Json(old),))
                elif target_op['kind']=='issue':
                    alias = 'connection-' + str(target)
                    if self.gateways[0].key(alias):
                        self.gateways[0].revoke(alias)
                    with self.store.transaction() as cur:
                        cur.execute("UPDATE gateway_connection_key SET status='revoked' WHERE operation_id=%s",(str(target),))
                elif target_op['kind']=='revoke':
                    for alias in target_op['payload']['key_aliases']:
                        if self.gateways[0].key(alias):
                            self.gateways[0].revoke(alias)
                        with self.store.transaction() as cur:
                            cur.execute("UPDATE gateway_connection_key SET status='revoked' WHERE key_alias=%s",(alias,))
                elif target_op['kind']=='budget':
                    alias = target_op['payload']['key_alias']
                    key = self.gateways[0].key(alias)
                    metadata = (key or {}).get('metadata') or {}
                    if not key or metadata.get('tags') != [op['code']]:
                        raise Conflict('Repair managed key ownership before recovering budget')
                    marker = any(isinstance(item,dict) and item.get('operation_id')==str(target)
                                 for item in metadata.get('quota_log',[]))
                    budget = target_op['payload']['budget']
                    if marker and ((budget['mode']=='unlimited' and 'quota_usd' in metadata) or
                                   (budget['mode']=='finite' and metadata.get('quota_usd')!=budget['usd'])):
                        raise Conflict('Quota changed after the interrupted operation; reconcile manually')
                    if not marker:
                        metadata = quota_metadata(metadata,target_op['payload']['budget'],target_op['actor'],datetime.now(timezone.utc).isoformat())
                        metadata['quota_log'][-1]['operation_id']=str(target)
                        self.gateways[0].call('/key/update',{'key_alias':alias,'metadata':metadata})
                    confirmed = self.gateways[0].key(alias)
                    if not confirmed or confirmed.get('metadata')!=metadata:
                        raise Conflict('Budget recovery not confirmed')
                    with self.store.transaction() as cur:
                        cur.execute('UPDATE gateway_connection_key SET budget=%s WHERE key_alias=%s',(Json(target_op['payload']['budget']),alias))
                else:
                    raise Conflict('Resolve this operation manually before clearing recovery')
                with self.store.transaction() as cur:
                    cur.execute('UPDATE gateway_connection_deployment SET recovery_operation=NULL')
                self.store.stage(str(target),'updated' if target_op['kind']=='budget' else 'failed','recovered')
                self.store.stage(operation_id,'recovered','recovered',{'target_operation':str(target)})
            except Exception:
                self.store.stage(operation_id,'failed','recovery-failed')
                raise RuntimeError('Recovery failed; deployment remains locked') from None
            return self.store.operation(operation_id)

    def apply(self, operation_id):
        op = self.store.operation(operation_id)
        if op['kind'] != 'apply':
            raise ValueError('Expected apply operation')
        if op['status'] == 'applied':
            return op
        with self.lock():
            op = self.store.operation(operation_id)
            if op['status']=='applied':
                return op
            if op['status'] == 'running':
                # A crashed rollout is compensated, never blindly replayed.
                try:
                    with gateway_registry.operation_lock(self.ledger_dsn):
                        self.restore(operation_id)
                        old = json.loads((self.state/'snapshots'/operation_id/'baseline.json').read_text())
                        with psycopg2.connect(self.ledger_dsn) as cn:
                            old['registry'] = self.db_state(cn)
                        old['files'] = self.files()
                        with self.store.transaction() as cur:
                            cur.execute('UPDATE gateway_connection_deployment SET baseline=%s',(Json(old),))
                            self.store.stage(operation_id, 'failed', 'recovered-after-restart', cursor=cur)
                except Exception:
                    self.store.stage(operation_id, 'recovery-required', 'restart-restore-failed')
                return self.store.operation(operation_id)
            with gateway_registry.operation_lock(self.ledger_dsn):
                cn = psycopg2.connect(self.ledger_dsn)
                try:
                    candidate = self.preview(op['code'], op['expected_revision'], cn)
                    if candidate['preview_hash'] != op['payload'].get('preview_hash'):
                        raise Conflict('Preview expired; review a fresh preview')
                    self.snapshot(operation_id)
                    self.store.stage(operation_id, 'running', 'render')
                    atomic_write(self.paths['routes'], yaml.safe_dump(candidate['routes'], allow_unicode=True, sort_keys=False).encode())
                    with self.store.transaction() as cur:
                        cur.execute('SELECT applied FROM gateway_connection_profile WHERE applied IS NOT NULL AND code<>%s', (op['code'],))
                        applied = [r['applied'] for r in cur.fetchall()] + [candidate['profile']]
                    # Preserve legacy tags from the deployment environment, remove only managed codes.
                    legacy_chat = os.environ.get('QUOTA_CHAT_TAGS', 'contact-center,sale-agent,tla-hd,ralli').split(',')
                    managed = {p['code'] for p in applied}
                    chat = sorted((set(legacy_chat)-managed) | {p['code'] for p in applied if p['quota_response_mode']=='chat'})
                    services = {service: {'env_file': [str(self.paths['environment'])], 'environment': {
                        'MANAGED_SECRET_REFS': ','.join(sorted(self.secrets())), 'QUOTA_CHAT_TAGS': ','.join(chat)}}
                        for service in ('litellm-1','litellm-2')}
                    for index,service in enumerate(('litellm-1','litellm-2')):
                        endpoint = urllib.parse.urlsplit(self.gateways[index].url)
                        if endpoint.hostname in {'127.0.0.1','localhost'} and endpoint.scheme=='http' and endpoint.port:
                            services[service]['ports'] = [f'127.0.0.1:{endpoint.port}:4000']
                    atomic_write(self.paths['override'], yaml.safe_dump({'services': services}).encode())
                    self.store.stage(operation_id, 'running', 'rollout')
                    self.rollout()
                    self.store.stage(operation_id, 'running', 'registry')
                    gateway_registry.apply_config(cn, gateway_registry.parse_config(yaml.safe_dump(candidate['registry'])))
                    cn.commit()
                    atomic_write(self.paths['registry'], yaml.safe_dump(candidate['registry'],allow_unicode=True,sort_keys=False).encode())
                    baseline = {'files': self.files(), 'registry': self.db_state(cn), 'ownership': candidate['ownership']}
                    with self.store.transaction() as cur:
                        cur.execute('UPDATE gateway_connection_profile SET applied=draft,applied_revision=revision WHERE code=%s AND revision=%s',
                                    (op['code'],op['expected_revision']))
                        if cur.rowcount != 1:
                            raise Conflict('Draft changed during rollout')
                        cur.execute('UPDATE gateway_connection_deployment SET baseline=%s', (Json(baseline),))
                        # Profile, baseline and terminal checkpoint commit together: a restart
                        # must never restore old files after the new applied profile committed.
                        self.store.stage(operation_id, 'applied', 'applied', {'reporting': 'awaiting-refresh', 'access': 'key-not-issued'}, cursor=cur)
                except Exception as exc:
                    cn.rollback()
                    if op['status'] == 'queued' and not (self.state/'snapshots'/operation_id/'manifest.json').exists():
                        self.store.stage(operation_id, 'failed', 'validation', {'reason': str(exc) if isinstance(exc,(ValueError,Conflict)) else 'Validation failed'})
                    else:
                        try:
                            self.restore(operation_id)
                            old_baseline = json.loads((self.state/'snapshots'/operation_id/'baseline.json').read_text())
                            old_baseline['files'] = self.files()
                            old_baseline['registry'] = self.db_state(cn)
                            with self.store.transaction() as cur:
                                cur.execute('UPDATE gateway_connection_deployment SET baseline=%s',(Json(old_baseline),))
                            self.store.stage(operation_id, 'failed', 'restored', {'reason': 'Apply failed; configuration restored; registry history retained'})
                        except Exception:
                            self.store.stage(operation_id, 'recovery-required', 'restore-failed')
                    return self.store.operation(operation_id)
                finally:
                    cn.close()
            # Lock ownership does not transfer to the subprocess. Run only after releasing registry lock.
            try:
                result = subprocess.run([sys.executable,'scripts/refresh_gateway.py','--db',self.ledger_dsn],
                    cwd=self.root, capture_output=True, timeout=180,
                    env={**os.environ,'TOKEN_LEDGER_DSN':self.ledger_dsn,'GATEWAY_DSN':self.gateway_dsn})
                self.store.stage(operation_id,'applied','applied',{'reporting': 'refresh-complete' if result.returncode==0 else 'refresh-pending',
                    'access':'key-not-issued'})
            except (OSError, subprocess.TimeoutExpired):
                self.store.stage(operation_id,'applied','applied',{'reporting':'refresh-pending','access':'key-not-issued'})
        return self.store.operation(operation_id)

    def issue(self, operation_id):
        with self.lock():
            op = self.store.operation(operation_id)
            if op['kind'] != 'issue':
                raise ValueError('Expected issuance operation')
            alias = 'connection-' + operation_id
            gateway = self.gateways[0]
            if op['status'] != 'queued':
                if op['status'] in {'running','recovery-required'}:
                    if gateway.key(alias):
                        gateway.revoke(alias)
                    with self.store.transaction() as cur:
                        cur.execute("UPDATE gateway_connection_key SET status='revoked' WHERE operation_id=%s",(operation_id,))
                    self.store.stage(operation_id,'failed','unreceived-key-revoked')
                raise Conflict('Plaintext issuance response cannot be replayed; revoke and create replacement')
            profile = self.store.profile(op['code'])
            if profile['applied_revision'] != op['expected_revision']:
                raise Conflict('Applied revision changed')
            p = profile['applied']
            budget = validate_budget(op['payload']['budget'])
            metadata = {'tags':[p['code']]}
            if budget['mode']=='finite':
                metadata['quota_usd'] = budget['usd']
            self.store.stage(operation_id,'running','issuing')
            try:
                if gateway.key(alias):
                    raise Conflict('Operation alias already exists')
                _, response = gateway.call('/key/generate',{'key_alias':alias,
                    'models':[m['alias'] for m in p['models']], 'metadata':metadata})
                key = response['key']
                current = gateway.key(alias)
                if not current or (current.get('metadata') or {}).get('tags') != [p['code']]:
                    raise RuntimeError('Issued key metadata mismatch')
                with self.store.transaction() as cur:
                    cur.execute('INSERT INTO gateway_connection_key(key_alias,code,operation_id,status,budget) VALUES(%s,%s,%s,%s,%s)',
                                (alias,p['code'],operation_id,'active',Json(budget)))
                self.store.stage(operation_id,'issued','issued',{'key_alias':alias})
                return {'key':key,'key_alias':alias,'warning':'Copy now; plaintext is never stored or returned again.'}
            except Exception:
                try:
                    gateway.revoke(alias)
                    self.store.stage(operation_id,'failed','issuance-compensated')
                except Exception:
                    self.store.stage(operation_id,'recovery-required','issuance-revocation-unconfirmed')
                raise RuntimeError('Issuance failed; inspect operation status') from None

    def revoke(self, operation_id):
        with self.lock():
            op = self.store.operation(operation_id)
            if op['kind'] != 'revoke':
                raise ValueError('Expected revocation operation')
            if op['status']=='revoked':
                return op
            aliases = op['payload']['key_aliases']
            with self.store.transaction() as cur:
                cur.execute('SELECT key_alias FROM gateway_connection_key WHERE code=%s AND key_alias=ANY(%s)',(op['code'],aliases))
                if set(aliases) != {r['key_alias'] for r in cur.fetchall()}:
                    raise ValueError('Only managed keys belonging to this profile can be revoked')
            self.store.stage(operation_id,'running','revoking')
            try:
                for alias in aliases:
                    if self.gateways[0].key(alias):
                        self.gateways[0].revoke(alias)
                    with self.store.transaction() as cur:
                        cur.execute("UPDATE gateway_connection_key SET status='revoked' WHERE key_alias=%s",(alias,))
                self.store.stage(operation_id,'revoked','revoked',{'key_aliases':aliases})
            except Exception:
                self.store.stage(operation_id,'recovery-required','revocation-unconfirmed')
                raise RuntimeError('Revocation unconfirmed; inspect operation status') from None
            return self.store.operation(operation_id)

    def budget(self, operation_id):
        with self.lock():
            op = self.store.operation(operation_id)
            if op['kind'] != 'budget':
                raise ValueError('Expected budget operation')
            if op['status']=='updated':
                return op
            alias = op['payload']['key_alias']
            with self.store.transaction() as cur:
                cur.execute("SELECT key_alias FROM gateway_connection_key WHERE code=%s AND key_alias=%s AND status='active'",(op['code'],alias))
                if not cur.fetchone():
                    raise ValueError('Choose an active managed key belonging to this profile')
            gateway = self.gateways[0]
            key = gateway.key(alias)
            if not key:
                raise Conflict('Key no longer exists')
            current = key.get('metadata') or {}
            if current.get('tags') != [op['code']]:
                raise Conflict('Managed key routing tags changed; repair before changing quota')
            completed = any(isinstance(item,dict) and item.get('operation_id')==operation_id
                            for item in current.get('quota_log',[]))
            if completed:
                budget = op['payload']['budget']
                if ((budget['mode']=='unlimited' and 'quota_usd' in current) or
                    (budget['mode']=='finite' and current.get('quota_usd')!=budget['usd'])):
                    raise Conflict('Quota changed after this operation; review the current budget')
                with self.store.transaction() as cur:
                    cur.execute('UPDATE gateway_connection_key SET budget=%s WHERE key_alias=%s',(Json(op['payload']['budget']),alias))
                self.store.stage(operation_id,'updated','updated',{'key_alias':alias,'budget':op['payload']['budget']})
                return self.store.operation(operation_id)
            metadata = quota_metadata(current,op['payload']['budget'],op['actor'],datetime.now(timezone.utc).isoformat())
            metadata['quota_log'][-1]['operation_id']=operation_id
            self.store.stage(operation_id,'running','updating-budget')
            latest = gateway.key(alias)
            if not latest or digest(latest.get('metadata') or {})!=digest(current):
                self.store.stage(operation_id,'failed','metadata-conflict')
                raise Conflict('Key metadata changed; retry after review')
            try:
                gateway.call('/key/update',{'key_alias':alias,'metadata':metadata})
                confirmed = gateway.key(alias)
            except RuntimeError:
                self.store.stage(operation_id,'recovery-required','budget-update-unconfirmed')
                raise RuntimeError('Budget update unconfirmed; inspect operation before retrying') from None
            if not confirmed or confirmed.get('metadata')!=metadata:
                self.store.stage(operation_id,'failed','metadata-readback-conflict')
                raise Conflict('Gateway metadata update could not be confirmed')
            with self.store.transaction() as cur:
                cur.execute('UPDATE gateway_connection_key SET budget=%s WHERE key_alias=%s',(Json(op['payload']['budget']),alias))
            self.store.stage(operation_id,'updated','updated',{'key_alias':alias,'budget':op['payload']['budget']})
            return self.store.operation(operation_id)

    def verify(self, operation_id, virtual_key):
        with self.lock():
            return self._verify(operation_id,virtual_key)

    def _verify(self, operation_id, virtual_key):
        op = self.store.operation(operation_id)
        if op['kind'] != 'verify':
            raise ValueError('Expected verification operation')
        if op['status'] != 'queued':
            return op  # Never duplicate a billable test after HTTP retry.
        if not virtual_key or secrets.compare_digest(virtual_key.encode(), self.gateways[0].master.encode()):
            raise ValueError('Provide the actual agent Virtual Key, not the master key')
        p = self.store.profile(op['code'])['applied']
        if not p:
            raise Conflict('Apply before verification')
        self.store.stage(operation_id,'running','request')
        try:
            headers, response = self.gateways[0].call('/v1/chat/completions',{
                'model':p['models'][0]['alias'], 'messages':[{'role':'user','content':'Reply OK.'}],
                'max_tokens':8,'user':'svc.'+p['code'] if p['user_mode']=='single' else 'connection-check',
                'metadata':{'connection_check_id':operation_id}}, key=virtual_key)
            correlation = headers.get('x-litellm-call-id')
            rid = headers.get('x-litellm-model-id')
            hook_spec = importlib.util.spec_from_file_location('connection_quota_hook',
                Path(__file__).resolve().parents[1]/'docker/gateway/quota_hook.py')
            hook = importlib.util.module_from_spec(hook_spec)
            hook_spec.loader.exec_module(hook)
            content = (response.get('choices') or [{}])[0].get('message',{}).get('content')
            if not correlation and not rid and content == hook._message():
                self.store.stage(operation_id,'failed','quota-blocked',{'gateway':'failed',
                    'reason':'Quota stop message returned with HTTP 200; no provider call verified',
                    'external_agent':'awaiting-agent-request'})
                return self.store.operation(operation_id)
            result = {'gateway':'pending','external_agent':'awaiting-agent-request','call_id':correlation,
                      'route_id':rid,'reporting':'pending','started_at':op['created_at'].isoformat()}
            expected = route_id(p['code'],p['models'][0]['alias'])
            if rid is not None and rid != expected:
                result.update(gateway='failed',reason='Unexpected provider route')
            elif not correlation or not rid:
                result.update(gateway='inconclusive',reason='Missing Gateway correlation or provider-route evidence')
            else:
                result = self.evidence(p,correlation,result)
            self.store.stage(operation_id,'pending' if result['gateway']=='pending' else result['gateway'],'evidence',
                             {**result,'deadline':time.time()+60,'expected_profile':p,'refresh_attempted':False})
        except RuntimeError as exc:
            self.store.stage(operation_id,'failed','request',{'gateway':'failed','reason':str(exc),
                            'external_agent':'awaiting-agent-request'})
        return self.store.operation(operation_id)

    def evidence(self, p, correlation, result):
        # The pinned image maps header call ID to metadata, not request_id.
        with psycopg2.connect(self.gateway_dsn) as cn:
            cn.set_session(readonly=True)
            with cn.cursor() as cur:
                cur.execute('SELECT request_id,request_tags,status,total_tokens,metadata '
                            'FROM "LiteLLM_SpendLogs" WHERE "startTime">=%s '
                            'AND metadata->>\'litellm_call_id\'=%s', (result['started_at'],correlation))
                rows = cur.fetchall()
        if len(rows)!=1:
            return {**result,'gateway':'pending','reason':'Correlated log not uniquely available; waiting for evidence'}
        request_id,tags,status,tokens,metadata = rows[0]
        if p['code'] not in (tags or []) or status!='success':
            return {**result,'gateway':'failed','reason':'Wrong agent tag or quota/provider failure'}
        cost = (metadata.get('cost_breakdown') or {}).get('total_cost')
        if cost is None:
            return {**result,'gateway':'inconclusive','reason':'Missing recorded cost evidence'}
        with psycopg2.connect(self.ledger_dsn) as cn:
            cn.set_session(readonly=True)
            with cn.cursor() as cur:
                cur.execute('SELECT f.total_tokens,f.cost_usd,g.code FROM fact_call f JOIN dim_agent g ON g.agent_id=f.agent_id '
                            "WHERE f.call_id=%s AND f.source='gateway'", (request_id,))
                row = cur.fetchone()
        if row is None:
            return {**result,'request_id':request_id,'gateway':'pending','reporting':'pending',
                    'reason':'Gateway log found; matching ledger usage awaits refresh'}
        # Migration 004 uses unconstrained NUMERIC for calls; daily rollups use a different scale.
        expected_cost = Decimal(str(cost))
        if row[2]!=p['code'] or row[0]!=tokens or row[1] is None or row[1]!=expected_cost:
            return {**result,'gateway':'failed','reporting':'mismatch','reason':'Ledger evidence mismatch'}
        return {**result,'gateway':'verified','reporting':'verified','request_id':request_id,
                'verified_at':datetime.now(timezone.utc).isoformat()}

    def template(self, code, context):
        p = self.store.profile(code)['draft']
        endpoint = self.docker_endpoint if context=='docker' else self.host_endpoint
        return {'text':integration_template(p,endpoint,self.network,context)}

    def external_verify(self, operation_id):
        with self.lock():
            op = self.store.operation(operation_id)
            if op['kind']!='verify' or not op['payload'].get('external_request_id'):
                raise ValueError('Expected external verification operation')
            if op['status']!='queued':
                return op
            p = self.store.profile(op['code'])['applied']
            request_id = op['payload']['external_request_id']
            with psycopg2.connect(self.gateway_dsn) as cn:
                cn.set_session(readonly=True)
                with cn.cursor() as cur:
                    cur.execute('SELECT request_tags,status,end_user,metadata FROM "LiteLLM_SpendLogs" WHERE request_id=%s',(request_id,))
                    row = cur.fetchone()
            if not row:
                result = {'external_agent':'inconclusive','reason':'Request ID is not available in retained Gateway logs'}
            elif p['code'] not in (row[0] or []):
                result = {'external_agent':'failed','reason':'Request belongs to a different agent'}
            else:
                correlation = row[3].get('litellm_call_id')
                with self.store.transaction() as cur:
                    cur.execute("SELECT id FROM gateway_connection_operation WHERE kind='verify' AND result->>'call_id'=%s",(correlation,))
                    is_worker = bool(cur.fetchone())
                if is_worker:
                    result = {'external_agent':'failed','reason':'This request originated from the worker test'}
                elif row[1]!='success' or (p['user_mode']=='single' and row[2]!='svc.'+p['code']) or not gateway_registry.valid_identity(row[2]):
                    result = {'external_agent':'failed','reason':'Request failed or has unexpected user identity'}
                else:
                    # The pinned image does not preserve a trustworthy route ID in SpendLogs.
                    # A submitted response header alone cannot prove external origin or provider routing.
                    result = {'external_agent':'inconclusive','request_id':request_id,
                              'reason':'Agent tag and identity observed, but retained log lacks trusted external-origin/provider-route evidence'}
            self.store.stage(operation_id,result['external_agent'],'external-evidence',result)
            return self.store.operation(operation_id)

    def drain(self):
        # Recover an interrupted issuance only when no RPC owns the deployment lock.
        with self.store.transaction() as cur:
            cur.execute("SELECT id FROM gateway_connection_operation WHERE kind='issue' AND status='running' ORDER BY created_at LIMIT 1")
            interrupted = cur.fetchone()
        if interrupted:
            try:
                self.issue(str(interrupted['id']))
            except Conflict:
                pass  # Expected: plaintext is never replayed after recovery.
        with self.store.transaction() as cur:
            cur.execute("SELECT id FROM gateway_connection_operation WHERE kind='verify' AND status='running' ORDER BY created_at LIMIT 1")
            interrupted_test = cur.fetchone()
        if interrupted_test:
            with self.lock():
                # Lock availability proves there is no live request handler to complete this test.
                if self.store.operation(str(interrupted_test['id']))['status']=='running':
                    self.store.stage(str(interrupted_test['id']),'inconclusive','interrupted',{
                        'gateway':'inconclusive','reason':'Test interrupted; no billable request is retried',
                        'external_agent':'awaiting-agent-request'})
        with self.store.transaction() as cur:
            cur.execute("SELECT id FROM gateway_connection_operation WHERE kind='apply' AND status IN ('queued','running') ORDER BY created_at LIMIT 1")
            op = cur.fetchone()
        if op:
            self.apply(str(op['id']))
        with self.store.transaction() as cur:
            cur.execute("SELECT * FROM gateway_connection_operation WHERE kind='verify' AND status='pending' ORDER BY created_at LIMIT 1")
            verification = cur.fetchone()
        if verification:
            result = verification['result']
            p = result['expected_profile']
            if not result.get('refresh_attempted'):
                try:
                    subprocess.run([sys.executable,'scripts/refresh_gateway.py','--db',self.ledger_dsn],
                        cwd=self.root,capture_output=True,timeout=45,
                        env={**os.environ,'TOKEN_LEDGER_DSN':self.ledger_dsn,'GATEWAY_DSN':self.gateway_dsn})
                except (OSError,subprocess.TimeoutExpired):
                    pass  # Evidence remains pending; never claim refresh succeeded.
                result['refresh_attempted']=True
            refreshed = self.evidence(p,result['call_id'],result)
            if refreshed['gateway']=='pending' and time.time()>=result['deadline']:
                refreshed['gateway']='inconclusive'
            self.store.stage(str(verification['id']),refreshed['gateway'],'evidence',refreshed)


def build_app(worker, credential):
    if not credential:
        raise ValueError('Worker RPC credential required')
    app = FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    bearer = HTTPBearer(auto_error=False)

    def auth(cred: HTTPAuthorizationCredentials | None=Depends(bearer)):
        if cred is None or not secrets.compare_digest(cred.credentials.encode(),credential.encode()):
            raise HTTPException(401,'Worker authentication required')

    @app.post('/rpc/{action}')
    def rpc(action: str, body: dict, authorized=Depends(auth)):
        try:
            if action=='preview' and set(body)=={'code','revision'}:
                return worker.preview(body['code'],body['revision'])
            if action=='template' and set(body)=={'code','context'} and body['context'] in ('host','docker'):
                return worker.template(body['code'],body['context'])
            if action in ('issue','revoke','budget','recover','external-verify') and set(body)=={'operation_id'}:
                if action=='external-verify':
                    return worker.external_verify(str(uuid.UUID(body['operation_id'])))
                return getattr(worker,action)(str(uuid.UUID(body['operation_id'])))
            if action=='reconcile' and set(body)=={'code','revision','accept_hash'}:
                return worker.reconcile(body['code'],body['revision'],body['accept_hash'])
            if action=='verify' and set(body)=={'operation_id','virtual_key'}:
                return worker.verify(str(uuid.UUID(body['operation_id'])),body['virtual_key'])
            if action=='secret' and set(body)=={'value'}:
                return worker.import_secret(body['value'])
            raise ValueError('Unsupported action or fields')
        except Conflict as exc:
            raise HTTPException(409,str(exc)) from None
        except ValueError as exc:
            raise HTTPException(422,str(exc)) from None
        except KeyError:
            raise HTTPException(404,'Profile or operation not found') from None
        except Exception:
            raise HTTPException(503,'Worker operation failed; inspect sanitized operation status') from None
    return app
