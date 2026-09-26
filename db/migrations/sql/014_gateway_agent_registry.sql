CREATE SEQUENCE gateway_agent_id_seq AS integer;
SELECT setval('gateway_agent_id_seq', COALESCE(MAX(agent_id),0)+1, false) FROM dim_agent;
CREATE SEQUENCE gateway_account_id_seq AS integer;
SELECT setval('gateway_account_id_seq', COALESCE(MAX(account_id),0)+1, false) FROM account;

CREATE TABLE gateway_agent_registry (
    agent_id integer PRIMARY KEY REFERENCES dim_agent(agent_id),
    user_mode text NOT NULL CHECK (user_mode IN ('single','multiple')),
    reporting_start_date date NOT NULL,
    config_version integer NOT NULL CHECK (config_version=1),
    config_hash text NOT NULL,
    applied_at timestamptz NOT NULL DEFAULT now(),
    pending_backfill boolean NOT NULL DEFAULT true
);
CREATE TABLE gateway_observed_identity (
    agent_id integer NOT NULL REFERENCES gateway_agent_registry(agent_id),
    external_user_id text COLLATE "C" NOT NULL
        CHECK (octet_length(external_user_id) BETWEEN 1 AND 256),
    account_id integer NOT NULL UNIQUE REFERENCES account(account_id),
    first_seen timestamp NOT NULL,
    last_seen timestamp NOT NULL CHECK (last_seen >= first_seen),
    PRIMARY KEY (agent_id, external_user_id)
);
CREATE INDEX gateway_identity_seen ON gateway_observed_identity(agent_id,last_seen);

DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='api_readonly') THEN
        GRANT SELECT ON gateway_agent_registry, gateway_observed_identity TO api_readonly;
    END IF;
END $$;
