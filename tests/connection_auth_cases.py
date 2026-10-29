"""Dependency-backed auth tests that need neither Docker nor a database."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.connection_api import router


def settings(**overrides):
    values={'CONNECTIONS_ENABLED':'1','CONNECTION_ADMIN_KEY':'admin-only',
            'CONNECTION_WORKER_KEY':'worker-only','CONNECTION_WORKER_URL':'http://127.0.0.1:8766',
            'CONNECTION_ADMIN_DSN':'postgresql://never-contacted/test','DASHBOARD_KEY':'reader-only'}
    values.update(overrides)
    return lambda name:values.get(name,'')


@pytest.mark.parametrize('field',['CONNECTION_ADMIN_KEY','CONNECTION_WORKER_KEY','CONNECTION_WORKER_URL','CONNECTION_ADMIN_DSN'])
def test_feature_missing_config_fails_closed(field):
    with pytest.raises(SystemExit): router(settings(**{field:''}))


def test_reader_and_admin_cannot_share_credential():
    with pytest.raises(SystemExit): router(settings(CONNECTION_ADMIN_KEY='reader-only'))


def test_worker_remote_plain_http_rejected():
    with pytest.raises(SystemExit): router(settings(CONNECTION_WORKER_URL='http://remote-host:8766'))


def test_open_mode_never_grants_admin():
    app=FastAPI(); app.include_router(router(settings(DASHBOARD_OPEN='1')))
    client=TestClient(app)
    assert client.post('/api/gateway-connections',json={}).status_code==401
    assert client.post('/api/gateway-connections',json={},headers={'Authorization':'Bearer reader-only'}).status_code==403


def test_disabled_feature_no_database_fallback():
    app=FastAPI(); app.include_router(router(settings(CONNECTIONS_ENABLED='0',CONNECTION_ADMIN_DSN='')))
    client=TestClient(app)
    assert client.get('/api/gateway-connections',headers={'Authorization':'Bearer any'}).status_code==503


ADMIN={'Authorization':'Bearer admin-only'}
READER={'Authorization':'Bearer reader-only'}


def health_client(**overrides):
    app=FastAPI(); app.include_router(router(settings(**overrides)))
    return TestClient(app)


@pytest.mark.parametrize('body',[{'run_at':'25:00'},{'run_at':'7h'},{'run_at':'7:30'},{'run_at':8},{},
                                 {'run_at':'07:30','extra':1}])
def test_health_schedule_rejects_bad_time_before_touching_database(body):
    assert health_client().put('/api/agent-health/schedule',json=body,headers=ADMIN).status_code==422


def test_health_writes_refuse_the_dashboard_key():
    client=health_client()
    assert client.put('/api/agent-health/schedule',json={'run_at':'07:30'},headers=READER).status_code==403
    assert client.post('/api/agent-health/run',headers=READER).status_code==403


def test_health_writes_are_unavailable_when_administration_is_off():
    client=health_client(CONNECTIONS_ENABLED='0',CONNECTION_ADMIN_DSN='')
    assert client.put('/api/agent-health/schedule',json={'run_at':'07:30'},headers=ADMIN).status_code==503
    assert client.post('/api/agent-health/run',headers=ADMIN).status_code==503


class FakeCursor:
    def __init__(self,row=None,error=None):
        self.row,self.error,self.sql=row,error,[]
    def execute(self,sql,params=None):
        self.sql.append(sql)
        if self.error: raise self.error
    def fetchone(self):
        return self.row


def fake_transactions(monkeypatch,*cursors):
    from contextlib import contextmanager
    from backend.connection_store import ConnectionStore
    queue=list(cursors)
    @contextmanager
    def transaction(self):
        yield queue.pop(0)
    monkeypatch.setattr(ConnectionStore,'transaction',transaction)


def test_health_schedule_saves_a_valid_time(monkeypatch):
    from datetime import time
    cur=FakeCursor(row={'run_at':time(7,30),'last_run_date':None})
    fake_transactions(monkeypatch,cur)
    response=health_client().put('/api/agent-health/schedule',json={'run_at':'07:30'},headers=ADMIN)
    assert response.status_code==200
    assert response.json()=={'run_at':'07:30','last_run_date':None}
    assert 'UPDATE agent_health_setting' in cur.sql[0]


def test_health_run_now_queues_a_manual_run(monkeypatch):
    cur=FakeCursor()
    fake_transactions(monkeypatch,cur)
    response=health_client().post('/api/agent-health/run',headers=ADMIN)
    assert response.status_code==202
    assert response.json()['id']
    assert "'manual'" in cur.sql[0]


def test_health_run_now_twice_returns_the_active_run(monkeypatch):
    import psycopg2.errors
    fake_transactions(monkeypatch,FakeCursor(error=psycopg2.errors.UniqueViolation()),
                      FakeCursor(row={'id':'11111111-1111-1111-1111-111111111111'}))
    response=health_client().post('/api/agent-health/run',headers=ADMIN)
    assert response.status_code==409
    assert response.json()['detail']['id']=='11111111-1111-1111-1111-111111111111'


def test_health_shipped_config_loads():
    # Ở đây chứ không ở test_watch_agents.py: cần PyYAML, mà bộ test_*.py chạy trên máy sạch.
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(root/'scripts'))
    import watch_agents
    assert 'ralli' in watch_agents.load_config(root/'config'/'agent-health.yaml')
