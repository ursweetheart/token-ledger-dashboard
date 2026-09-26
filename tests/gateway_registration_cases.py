"""Gateway-only onboarding: pure validation and opt-in disposable PostgreSQL tests.

Run only against the dedicated gateway-onboarding-test-pg container. Never falls
back to project credentials. Each integration test creates its own database.
"""
import os
import shutil
import subprocess
import sys
import uuid
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from db import connect, gateway_registry as reg, load_gateway as lg


def config(code="support-helper", mode="multiple"):
    return reg.parse_config(f"""version: 1
agents:
  - code: {code}
    name: Support Helper
    user_mode: {mode}
    reporting_start_date: 2026-09-01
""")


@pytest.mark.parametrize("text", [
    "version: 1\nversion: 1\nagents: []", "version: true\nagents: []",
    "version: 1\nagents: null", "version: 1\nagents: []\nsecret: x",
    "version: 1\nagents: [{code: yes}]",
])
def test_invalid_yaml(text):
    with pytest.raises(ValueError):
        reg.parse_config(text)


@pytest.mark.parametrize("value,valid", [("Alice", True), ("alice", True),
    (" Alice ", True), ("é" * 128, True), ("é" * 129, False),
    ("\ud800", False), ("\x00", False), ("\nAlice", False), ("  ", False), (None, False)])
def test_exact_identity_validation(value, valid):
    assert reg.valid_identity(value) is valid


@pytest.mark.parametrize("field,value", [("code", "UPPER"), ("name", " "),
    ("user_mode", "people"), ("active", "true"), ("reporting_start_date", None),
    ("reporting_start_date", "2026-02-30"), ("unknown", 1)])
def test_invalid_agent_fields(field, value):
    import yaml
    rows = config()
    rows[0][field] = value
    with pytest.raises(ValueError):
        reg.parse_config(yaml.safe_dump({"version": 1, "agents": rows}))


@pytest.fixture
def database(request):
    admin_dsn = os.environ.get("GATEWAY_ONBOARDING_TEST_DSN")
    if not admin_dsn:
        pytest.skip("explicit isolated PostgreSQL DSN required")
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import parse_dsn
    from sqlalchemy.engine import URL
    params = parse_dsn(admin_dsn)
    assert params.get("dbname") == "onboarding_test"
    assert params.get("host") == "127.0.0.1"
    assert params.get("user") == "onboarding"
    admin = psycopg2.connect(admin_dsn)
    admin.autocommit = True
    name = "onboarding_" + uuid.uuid4().hex
    with admin.cursor() as cur:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    dsn = URL.create("postgresql", username=params["user"], password=params.get("password"),
                     host=params["host"], port=int(params.get("port", 5432)),
                     database=name).render_as_string(hide_password=False)
    try:
        if hasattr(request, "param"):
            from alembic import command
            from alembic.config import Config
            cfg = Config("alembic.ini")
            cfg.attributes["explicit_dsn"] = dsn
            command.upgrade(cfg, request.param)
        else:
            connect.apply_migrations(dsn)
        yield dsn
    finally:
        # Exact UUID database created above, never a schema in the live project DB.
        with admin.cursor() as cur:
            cur.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        admin.close()


def query(dsn, sql, params=()):
    cn, _ = connect.open_db(dsn)
    try:
        with cn.cursor() as cur:
            cur.execute(sql, params or None)
            result = cur.fetchall() if cur.description else None
        cn.commit()
        return result
    finally:
        cn.close()


def apply(dsn, rows, dry=False):
    with reg.operation_lock(dsn):
        cn, _ = connect.open_db(dsn)
        try:
            plan = reg.apply_config(cn, rows, dry)
            cn.commit()
            return plan
        finally:
            cn.close()


def snapshot(dsn):
    tables = [r[0] for r in query(dsn, "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY 1")]
    return {t: query(dsn, f'SELECT row_to_json(t)::text FROM "{t}" t ORDER BY row_to_json(t)::text') for t in tables}


