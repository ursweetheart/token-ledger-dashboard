"""Opt-in disposable PostgreSQL and worker fault tests, no production credentials."""
import copy
import json
import os
from pathlib import Path
from unittest.mock import patch
import uuid
import subprocess
import sys
import time
import pytest
import psycopg2
from psycopg2.extras import Json
import yaml
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.connection_config import Conflict
from backend.connection_store import ConnectionStore
from backend.connection_worker import Worker
from backend.connection_api import router
from tests.connection_config_cases import profile

DSN = os.environ.get('CONNECTION_TEST_DSN','')


@pytest.fixture(scope='session',autouse=True)
def fixture_gateway_ready():
    if not DSN:
        return
    from backend.connection_worker import Gateway
    for port in (4401,4402):
        gateway=Gateway(f'http://127.0.0.1:{port}','sk-isolated-connections-test-master')
        for attempt in range(60):
            try:
                gateway.call('/health/liveliness')
                break
            except RuntimeError:
                if attempt==59: raise
                time.sleep(1)


@pytest.fixture
def store():
    if not DSN:
        pytest.skip('Set CONNECTION_TEST_DSN for disposable connection_ledger_test only')
    from urllib.parse import urlsplit
    parsed=urlsplit(DSN)
    assert parsed.hostname=='127.0.0.1' and parsed.port==55439 and parsed.path=='/connection_ledger_test'
    with psycopg2.connect(DSN) as cn:
        with cn.cursor() as cur:
            cur.execute('TRUNCATE gateway_connection_key,gateway_connection_audit,gateway_connection_deployment,gateway_connection_operation,gateway_connection_profile')
            cur.execute('INSERT INTO gateway_connection_deployment(singleton) VALUES(true)')
    return ConnectionStore(DSN)


@pytest.fixture
def worker(store,tmp_path):
    root=tmp_path/'repo'; (root/'docker/gateway').mkdir(parents=True); (root/'config').mkdir()
    state=tmp_path/'restricted'; state.mkdir(mode=0o700)
    routes={'model_list':[{'model_name':'legacy','litellm_params':{'model':'gemini/test','tags':['legacy']}}],
            'router_settings':{'enable_tag_filtering':True}}
    (root/'docker/gateway/config.gateway.yaml').write_text(yaml.safe_dump(routes),encoding='utf-8')
    (root/'config/gateway-agents.yaml').write_text('version: 1\nagents: []\n',encoding='utf-8')
    w=Worker(root,state,DSN,'postgresql://connection_test:isolated-test-only@127.0.0.1:55439/connection_test',
             ['http://127.0.0.1:4401','http://127.0.0.1:4402'],'sk-isolated-connections-test-master',
             'http://127.0.0.1:4401','http://gateway-lb:4000','shared-test-network')
    w.bootstrap()
    reference=w.import_secret('AQ.dummy-google-provider-key')['secret_ref']
    p=profile('test-'+uuid.uuid4().hex[:10]); p['secret_ref']=reference
    saved=store.save(p,0,'admin')
    return w,saved


def test_revision_and_idempotency(store):
    p=profile('revision-'+uuid.uuid4().hex[:10]); store.save(p,0,'admin')
    with pytest.raises(Conflict): store.save(p,0,'admin')
    op=store.enqueue(p['code'],'apply',1,'idem-test-key','admin',{'preview_hash':'a'})
    again=store.enqueue(p['code'],'apply',1,'idem-test-key','admin',{'preview_hash':'a'})
    assert op['id']==again['id']
    with pytest.raises(Conflict): store.enqueue(p['code'],'apply',1,'idem-test-key','admin',{'preview_hash':'b'})


