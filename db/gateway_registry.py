"""Gateway-only registration. No exports, provider calls, or implicit migrations.

Callers own transactions. operation_lock serializes apply and complete refresh cycles;
nested calls in the same Python context share ownership (never an environment bypass).
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timedelta
import hashlib
import json
import re
import unicodedata

try:
    from . import connect
except ImportError:
    import connect

LOCK_ID = 74120924
_held = ContextVar("gateway_registry_lock", default=None)


def available(cn):
    with cn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.gateway_agent_registry')")
        return cur.fetchone()[0] is not None


@contextmanager
def operation_lock(dsn):
    held = _held.get()
    if held is not None:
        if held != dsn:
            raise RuntimeError("Nested Gateway operation targets a different database")
        yield
        return
    cn, _ = connect.open_db(dsn)
    token = None
    try:
        with cn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_ID,))
            if not cur.fetchone()[0]:
                raise RuntimeError("Gateway apply/refresh already running; retry after it finishes")
        cn.commit()
        token = _held.set(dsn)
        yield
    finally:
        if token is not None:
            _held.reset(token)
        cn.close()  # Session advisory lock released even after a failed transaction.


def guard_legacy(cn):
    if available(cn):
        with cn.cursor() as cur:
            cur.execute("SELECT EXISTS (SELECT 1 FROM gateway_agent_registry)")
            if cur.fetchone()[0]:
                raise RuntimeError("Bulk reload refused: Gateway agents are registered. "
                                   "Use apply_gateway_agents.py and refresh_gateway.py; "
                                   "do not rebuild or run load_org.py.")


def read_registry(cn):
    if not available(cn):
        return {}
    with cn.cursor() as cur:
        cur.execute("SELECT r.agent_id,g.code,r.user_mode,r.reporting_start_date,"
                    "r.pending_backfill FROM gateway_agent_registry r "
                    "JOIN dim_agent g USING(agent_id)")
        return {a: dict(code=c, user_mode=m, start=d, pending=p)
                for a, c, m, d, p in cur.fetchall()}


def parse_config(text):
    import yaml

    class StrictLoader(yaml.SafeLoader):
        pass

    def mapping(loader, node):
        result = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node)
            if not isinstance(key, str) or key in result:
                raise ValueError(f"Invalid or duplicate YAML key: {key!r}")
            result[key] = loader.construct_object(value_node)
        return result

    StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
    root = yaml.load(text, Loader=StrictLoader)
    if not isinstance(root, dict) or set(root) != {"version", "agents"}:
        raise ValueError("Config requires exactly version and agents")
    if type(root["version"]) is not int or root["version"] != 1:
        raise ValueError("Only config version 1 is supported")
    if not isinstance(root["agents"], list):
        raise ValueError("agents must be a list")
    seen, rows = set(), []
    required = {"code", "name", "user_mode", "reporting_start_date"}
    for i, row in enumerate(root["agents"]):
        if not isinstance(row, dict) or not required <= set(row) or set(row) - required - {"active"}:
            raise ValueError(f"agents[{i}]: missing or unknown fields")
        code = row["code"]
        if not isinstance(code, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", code):
            raise ValueError(f"agents[{i}]: invalid code")
        if code in seen:
            raise ValueError(f"Duplicate agent code: {code}")
        seen.add(code)
        if not isinstance(row["name"], str) or not row["name"].strip():
            raise ValueError(f"{code}: name must be nonblank")
        if row["user_mode"] not in ("single", "multiple"):
            raise ValueError(f"{code}: user_mode must be single or multiple")
        active = row.get("active", True)
        if type(active) is not bool:
            raise ValueError(f"{code}: active must be a boolean")
        raw = row["reporting_start_date"]
        if type(raw) is date:  # SafeLoader supports an unquoted ISO date too.
            day = raw
        elif isinstance(raw, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            day = date.fromisoformat(raw)
        else:
            raise ValueError(f"{code}: reporting_start_date must be YYYY-MM-DD")
        rows.append(dict(code=code, name=row["name"].strip(), user_mode=row["user_mode"],
                         reporting_start_date=day, active=active))
    return rows


def _allocate(cur, table, column, sequence):
    # All identifiers are internal constants; caller holds operation_lock.
    # Legacy loaders may have inserted IDs after migration but before first apply.
    cur.execute(f"SELECT nextval('{sequence}')")
    value = cur.fetchone()[0]
    cur.execute(f"SELECT COALESCE(MAX({column}),0) FROM {table}")
    maximum = cur.fetchone()[0]
    if value <= maximum:
        value = maximum + 1
        cur.execute("SELECT setval(%s,%s,true)", (sequence, value))
    return value


def insert_account(cur, agent_id, username, kind, unit_id, label=None):
    account_id = _allocate(cur, "account", "account_id", "gateway_account_id_seq")
    cur.execute("INSERT INTO account(account_id,username,full_name,kind,unit_id,is_shared,"
                "unit_agent_id,unit_conflict) VALUES (%s,%s,%s,%s,%s,1,%s,0)",
                (account_id, username, label, kind, unit_id, agent_id))
    return account_id


def apply_config(cn, rows, dry_run=False):
    if not available(cn):
        raise RuntimeError("Registry schema missing; run the reviewed migrations first")
    registry = read_registry(cn)
    with cn.cursor() as cur:
        cur.execute("SELECT code,agent_id,name,is_running FROM dim_agent")
        existing = {code: (aid, name, active) for code, aid, name, active in cur.fetchall()}
        plan = []
        for row in rows:
            code = row["code"]
            old = existing.get(code)
            if old:
                if old[0] not in registry:
                    raise ValueError(f"{code}: legacy agent {old[0]} cannot be taken over")
                policy = registry[old[0]]
                if policy["user_mode"] != row["user_mode"] or policy["start"] != row["reporting_start_date"]:
                    raise ValueError(f"{code}: user_mode/reporting_start_date are immutable")
                action = "unchanged" if old[1:] == (row["name"], row["active"]) else "update"
            else:
                action = "create"
            plan.append(dict(code=code, action=action))
        configured = {r["code"] for r in rows}
        plan.extend(dict(code=p["code"], action="retained") for p in registry.values()
                    if p["code"] not in configured)
        if dry_run:
            return plan
        for row, entry in zip(rows, plan):
            if entry["action"] == "unchanged":
                continue
            fingerprint = hashlib.sha256(json.dumps(row, sort_keys=True, default=str).encode()).hexdigest()
            if entry["action"] == "update":
                aid = existing[row["code"]][0]
                cur.execute("UPDATE dim_agent SET name=%s,is_running=%s WHERE agent_id=%s",
                            (row["name"], row["active"], aid))
                cur.execute("UPDATE gateway_agent_registry SET config_hash=%s,applied_at=now() WHERE agent_id=%s",
                            (fingerprint, aid))
                continue
            aid = _allocate(cur, "dim_agent", "agent_id", "gateway_agent_id_seq")
            cur.execute("INSERT INTO dim_agent(agent_id,code,name,gcp_project_id,has_org_tree,"
                        "project_created_at,data_from,data_to,is_running,has_google_source) "
                        "VALUES (%s,%s,%s,NULL,false,NULL,%s,NULL,%s,false)",
                        (aid, row["code"], row["name"], row["reporting_start_date"], row["active"]))
            unit = f"__gateway_{aid}__"
            label = f"Gateway: {row['name']} (department unknown)"
            cur.execute("INSERT INTO dim_unit(unit_id,agent_id,name,parent_id,level,path,is_technical) "
                        "VALUES (%s,%s,%s,NULL,0,%s,true)", (unit, aid, label, label))
            single = row["user_mode"] == "single"
            insert_account(cur, aid, f"svc.{row['code']}" if single else f"__whole_agent_{aid}__",
                           "service_account" if single else "whole_agent", unit)
            insert_account(cur, aid, f"__unattributed_{aid}__", "unattributed", unit)
            cur.execute("INSERT INTO gateway_agent_registry(agent_id,user_mode,reporting_start_date,"
                        "config_version,config_hash) VALUES (%s,%s,%s,1,%s)",
                        (aid, row["user_mode"], row["reporting_start_date"], fingerprint))
    return plan


def valid_identity(value):
    return (isinstance(value, str) and bool(value.strip())
            and not any(unicodedata.category(c) in ("Cc", "Cs") for c in value)
            and len(value.encode("utf-8")) <= 256)


def in_scope(policy, timestamp):
    return (timestamp + timedelta(hours=7)).date() >= policy["start"]


def discover(cn, agent_id, identity, timestamp, dry_run=False):
    with cn.cursor() as cur:
        cur.execute("SELECT account_id FROM gateway_observed_identity WHERE agent_id=%s AND external_user_id=%s",
                    (agent_id, identity))
        old = cur.fetchone()
        if dry_run:
            return old[0] if old else None
        if old:
            cur.execute("UPDATE gateway_observed_identity SET first_seen=LEAST(first_seen,%s),"
                        "last_seen=GREATEST(last_seen,%s) WHERE agent_id=%s AND external_user_id=%s",
                        (timestamp, timestamp, agent_id, identity))
            return old[0]
        username = f"gw:{agent_id}:{identity.encode('utf-8').hex()}"
        cur.execute("SELECT account_id FROM account WHERE username=%s", (username,))
        if cur.fetchone():
            raise ValueError("Gateway identity namespace collision; refusing to reuse a legacy account")
        aid = insert_account(cur, agent_id, username, "gateway_observed", f"__gateway_{agent_id}__")
        cur.execute("INSERT INTO gateway_observed_identity(agent_id,external_user_id,account_id,first_seen,last_seen) "
                    "VALUES (%s,%s,%s,%s,%s)", (agent_id, identity, aid, timestamp, timestamp))
        return aid