def test_apply_atomic_idempotent_and_readonly_preview(database):
    dsn = database
    before = snapshot(dsn)
    seq = query(dsn, "SELECT last_value,is_called FROM gateway_agent_id_seq")
    assert apply(dsn, config(), True) == [{"code": "support-helper", "action": "create"}]
    assert snapshot(dsn) == before
    assert query(dsn, "SELECT last_value,is_called FROM gateway_agent_id_seq") == seq
    apply(dsn, config())
    once = snapshot(dsn)
    assert apply(dsn, config())[0]["action"] == "unchanged"
    assert snapshot(dsn) == once
    assert apply(dsn, [])[0]["action"] == "retained"
    bad = config("new-valid") + config(mode="single")
    with pytest.raises(ValueError, match="immutable"):
        apply(dsn, bad)
    assert snapshot(dsn) == once
    update = config()
    update[0].update(name="Renamed", active=False)
    apply(dsn, update)
    assert query(dsn, "SELECT name,is_running FROM dim_agent") == [("Renamed", False)]
    with pytest.raises(RuntimeError, match="Bulk reload refused"):
        connect.rebuild(dsn)


def test_lock_across_processes(database):
    with reg.operation_lock(database):
        child = subprocess.run([sys.executable, "-c",
            "from db.gateway_registry import operation_lock; import sys\nwith operation_lock(sys.argv[1]): pass", database],
            capture_output=True, text=True, timeout=10)
        assert child.returncode != 0
        assert "already running" in child.stderr
    with reg.operation_lock(database):
        with reg.operation_lock(database):
            pass