def test_auth_and_preview_purity(worker):
    w,p=worker
    settings={'CONNECTIONS_ENABLED':'1','CONNECTION_ADMIN_KEY':'admin-test',
              'CONNECTION_ADMIN_DSN':DSN,'CONNECTION_WORKER_URL':'http://127.0.0.1:8766',
              'CONNECTION_WORKER_KEY':'rpc-test','DASHBOARD_KEY':'reader-test'}
    app=FastAPI(); app.include_router(router(lambda name:settings.get(name,'')))
    client=TestClient(app)
    assert client.get('/api/gateway-connections').status_code==401
    assert client.get('/api/gateway-connections',headers={'Authorization':'Bearer reader-test'}).status_code==403
    assert client.get('/api/gateway-connections',headers={'Authorization':'Bearer admin-test'}).status_code==200
    files=w.files()
    with w.store.transaction() as cur:
        cur.execute('SELECT count(*) AS n FROM gateway_connection_audit'); audit=cur.fetchone()['n']
    candidate=w.preview(p['code'],1)
    assert 'dummy-google-provider-key' not in json.dumps(candidate)
    assert w.files()==files
    with w.store.transaction() as cur:
        cur.execute('SELECT count(*) AS n FROM gateway_connection_audit'); assert cur.fetchone()['n']==audit


def test_apply_and_drift(worker):
    w,p=worker
    preview=w.preview(p['code'],1)
    op=w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':preview['preview_hash']})
    with patch.object(w,'rollout'), patch('backend.connection_worker.subprocess.run') as run:
        run.return_value.returncode=0
        result=w.apply(str(op['id']))
    assert result['status']=='applied'
    assert w.store.profile(p['code'])['applied_revision']==1
    assert w.apply(str(op['id']))['status']=='applied'
    w.paths['routes'].write_text(w.paths['routes'].read_text()+'\n# external drift\n')
    with pytest.raises(Conflict): w.preview(p['code'],1)


def test_failed_second_instance_restores(worker):
    w,p=worker; before=w.files(); preview=w.preview(p['code'],1)
    op=w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':preview['preview_hash']})
    with patch.object(w,'rollout',side_effect=[RuntimeError('second instance'),None]):
        result=w.apply(str(op['id']))
    assert result['status']=='failed'
    assert w.files()==before
    assert w.store.profile(p['code'])['applied_revision'] is None


def test_failed_rollback_blocks_next_apply(worker):
    w,p=worker; preview=w.preview(p['code'],1)
    op=w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':preview['preview_hash']})
    with patch.object(w,'rollout',side_effect=RuntimeError('unhealthy')):
        assert w.apply(str(op['id']))['status']=='recovery-required'
    with pytest.raises(Conflict): w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{})


def test_reject_master_key_and_no_test_retry(worker):
    w,p=worker
    with w.store.transaction() as cur:
        cur.execute('UPDATE gateway_connection_profile SET applied=draft,applied_revision=revision WHERE code=%s',(p['code'],))
    op=w.store.enqueue(p['code'],'verify',1,uuid.uuid4().hex,'admin',{})
    with pytest.raises(ValueError): w.verify(str(op['id']),'sk-isolated-connections-test-master')
    w.store.stage(str(op['id']),'failed','request')
    with patch.object(w.gateways[0],'call') as call:
        w.verify(str(op['id']),'sk-test')
        call.assert_not_called()


