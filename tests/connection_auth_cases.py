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