def test_apply_rolls_back_after_partial_inserts(database, monkeypatch):
    before = snapshot(database)
    original = reg.insert_account
    def fail_after_insert(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError("injected registration failure")
    monkeypatch.setattr(reg, "insert_account", fail_after_insert)
    with pytest.raises(RuntimeError, match="injected"):
        apply(database, config())
    assert snapshot(database) == before


def source_fixture(dsn):
    query(dsn, '''CREATE TABLE "LiteLLM_SpendLogs" (
        request_id text PRIMARY KEY,"startTime" timestamp,model text,end_user text,
        request_tags jsonb,prompt_tokens bigint,completion_tokens bigint,total_tokens bigint,
        metadata jsonb,status text,request_duration_ms integer,api_key text,cache_hit text)''')


def source_row(dsn, call_id, code, identity, timestamp="2026-09-02 01:00:00", status="success"):
    import json
    tags = code if isinstance(code, list) else ([code] if code else [])
    query(dsn, '''INSERT INTO "LiteLLM_SpendLogs" VALUES
        (%s,%s,'test/model',%s,%s,10,20,30,%s,%s,120,'fixture-key','False')''',
        (call_id, timestamp, identity, json.dumps(tags),
         json.dumps({"cost_breakdown": {"total_cost": "0.001"},
                     "usage_object": {"completion_tokens_details": {"text_tokens": 20}}}), status))


def test_load_backfill_rollups_api_and_replay(database, monkeypatch):
    from scripts import refresh_gateway as refresh
    from backend import store
    from backend.gateway_identities import identities
    dsn = database
    source_fixture(dsn)
    apply(dsn, config("newest", "single"))
    source_row(dsn, "newest", "newest", "svc.newest", "2026-09-24 01:00:00")
    monkeypatch.setattr(lg.connect, "GATEWAY_DSN", dsn)
    assert refresh.run_once(dsn, True) == 0
    apply(dsn, config() + config("second"))
    for i, (code, user, ts, status) in enumerate([
        ("support-helper", "Alice", "2026-09-01 01:00:00", "success"),
        ("support-helper", "alice", "2026-09-02 01:00:00", "success"),
        ("second", "Alice", "2026-09-02 01:00:00", "success"),
        ("support-helper", "Bob", "2026-09-02 01:00:00", "failure"),
        ("support-helper", " ", "2026-09-02 01:00:00", "success"),
        ("support-helper", "before", "2026-08-31 16:59:59", "success"),
        ("support-helper", "boundary", "2026-08-31 17:00:00", "success"),
        ("not-registered", "ghost", "2026-09-02 01:00:00", "success"),
    ]):
        source_row(dsn, f"fixture-{i}", code, user, ts, status)
    source_row(dsn, "dup_cache_hit", "support-helper", "ghost-cache")
    before = snapshot(dsn)
    assert lg.main(["--db", dsn, "--gateway-db", dsn, "--dry-run"]) == 0
    assert snapshot(dsn) == before
    assert lg.main(["--db", dsn, "--gateway-db", dsn]) == 0
    assert query(dsn, "SELECT COUNT(*) FROM gateway_agent_registry WHERE pending_backfill") == [(2,)]
    assert refresh.run_once(dsn, True) == 0
    assert query(dsn, "SELECT COUNT(*) FROM gateway_agent_registry WHERE pending_backfill") == [(0,)]
    assert query(dsn, "SELECT count(*),sum(total_tokens),sum(cost_usd) FROM fact_call") == [(7, 210, Decimal("0.007"))]
    observed = query(dsn, "SELECT external_user_id,account_id FROM gateway_observed_identity ORDER BY agent_id,external_user_id")
    assert len(observed) == 5
    assert len({r[1] for r in observed}) == 5
    assert [r[0] for r in observed].count("Alice") == 2
    facts = query(dsn, "SELECT call_id,account_id,total_tokens,cost_usd FROM fact_call ORDER BY 1")
    assert lg.main(["--db", dsn, "--gateway-db", dsn, "--full"]) == 0
    assert query(dsn, "SELECT call_id,account_id,total_tokens,cost_usd FROM fact_call ORDER BY 1") == facts
    cn, _ = connect.open_db(dsn)
    try:
        result = identities(cn, "2026-09-01", "2026-09-30")
        assert result["calls"] == 6 and result["total_tokens"] == 180
        assert any(r["external_user_id"] == "Bob" and r["calls"] == 0 and r["first_seen"] for r in result["rows"])
        assert not any("gw:" in str(r["external_user_id"]) for r in result["rows"])
        assert all(a["rate_pct"] is None for a in store.adoption(cn) if a.get("kind") == "gateway_observed")
        assert not store.accounts(cn)
        assert len(identities(cn, "2026-09-01", "2026-09-30", limit=1)["rows"]) == 1
    finally:
        cn.close()


def test_discovery_rollback_and_namespace(database):
    apply(database, config())
    aid = query(database, "SELECT agent_id FROM gateway_agent_registry")[0][0]
    cn, _ = connect.open_db(database)
    try:
        with reg.operation_lock(database):
            first = reg.discover(cn, aid, "admin", datetime(2026, 9, 2))
            assert reg.discover(cn, aid, "admin", datetime(2026, 9, 3)) == first
            cn.rollback()
        assert query(database, "SELECT count(*) FROM gateway_observed_identity") == [(0,)]
        assert query(database, "SELECT count(*) FROM account WHERE kind='gateway_observed'") == [(0,)]
    finally:
        cn.close()


@pytest.mark.parametrize("stage", ["daily", "hourly", "performance", "heartbeat", "gateway"])
def test_failed_refresh_preserves_pending(database, monkeypatch, stage):
    from scripts import refresh_gateway as refresh
    from types import SimpleNamespace
    dsn = database
    source_fixture(dsn)
    apply(dsn, config())
    source_row(dsn, "test", "support-helper", "Alice")
    monkeypatch.setattr(lg.connect, "GATEWAY_DSN", dsn)
    original = refresh.subprocess.run
    names = {"daily": "build_usage_daily.py", "hourly": "build_usage_hourly.py",
             "performance": "build_performance.py"}
    with monkeypatch.context() as patch:
        if stage in names:
            def fail(command, **kwargs):
                if command[1].endswith(names[stage]):
                    return SimpleNamespace(returncode=1, stdout="injected rollup failure", stderr="")
                return original(command, **kwargs)
            patch.setattr(refresh.subprocess, "run", fail)
        elif stage == "heartbeat":
            patch.setattr(refresh, "write_heartbeat", lambda *args: False)
        else:
            patch.setattr(refresh.load_gateway, "main", lambda *args: 1)
        assert refresh.run_once(dsn, True) == 1
    assert query(dsn, "SELECT pending_backfill FROM gateway_agent_registry") == [(True,)]
    assert refresh.run_once(dsn, True) == 0
    assert query(dsn, "SELECT pending_backfill FROM gateway_agent_registry") == [(False,)]
    assert query(dsn, "SELECT count(*),sum(total_tokens) FROM fact_call") == [(1, 30)]


def test_api_auth_boundaries_and_unknown_denominator(database, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("DASHBOARD_KEY", "onboarding-fixture")
    monkeypatch.setenv("DASHBOARD_OPEN", "0")
    monkeypatch.setenv("QUOTA_DISABLED", "1")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "unused-fixture")
    from backend import main, store
    monkeypatch.setattr(main, "DASHBOARD_KEY", "onboarding-fixture")
    monkeypatch.setattr(main, "DASHBOARD_OPEN", False)
    monkeypatch.setattr(store, "DSN", database)
    apply(database, config())
    aid = query(database, "SELECT agent_id FROM gateway_agent_registry")[0][0]
    cn, _ = connect.open_db(database)
    try:
        with reg.operation_lock(database):
            for i in range(10):
                reg.discover(cn, aid, f"observed-{i}", datetime(2026, 9, 2))
            cn.commit()
    finally:
        cn.close()
    client = TestClient(main.app)
    url = "/api/gateway-identities"
    assert client.get(url).status_code == 401
    client.headers["Authorization"] = "Bearer onboarding-fixture"
    assert client.get(url).status_code == 200
    assert client.get(url + "?limit=0").status_code == 422
    assert client.get(url + "?offset=-1").status_code == 422
    assert client.get(url + "?agent_id=0").status_code == 422
    assert client.get(url + "?start=2026-02-30").status_code == 400
    assert client.get(url + "?agent_id=999999").json()["rows"] == []
    row = client.get("/api/adoption").json()["rows"][0]
    assert row["rate_pct"] is None and row["provisioned"] is None
    assert row["denominator_known"] is False
    assert client.get("/api/accounts").json()["rows"] == []


@pytest.mark.parametrize("database", ["012_nhip_tim_lam_moi", "013_model_catalog_pricing"], indirect=True)
def test_upgrade_preserves_legacy_and_grants(database, tmp_path):
    dsn = database
    query(dsn, """INSERT INTO dim_agent VALUES
        (41,'legacy','Legacy',NULL,false,NULL,'2026-08-01',NULL,true,false);
        INSERT INTO dim_unit(unit_id,agent_id,name,is_technical) VALUES ('legacy-unit',41,'Legacy',false);
        INSERT INTO account(account_id,username,kind,unit_id,is_shared,unit_agent_id,unit_conflict)
        VALUES (9001,'Alice','real','legacy-unit',0,41,0);
        INSERT INTO dim_model VALUES (71,'legacy-model','legacy','test');
        INSERT INTO fact_call(call_id,agent_id,ts_raw,tz_confirmed,ts_local,user_id,account_id,
          unit_id,model_id,prompt_tokens,completion_tokens,total_tokens,source,cost_usd,outcome)
        VALUES ('legacy-call',41,'2026-08-02',true,'2026-08-02 07:00','Alice',9001,
          'legacy-unit',71,10,20,30,'app',0.123456,'success');
        DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='api_readonly')
          THEN CREATE ROLE api_readonly; END IF; END $$;
        GRANT SELECT ON account,dim_agent,fact_call TO api_readonly;""")
    before = snapshot(dsn)
    grants = query(dsn, "SELECT table_name,privilege_type FROM information_schema.role_table_grants WHERE grantee='api_readonly' ORDER BY 1,2")
    connect.apply_migrations(dsn)
    after = snapshot(dsn)
    for table in before:
        if table != "alembic_version":
            assert after[table] == before[table], table
    assert set(grants) <= set(query(dsn, "SELECT table_name,privilege_type FROM information_schema.role_table_grants WHERE grantee='api_readonly'"))
    assert query(dsn, "SELECT has_table_privilege('api_readonly','gateway_agent_registry','SELECT'),has_table_privilege('api_readonly','gateway_agent_registry','INSERT')") == [(True, False)]
    with pytest.raises(ValueError, match="legacy agent"):
        apply(dsn, config("legacy"))
    apply(dsn, config())
    assert query(dsn, "SELECT agent_id FROM dim_agent WHERE code='support-helper'") == [(42,)]
    assert query(dsn, "SELECT min(account_id) FROM account WHERE kind<>'real'")[0][0] > 9001
    cn, _ = connect.open_db(dsn)
    try:
        with reg.operation_lock(dsn):
            observed = reg.discover(cn, 42, "Alice", datetime(2026, 9, 2))
            cn.commit()
        assert observed != 9001
    finally:
        cn.close()
    protected = snapshot(dsn)
    # CLI loaders resolve source files before checking the database guard.
    # Use a disposable checkout with minimal inputs, independent of local pulls.
    root = Path(__file__).resolve().parents[1]
    shutil.copytree(root / "db", tmp_path / "db", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "scripts").mkdir()
    shutil.copy2(root / "scripts" / "rebuild_db.py", tmp_path / "scripts" / "rebuild_db.py")
    sources = {
        "data/raw_web/ralli/2026-09-01": (
            "units.json", "users-list.json", "db-token_usage-raw.json"),
        "data/raw_web/tla-hd/2026-09-01": (
            "units-tree.json", "units-members.json", "token-usage-year.json",
            "token-usage-filter-options.json", "usage-day-user-model.json"),
        "data/da_xu_ly/billing": ("billing_2026-09-01.csv",),
    }
    for folder, names in sources.items():
        directory = tmp_path / folder
        directory.mkdir(parents=True)
        for name in names:
            (directory / name).touch()
    for script in ("db/load_org.py", "scripts/rebuild_db.py", "db/load_billing.py"):
        args = [sys.executable, script, "--db", dsn]
        if script.endswith("load_billing.py"):
            args += ["--rebuild"]
        result = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True, timeout=15)
        assert result.returncode != 0
        assert "Bulk reload refused" in result.stderr
        assert snapshot(dsn) == protected