def test_live_issue_unlimited_and_revocation(worker):
    w,p=worker
    with w.store.transaction() as cur:
        cur.execute('UPDATE gateway_connection_profile SET applied=draft,applied_revision=revision WHERE code=%s',(p['code'],))
    op=w.store.enqueue(p['code'],'issue',1,uuid.uuid4().hex,'admin',{'budget':{'mode':'finite','usd':50}})
    issued=w.issue(str(op['id']))
    alias=issued['key_alias']
    try:
        assert issued['key'].startswith('sk-')
        assert issued['key'] not in json.dumps(w.store.detail(p['code']),default=str)
        with pytest.raises(Conflict): w.issue(str(op['id']))
        with psycopg2.connect(w.gateway_dsn) as cn:
            with cn.cursor() as cur:
                cur.execute('UPDATE "LiteLLM_VerificationToken" SET spend=40 WHERE key_alias=%s',(alias,))
        replacement=w.store.enqueue(p['code'],'issue',1,uuid.uuid4().hex,'admin',{'budget':{'mode':'finite','usd':10}})
        second=w.issue(str(replacement['id']))
        try:
            old=w.gateways[0].key(alias); new=w.gateways[0].key(second['key_alias'])
            assert old['spend']==40 and old['metadata']['quota_usd']==50
            assert new['spend']==0 and new['metadata']['quota_usd']==10
        finally:
            w.gateways[0].revoke(second['key_alias'])
        budget=w.store.enqueue(p['code'],'budget',1,uuid.uuid4().hex,'admin',{'key_alias':alias,'budget':{'mode':'unlimited'}})
        assert w.budget(str(budget['id']))['status']=='updated'
        key=w.gateways[0].key(alias)
        assert 'quota_usd' not in key['metadata'] and key['metadata']['tags']==[p['code']]
        w.store.stage(str(budget['id']),'running','updating-budget')
        with patch.object(w.gateways[0],'call',wraps=w.gateways[0].call) as call:
            assert w.budget(str(budget['id']))['status']=='updated'
            assert not any(item.args[0]=='/key/update' for item in call.call_args_list)
    finally:
        revoke=w.store.enqueue(p['code'],'revoke',1,uuid.uuid4().hex,'admin',{'key_aliases':[alias]})
        assert w.revoke(str(revoke['id']))['status']=='revoked'


def test_recover_failed_rollout(worker):
    w,p=worker; preview=w.preview(p['code'],1)
    op=w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':preview['preview_hash']})
    with patch.object(w,'rollout',side_effect=RuntimeError('failed')):
        w.apply(str(op['id']))
    recovery=w.store.enqueue(p['code'],'recover',1,uuid.uuid4().hex,'admin',{})
    with patch.object(w,'rollout'):
        assert w.recover(str(recovery['id']))['status']=='recovered'
    w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':w.preview(p['code'],1)['preview_hash']})


def test_reconcile_file_drift(worker):
    w,p=worker
    with w.store.transaction() as cur:
        cur.execute('SELECT name FROM dim_agent WHERE code=%s',(p['code'],))
    # File drift is reviewed explicitly, not silently overwritten.
    w.paths['registry'].write_text('version: 1\nagents: []\n# CLI edit\n')
    with pytest.raises(Conflict): w.preview(p['code'],1)
    reviewed=w.reconcile(p['code'],1)
    assert not reviewed['accepted']
    assert w.reconcile(p['code'],1,reviewed['review_hash'])['accepted']
    assert w.preview(p['code'],1)['preview_hash']


def test_registry_db_drift_is_not_silently_adopted(worker):
    w,p=worker
    from db import gateway_registry
    with gateway_registry.operation_lock(DSN), psycopg2.connect(DSN) as cn:
        gateway_registry.apply_config(cn,gateway_registry.parse_config(yaml.safe_dump({
            'version':1,'agents':[{k:p['draft'][k] for k in
            ['code','name','user_mode','reporting_start_date','active']}]})))
    with pytest.raises(Conflict,match='database drift'): w.preview(p['code'],1)
    review=w.reconcile(p['code'],1)
    assert w.reconcile(p['code'],1,review['review_hash'])['accepted']
    assert w.preview(p['code'],1)['preview_hash']


def test_secret_import_cannot_hide_external_drift(worker):
    w,p=worker
    w.paths['environment'].write_text(w.paths['environment'].read_text()+'KEY_MANAGED_EXTERNAL="dummy-external-key"\n')
    before=w.files()
    with pytest.raises(Conflict,match='Secret file drift'): w.import_secret('another-dummy-key')
    assert w.files()==before


def test_restart_compensates_without_replaying_deployment(worker):
    w,p=worker
    preview=w.preview(p['code'],1)
    op=w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':preview['preview_hash']})
    w.snapshot(str(op['id']))
    before=w.files()
    w.store.stage(str(op['id']),'running','rollout')
    w.paths['routes'].write_text('model_list: []\n')
    with patch.object(w,'rollout') as rollout:
        assert w.apply(str(op['id']))['stage']=='recovered-after-restart'
        rollout.assert_called_once()
    assert w.files()==before and w.preview(p['code'],1)['preview_hash']


