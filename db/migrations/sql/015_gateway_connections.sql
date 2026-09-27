CREATE TABLE gateway_connection_profile (
    code text PRIMARY KEY,
    revision bigint NOT NULL CHECK(revision > 0),
    applied_revision bigint,
    draft jsonb NOT NULL,
    applied jsonb,
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE gateway_connection_operation (
    id uuid PRIMARY KEY,
    code text NOT NULL REFERENCES gateway_connection_profile(code),
    kind text NOT NULL CHECK(kind IN ('apply','issue','revoke','verify','recover','budget')),
    idempotency_key text NOT NULL UNIQUE,
    request_hash text NOT NULL,
    expected_revision bigint NOT NULL,
    actor text NOT NULL,
    status text NOT NULL DEFAULT 'queued',
    stage text NOT NULL DEFAULT 'queued',
    payload jsonb NOT NULL DEFAULT '{}',
    result jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE gateway_connection_audit (
    id bigserial PRIMARY KEY,
    operation_id uuid,
    code text NOT NULL,
    actor text NOT NULL,
    action text NOT NULL,
    detail jsonb NOT NULL DEFAULT '{}',
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE gateway_connection_key (
    key_alias text PRIMARY KEY,
    code text NOT NULL REFERENCES gateway_connection_profile(code),
    operation_id uuid NOT NULL UNIQUE REFERENCES gateway_connection_operation(id),
    status text NOT NULL,
    budget jsonb NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE gateway_connection_deployment (
    singleton boolean PRIMARY KEY DEFAULT true CHECK(singleton),
    baseline jsonb NOT NULL DEFAULT '{}',
    recovery_operation uuid REFERENCES gateway_connection_operation(id)
);
INSERT INTO gateway_connection_deployment(singleton) VALUES(true);
-- Provision login/password out of band. Do not grant ledger mutation to the API.
DO $$ BEGIN
    IF NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='connection_admin') THEN
        CREATE ROLE connection_admin NOLOGIN;
    END IF;
END $$;
GRANT SELECT,INSERT,UPDATE ON gateway_connection_profile,gateway_connection_operation,
    gateway_connection_audit,gateway_connection_key,gateway_connection_deployment TO connection_admin;
GRANT USAGE,SELECT ON SEQUENCE gateway_connection_audit_id_seq TO connection_admin;
GRANT SELECT ON dim_agent,gateway_agent_registry,ref_model_catalog TO connection_admin;
