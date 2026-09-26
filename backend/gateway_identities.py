"""Read-only, agent-scoped observed identities. Never a provisioned staff directory."""
from .store import _rows


def registered(cn):
    return _rows(cn, "SELECT to_regclass('public.gateway_agent_registry') IS NOT NULL AS ready")[0]["ready"]


def identities(cn, start, end, agent_id=None, limit=100, offset=0):
    empty = dict(rows=[], total=0, calls=0, total_tokens=0, agents=[], limit=limit, offset=offset)
    if not registered(cn):
        return empty
    agents = _rows(cn, "SELECT g.agent_id,g.code,g.name,g.is_running,r.user_mode "
                   "FROM gateway_agent_registry r JOIN dim_agent g USING(agent_id) "
                   "WHERE (%s::integer IS NULL OR g.agent_id=%s) ORDER BY g.agent_id",
                   (agent_id, agent_id))
    # Resolved view preserves the independent source choice for calls and tokens.
    rows = _rows(cn, """
        WITH usage AS (
            SELECT agent_id,account_id,SUM(calls) AS calls,SUM(total_tokens) AS total_tokens
            FROM usage_by_account_resolved WHERE day BETWEEN %s AND %s
            GROUP BY agent_id,account_id
        ), seen AS (
            SELECT agent_id,account_id,MIN(ts_raw) AS first_seen,MAX(ts_raw) AS last_seen
            FROM fact_call WHERE source='gateway' AND ts_local::date BETWEEN %s AND %s
            GROUP BY agent_id,account_id
        )
        SELECT a.account_id,g.agent_id,g.name AS agent,g.code,a.kind,
               CASE WHEN a.kind='gateway_observed' THEN i.external_user_id
                    WHEN a.kind='service_account' THEN a.username
                    ELSE NULL END AS external_user_id,
               'gateway' AS identity_source,
               s.first_seen,s.last_seen,
               COALESCE(u.calls,0) AS calls,COALESCE(u.total_tokens,0) AS total_tokens
        FROM gateway_agent_registry r JOIN dim_agent g USING(agent_id)
        JOIN account a ON a.unit_agent_id=g.agent_id
        LEFT JOIN gateway_observed_identity i ON i.account_id=a.account_id AND i.agent_id=g.agent_id
        LEFT JOIN usage u ON u.agent_id=g.agent_id AND u.account_id=a.account_id
        LEFT JOIN seen s ON s.agent_id=g.agent_id AND s.account_id=a.account_id
        WHERE (%s::integer IS NULL OR g.agent_id=%s)
          AND (s.account_id IS NOT NULL OR u.account_id IS NOT NULL
               OR a.kind IN ('service_account','whole_agent'))
        ORDER BY g.agent_id,a.account_id
    """, (start, end, start, end, agent_id, agent_id))
    result = dict(total=len(rows), calls=sum(int(r["calls"]) for r in rows),
                  total_tokens=sum(int(r["total_tokens"]) for r in rows), agents=agents,
                  limit=limit, offset=offset)
    result["rows"] = rows[offset:offset + limit]
    return result