def test_interrupted_verification_is_not_billed_again(worker):
    w,p=worker
    with w.store.transaction() as cur:
        cur.execute('UPDATE gateway_connection_profile SET applied=draft,applied_revision=revision WHERE code=%s',(p['code'],))
    op=w.store.enqueue(p['code'],'verify',1,uuid.uuid4().hex,'admin',{})
    w.store.stage(str(op['id']),'running','request')
    with patch.object(w.gateways[0],'call') as call:
        w.drain()
        call.assert_not_called()
    assert w.store.operation(str(op['id']))['status']=='inconclusive'


def test_ledger_refresh_waits_for_gateway_log(worker):
    # Refreshing before LiteLLM flushes SpendLogs loads nothing and used to end inconclusive.
    w,p=worker
    op=w.store.enqueue(p['code'],'verify',1,uuid.uuid4().hex,'admin',{})
    w.store.stage(str(op['id']),'pending','evidence',{'gateway':'pending','reporting':'pending','call_id':'c',
        'started_at':'2026-01-01T00:00:00+00:00','deadline':time.time()+60,'expected_profile':p})
    logged=[False]
    def evidence(profile,call_id,result):
        return {**result,'request_id':'r','reason':'Gateway log found'} if logged[0] else dict(result)
    with patch.object(w,'evidence',side_effect=evidence), patch('backend.connection_worker.subprocess.run') as run:
        w.drain()
        run.assert_not_called()
        logged[0]=True
        w.drain()
        run.assert_called_once()
        w.drain()
        run.assert_called_once()
    assert w.store.operation(str(op['id']))['result']['refresh_attempted'] is True


def test_draft_profiles_block_legacy_rebuild(worker):
    w,p=worker
    from db import gateway_registry
    with psycopg2.connect(DSN) as cn:
        with pytest.raises(RuntimeError,match='connection profiles'):
            gateway_registry.guard_legacy(cn)


@pytest.mark.parametrize('code,alias,mode',[('test-agent','connection-test','single'),('test-multi','connection-multi','multiple')])
def test_live_verified_usage_after_refresh(worker,code,alias,mode):
    w,existing=worker
    from db import gateway_registry
    p=profile(code); p['secret_ref']=existing['draft']['secret_ref']; p['user_mode']=mode
    p['models']=[{'alias':alias,'upstream':'gemini/test'}]
    p['reporting_start_date']='2026-09-26'
    w.store.save(p,0,'admin')
    with gateway_registry.operation_lock(DSN), psycopg2.connect(DSN) as cn:
        rows=gateway_registry.parse_config(yaml.safe_dump({'version':1,'agents':[{k:p[k] for k in
            ['code','name','user_mode','reporting_start_date','active']}]}))
        gateway_registry.apply_config(cn,rows)
    with w.store.transaction() as cur:
        cur.execute('UPDATE gateway_connection_profile SET applied=draft,applied_revision=revision WHERE code=%s',(p['code'],))
    issue=w.store.enqueue(p['code'],'issue',1,uuid.uuid4().hex,'admin',{'budget':{'mode':'finite','usd':1}})
    issued=w.issue(str(issue['id']))
    try:
        verify=w.store.enqueue(p['code'],'verify',1,uuid.uuid4().hex,'admin',{})
        observed=w.verify(str(verify['id']),issued['key'])
        assert observed['status']=='pending',observed['result']
        result=observed['result']
        for _ in range(20):
            result=w.evidence(p,result['call_id'],result)
            if result.get('request_id'): break
            time.sleep(1)
        assert result.get('request_id'),result
        command=subprocess.run([sys.executable,'scripts/refresh_gateway.py','--db',DSN],
            cwd=Path(__file__).resolve().parents[1],capture_output=True,timeout=45,
            env={**os.environ,'TOKEN_LEDGER_DSN':DSN,'GATEWAY_DSN':w.gateway_dsn})
        assert command.returncode==0,command.stdout.decode(errors='replace')[-1500:]
        confirmed=w.evidence(p,result['call_id'],result)
        assert confirmed['gateway']=='verified' and confirmed['reporting']=='verified',confirmed
        assert 'waiting' not in confirmed['reason'] and 'awaits' not in confirmed['reason'],confirmed['reason']
        assert confirmed['external_agent']=='awaiting-agent-request'
        external=w.store.enqueue(p['code'],'verify',1,uuid.uuid4().hex,'admin',{'external_request_id':confirmed['request_id']})
        with patch.object(w.gateways[0],'call') as call:
            assert w.external_verify(str(external['id']))['result']['external_agent']=='failed'
            call.assert_not_called()
        assert issued['key'] not in json.dumps(w.store.detail(p['code']),default=str)
    finally:
        revoke=w.store.enqueue(p['code'],'revoke',1,uuid.uuid4().hex,'admin',{'key_aliases':[issued['key_alias']]})
        w.revoke(str(revoke['id']))


