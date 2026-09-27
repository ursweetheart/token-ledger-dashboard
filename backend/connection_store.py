"""Explicit administration DSN; no fallback to the read-only/default ledger role."""
from contextlib import contextmanager
from datetime import date
import json
import uuid
import psycopg2
from psycopg2.extras import Json, RealDictCursor
from .connection_config import Conflict, digest, validate_profile


class ConnectionStore:
    def __init__(self, dsn):
        if not dsn:
            raise ValueError('CONNECTION_ADMIN_DSN is required')
        self.dsn = dsn

    @contextmanager
    def transaction(self):
        cn = psycopg2.connect(self.dsn, connect_timeout=5)
        try:
            with cn:
                with cn.cursor(cursor_factory=RealDictCursor) as cur:
                    yield cur
        finally:
            cn.close()

    def list_profiles(self):
        with self.transaction() as cur:
            cur.execute('SELECT * FROM gateway_connection_profile ORDER BY code')
            profiles = [dict(row) for row in cur.fetchall()]
            cur.execute('SELECT g.code,g.name FROM dim_agent g LEFT JOIN gateway_agent_registry r '
                        'ON r.agent_id=g.agent_id WHERE r.agent_id IS NULL ORDER BY g.code')
            return {'profiles': profiles, 'legacy': [dict(r) for r in cur.fetchall()]}

    def profile(self, code):
        with self.transaction() as cur:
            cur.execute('SELECT * FROM gateway_connection_profile WHERE code=%s', (code,))
            row = cur.fetchone()
            if not row:
                raise KeyError(code)
            return dict(row)

    @staticmethod
    def audit(cur, code, actor, action, detail, operation=None):
        cur.execute('INSERT INTO gateway_connection_audit(code,actor,action,detail,operation_id) '
                    'VALUES(%s,%s,%s,%s,%s)', (code, actor, action, Json(detail), operation))

    def save(self, value, expected_revision, actor):
        p = validate_profile(value)
        if type(expected_revision) is not int or expected_revision < 0:
            raise ValueError('expected_revision must be a nonnegative integer')
        with self.transaction() as cur:
            cur.execute('SELECT pg_advisory_xact_lock(74120925)')
            cur.execute('SELECT * FROM gateway_connection_profile WHERE code=%s FOR UPDATE', (p['code'],))
            old = cur.fetchone()
            if expected_revision != (old['revision'] if old else 0):
                raise Conflict('Profile revision changed')
            cur.execute('SELECT g.name,g.is_running,r.user_mode,r.reporting_start_date '
                        'FROM dim_agent g LEFT JOIN gateway_agent_registry r ON r.agent_id=g.agent_id '
                        'WHERE g.code=%s', (p['code'],))
            registry = cur.fetchone()
            if registry:
                if registry['user_mode'] is None:
                    raise ValueError('Legacy agent is read-only')
                if (registry['user_mode'] != p['user_mode'] or
                        registry['reporting_start_date'].isoformat() != p['reporting_start_date']):
                    raise ValueError('Registered user_mode/reporting_start_date are immutable')
            revision = expected_revision + 1
            cur.execute('INSERT INTO gateway_connection_profile(code,revision,draft) VALUES(%s,%s,%s) '
                        'ON CONFLICT(code) DO UPDATE SET revision=EXCLUDED.revision,draft=EXCLUDED.draft,updated_at=now()',
                        (p['code'], revision, Json(p)))
            self.audit(cur, p['code'], actor, 'save', {'revision': revision, 'profile': p})
        return self.profile(p['code'])

    def operation(self, operation_id):
        with self.transaction() as cur:
            cur.execute('SELECT * FROM gateway_connection_operation WHERE id=%s', (str(uuid.UUID(operation_id)),))
            row = cur.fetchone()
            if not row:
                raise KeyError(operation_id)
            return dict(row)

    def enqueue(self, code, kind, revision, key, actor, payload):
        if kind not in {'apply', 'issue', 'revoke', 'verify', 'recover','budget'}:
            raise ValueError('Unknown operation')
        if not isinstance(key, str) or not 8 <= len(key) <= 128:
            raise ValueError('An idempotency key of 8 to 128 characters is required')
        fingerprint = digest({'code': code, 'kind': kind, 'revision': revision, 'payload': payload})
        with self.transaction() as cur:
            cur.execute('SELECT singleton,recovery_operation FROM gateway_connection_deployment FOR UPDATE')
            deployment = cur.fetchone()
            if deployment['recovery_operation'] and kind != 'recover':
                raise Conflict('Deployment recovery is required')
            cur.execute('SELECT * FROM gateway_connection_operation WHERE idempotency_key=%s', (key,))
            old = cur.fetchone()
            if old:
                if old['request_hash'] != fingerprint:
                    raise Conflict('Idempotency key already belongs to another request')
                return dict(old)
            cur.execute('SELECT revision,applied_revision FROM gateway_connection_profile WHERE code=%s FOR UPDATE', (code,))
            p = cur.fetchone()
            if not p:
                raise KeyError(code)
            if type(revision) is not int or p['revision'] != revision:
                raise Conflict('Profile revision changed')
            if kind in {'issue','verify'} and p['applied_revision'] != revision:
                raise Conflict('Apply this revision before issuing or testing keys')
            if kind == 'issue':
                cur.execute("SELECT id FROM gateway_connection_operation WHERE kind='issue' AND status='running'")
                if cur.fetchone():
                    raise Conflict('Reconcile the interrupted issuance before creating a replacement')
            operation_id = str(uuid.uuid4())
            cur.execute('INSERT INTO gateway_connection_operation(id,code,kind,idempotency_key,request_hash,'
                        'expected_revision,actor,payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)',
                        (operation_id, code, kind, key, fingerprint, revision, actor, Json(payload)))
            self.audit(cur, code, actor, kind, {'revision': revision}, operation_id)
        return self.operation(operation_id)

    def stage(self, operation_id, status, stage, result=None, cursor=None):
        if cursor is not None:
            cursor.execute('UPDATE gateway_connection_operation SET status=%s,stage=%s,result=%s,updated_at=now() WHERE id=%s',
                           (status, stage, Json(result or {}), operation_id))
            if status == 'recovery-required':
                cursor.execute('UPDATE gateway_connection_deployment SET recovery_operation=%s', (operation_id,))
            op = self.operation(operation_id)
            self.audit(cursor, op['code'], op['actor'], status, {'stage': stage, **(result or {})}, operation_id)
            return
        with self.transaction() as cur:
            self.stage(operation_id, status, stage, result, cursor=cur)

    def detail(self, code):
        profile = self.profile(code)
        with self.transaction() as cur:
            cur.execute('SELECT * FROM gateway_connection_key WHERE code=%s ORDER BY created_at DESC', (code,))
            profile['keys'] = [dict(r) for r in cur.fetchall()]
            cur.execute('SELECT * FROM gateway_connection_operation WHERE code=%s ORDER BY created_at DESC LIMIT 30', (code,))
            profile['operations'] = [dict(r) for r in cur.fetchall()]
            cur.execute('SELECT * FROM gateway_connection_audit WHERE code=%s ORDER BY id DESC LIMIT 100', (code,))
            profile['audit'] = [dict(r) for r in cur.fetchall()]
        return profile