def test_adversarial_identities_and_tag_counters(database):
    dsn = database
    source_fixture(dsn)
    query(dsn, """INSERT INTO dim_agent VALUES
        (41,'legacy','Legacy',NULL,false,NULL,'2026-08-01',NULL,true,false);
        INSERT INTO dim_unit(unit_id,agent_id,name,is_technical) VALUES ('legacy-unit',41,'Legacy',false);
        INSERT INTO account(account_id,username,kind,unit_id,is_shared,unit_agent_id,unit_conflict)
        VALUES (9001,'admin','real','legacy-unit',0,41,0);
        INSERT INTO dim_model VALUES (71,'legacy-model','legacy','test');
        INSERT INTO fact_call(call_id,agent_id,ts_raw,tz_confirmed,ts_local,user_id,account_id,
          unit_id,model_id,prompt_tokens,completion_tokens,total_tokens,source,cost_usd,outcome)
        VALUES ('legacy-call',41,'2026-08-02',true,'2026-08-02 07:00','admin',9001,
          'legacy-unit',71,10,20,30,'app',0.123456,'success');""")
    legacy_facts = query(dsn, "SELECT call_id,account_id,cost_usd FROM fact_call WHERE call_id='legacy-call'")

    c1, c2 = config("agent-one"), config("agent-two")
    c1[0]["name"] = "Agent One"
    c2[0]["name"] = "Agent Two"
    apply(dsn, c1 + c2)
    a1 = query(dsn, "SELECT agent_id FROM dim_agent WHERE code='agent-one'")[0][0]
    a2 = query(dsn, "SELECT agent_id FROM dim_agent WHERE code='agent-two'")[0][0]

    source_row(dsn, "call-adv-1", "agent-one", "admin")
    source_row(dsn, "call-adv-2", "agent-two", "admin")
    source_row(dsn, "call-adv-3", "agent-one", "Alice")
    source_row(dsn, "call-adv-4", "agent-one", "alice")
    source_row(dsn, "call-adv-5", "agent-one", "Nguyễn Văn A")
    source_row(dsn, "call-adv-6", "agent-one", "   ")
    source_row(dsn, "call-adv-7", "agent-one", "\nEvil")
    source_row(dsn, "call-adv-8", "agent-one", "é" * 129)
    source_row(dsn, "call-adv-9", "agent-one", "FailureOnlyUser", status="failure")
    source_row(dsn, "call-adv-10_cache_hit12345", "agent-one", "CacheUser")
    source_row(dsn, "call-adv-11", ["agent-one", "agent-two"], "MultiTagUser")
    source_row(dsn, "call-adv-12", "unknown-agent", "UnknownTagUser")

    assert lg.main(["--db", dsn, "--gateway-db", dsn]) == 0

    assert query(dsn, "SELECT call_id,account_id,cost_usd FROM fact_call WHERE call_id='legacy-call'") == legacy_facts
    assert query(dsn, "SELECT username,kind FROM account WHERE account_id=9001") == [("admin", "real")]

    obs_admin = query(dsn, "SELECT agent_id,account_id FROM gateway_observed_identity WHERE external_user_id='admin' ORDER BY agent_id")
    assert len(obs_admin) == 2
    acc_a1, acc_a2 = obs_admin[0][1], obs_admin[1][1]
    assert acc_a1 != acc_a2
    assert acc_a1 != 9001 and acc_a2 != 9001

    obs_alice = query(dsn, "SELECT external_user_id,account_id FROM gateway_observed_identity WHERE agent_id=%s AND external_user_id IN ('Alice','alice') ORDER BY external_user_id", (a1,))
    assert len(obs_alice) == 2
    assert obs_alice[0][1] != obs_alice[1][1]

    obs_nv = query(dsn, "SELECT external_user_id,account_id FROM gateway_observed_identity WHERE agent_id=%s AND external_user_id='Nguyễn Văn A'", (a1,))
    assert len(obs_nv) == 1

    assert not query(dsn, "SELECT 1 FROM gateway_observed_identity WHERE external_user_id IN (%s, %s, %s)", ("   ", "\nEvil", "é" * 129))

    anchor_a1 = query(dsn, "SELECT account_id FROM account WHERE unit_agent_id=%s AND kind='whole_agent'", (a1,))[0][0]
    for cid in ("call-adv-6", "call-adv-7", "call-adv-8"):
        assigned = query(dsn, "SELECT account_id FROM fact_call WHERE call_id=%s", (cid,))
        assert assigned == [(anchor_a1,)]

    obs_fail = query(dsn, "SELECT external_user_id FROM gateway_observed_identity WHERE external_user_id='FailureOnlyUser'")
    assert len(obs_fail) == 1

    for dropped_cid in ("call-adv-10_cache_hit12345", "call-adv-11", "call-adv-12"):
        assert not query(dsn, "SELECT 1 FROM fact_call WHERE call_id=%s", (dropped_cid,))