def test_failure_after_registry_commit_keeps_history(worker):
    w,p=worker; before=w.files(); reviewed=w.preview(p['code'],1)
    op=w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':reviewed['preview_hash']})
    from backend import connection_worker as module
    real_write=module.atomic_write
    failed=False
    def fail_export(path,data):
        nonlocal failed
        if Path(path)==w.paths['registry'] and not failed:
            with psycopg2.connect(DSN) as other:
                with other.cursor() as cur:
                    cur.execute('SELECT pg_try_advisory_lock(%s)',(74120924,))
                    assert not cur.fetchone()[0], 'Registry lock must remain held through export'
            failed=True; raise OSError('injected export failure after commit')
        return real_write(path,data)
    with patch.object(w,'rollout'),patch.object(module,'atomic_write',side_effect=fail_export):
        assert w.apply(str(op['id']))['status']=='failed'
    assert w.files()==before
    with psycopg2.connect(DSN) as cn:
        with cn.cursor() as cur:
            cur.execute('SELECT count(*) FROM dim_agent WHERE code=%s',(p['code'],))
            assert cur.fetchone()[0]==1
    assert w.preview(p['code'],1)['preview_hash']  # Recovered baseline retains committed registry.


@pytest.mark.parametrize('stage',['routes','override','registry-transaction'])
def test_apply_failure_before_commit_restores_configuration(worker,stage):
    w,p=worker; before=w.files(); reviewed=w.preview(p['code'],1)
    op=w.store.enqueue(p['code'],'apply',1,uuid.uuid4().hex,'admin',{'preview_hash':reviewed['preview_hash']})
    from backend import connection_worker as module
    real_write=module.atomic_write; real_apply=module.gateway_registry.apply_config
    injected=False
    def write(path,data):
        nonlocal injected
        if stage in ('routes','override') and Path(path)==w.paths[stage] and not injected:
            injected=True; raise OSError('injected candidate write failure')
        return real_write(path,data)
    def registry(cn,rows,dry_run=False):
        if stage=='registry-transaction' and not dry_run:
            raise RuntimeError('injected registry transaction failure')
        return real_apply(cn,rows,dry_run)
    with patch.object(w,'rollout'),patch.object(module,'atomic_write',side_effect=write),patch.object(module.gateway_registry,'apply_config',side_effect=registry):
        assert w.apply(str(op['id']))['status']=='failed'
    assert w.files()==before
    with psycopg2.connect(DSN) as cn:
        with cn.cursor() as cur:
            cur.execute('SELECT count(*) FROM dim_agent WHERE code=%s',(p['code'],))
            assert cur.fetchone()[0]==0
    assert w.preview(p['code'],1)['preview_hash']


def test_deployment_lock_serializes_worker(worker):
    w,p=worker
    with w.lock():
        with pytest.raises(Conflict,match='deployment'):
            with w.lock(): pass


def test_crash_after_key_creation_is_reconciled(worker):
    w,p=worker
    with w.store.transaction() as cur:
        cur.execute('UPDATE gateway_connection_profile SET applied=draft,applied_revision=revision WHERE code=%s',(p['code'],))
    op=w.store.enqueue(p['code'],'issue',1,uuid.uuid4().hex,'admin',{'budget':{'mode':'finite','usd':1}})
    alias='connection-'+str(op['id'])
    w.store.stage(str(op['id']),'running','issuing')
    w.gateways[0].call('/key/generate',{'key_alias':alias,'models':['connection-test'],
                    'metadata':{'tags':[p['code']],'quota_usd':1}})
    with pytest.raises(Conflict):
        w.store.enqueue(p['code'],'issue',1,uuid.uuid4().hex,'admin',{'budget':{'mode':'finite','usd':1}})
    with pytest.raises(Conflict): w.issue(str(op['id']))
    assert w.gateways[0].key(alias) is None
    assert w.store.operation(str(op['id']))['status']=='failed'


def test_wrong_tag_and_missing_cost_never_verified(worker):
    w,p=worker
    from datetime import datetime,timezone
    result={'gateway':'pending','started_at':datetime.now(timezone.utc).isoformat()}
    with patch('backend.connection_worker.psycopg2.connect') as connect:
        cursor=connect.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value=[('request-id',['another-agent'],'success',4,{'cost_breakdown':{'total_cost':1}})]
        assert w.evidence(p['draft'],'call-id',result)['gateway']=='failed'
        cursor.fetchall.return_value=[('request-id',[p['code']],'success',4,{'cost_breakdown':{}})]
        assert w.evidence(p['draft'],'call-id',result)['gateway']=='inconclusive'


def test_live_chat_quota_200_is_not_success(worker):
    w,p=worker
    chat=profile('test-chat'); chat['secret_ref']=p['draft']['secret_ref']
    chat['models']=[{'alias':'connection-chat','upstream':'gemini/test'}]; chat['quota_response_mode']='chat'
    w.store.save(chat,0,'admin')
    with w.store.transaction() as cur:
        cur.execute('UPDATE gateway_connection_profile SET applied=draft,applied_revision=revision WHERE code=%s',(chat['code'],))
    issue=w.store.enqueue(chat['code'],'issue',1,uuid.uuid4().hex,'admin',{'budget':{'mode':'finite','usd':0}})
    issued=w.issue(str(issue['id']))
    try:
        verify=w.store.enqueue(chat['code'],'verify',1,uuid.uuid4().hex,'admin',{})
        result=w.verify(str(verify['id']),issued['key'])
        assert result['status']=='failed' and result['stage']=='quota-blocked'
    finally:
        revoke=w.store.enqueue(chat['code'],'revoke',1,uuid.uuid4().hex,'admin',{'key_aliases':[issued['key_alias']]})
        w.revoke(str(revoke['id']))


def test_live_rollout_delivers_secret_to_both_instances(worker):
    w,p=worker
    fixture=Path(__file__).resolve().parent/'gateway-connections/compose.yaml'
    override=w.state/'fixture.override.yaml'
    override.write_text(yaml.safe_dump({'services':{name:{'env_file':[str(w.paths['environment'])]}
                        for name in ('litellm-1','litellm-2')}}),encoding='utf-8')
    w.paths['routes']=fixture.parent/'config.yaml'
    def fixture_compose(*args):
        result=subprocess.run(['docker','compose','-f',str(fixture),'-f',str(override),*args],capture_output=True,timeout=180)
        if result.returncode: raise RuntimeError('Isolated fixture Compose failed')
        return result.stdout
    try:
        with patch.object(w,'compose',side_effect=fixture_compose):
            w.rollout()  # Real recreate, health, loaded model IDs, config bytes and env checks on both instances.
    finally:
        # Remove temp env_file references before pytest removes the restricted fixture directory.
        subprocess.run(['docker','compose','-f',str(fixture),'up','-d','--no-deps','litellm-1','litellm-2'],
                       capture_output=True,timeout=180,check=True)