def test_concurrent_discovery(database):
    import concurrent.futures
    import time
    dsn = database
    apply(dsn, config())
    aid = query(dsn, "SELECT agent_id FROM gateway_agent_registry")[0][0]
    identity = "racing-user"

    def worker(worker_id):
        for _ in range(30):
            try:
                cn, _ = connect.open_db(dsn)
                try:
                    with reg.operation_lock(dsn):
                        acc_id = reg.discover(cn, aid, identity, datetime(2026, 9, 2))
                        cn.commit()
                        return acc_id
                finally:
                    cn.close()
            except RuntimeError as e:
                if "already running" in str(e):
                    time.sleep(0.05)
                    continue
                raise
        raise TimeoutError("worker timed out waiting for operation_lock")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(worker, 1)
        f2 = executor.submit(worker, 2)
        r1, r2 = f1.result(), f2.result()

    assert r1 == r2 and isinstance(r1, int)
    rows = query(dsn, "SELECT account_id FROM gateway_observed_identity WHERE agent_id=%s AND external_user_id=%s", (aid, identity))
    assert len(rows) == 1
    assert rows[0][0] == r1


def test_api_duplicate_external_ids_and_filter_boundaries(database, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setenv("DASHBOARD_KEY", "onboarding-fixture")
    monkeypatch.setenv("DASHBOARD_OPEN", "0")
    monkeypatch.setenv("QUOTA_DISABLED", "1")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "unused-fixture")
    from backend import main, store
    monkeypatch.setattr(main, "DASHBOARD_KEY", "onboarding-fixture")
    monkeypatch.setattr(main, "DASHBOARD_OPEN", False)
    monkeypatch.setattr(store, "DSN", database)
    source_fixture(database)
    apply(database, config("agent-one") + config("agent-two"))
    a1 = query(database, "SELECT agent_id FROM dim_agent WHERE code='agent-one'")[0][0]
    a2 = query(database, "SELECT agent_id FROM dim_agent WHERE code='agent-two'")[0][0]

    source_row(database, "call-a1-alice", "agent-one", "Alice", "2026-09-02 01:00:00")
    source_row(database, "call-a2-alice", "agent-two", "Alice", "2026-09-02 01:00:00")
    assert lg.main(["--db", database, "--gateway-db", database]) == 0

    client = TestClient(main.app)
    client.headers["Authorization"] = "Bearer onboarding-fixture"

    res1 = client.get(f"/api/gateway-identities?agent_id={a1}&start=2026-09-01&end=2026-09-30").json()
    assert res1["total"] == 2
    assert {r["kind"] for r in res1["rows"]} == {"whole_agent", "gateway_observed"}
    alice1 = [r for r in res1["rows"] if r["kind"] == "gateway_observed"][0]
    assert alice1["agent_id"] == a1 and alice1["external_user_id"] == "Alice"

    res2 = client.get(f"/api/gateway-identities?agent_id={a2}&start=2026-09-01&end=2026-09-30").json()
    assert res2["total"] == 2
    assert {r["kind"] for r in res2["rows"]} == {"whole_agent", "gateway_observed"}
    alice2 = [r for r in res2["rows"] if r["kind"] == "gateway_observed"][0]
    assert alice2["agent_id"] == a2 and alice2["external_user_id"] == "Alice"
    assert alice1["account_id"] != alice2["account_id"]

    res_all = client.get("/api/gateway-identities?start=2026-09-01&end=2026-09-30").json()
    assert res_all["total"] == 4
    alice_rows = [r for r in res_all["rows"] if r["external_user_id"] == "Alice"]
    assert len(alice_rows) == 2
    assert {r["agent_id"] for r in alice_rows} == {a1, a2}
