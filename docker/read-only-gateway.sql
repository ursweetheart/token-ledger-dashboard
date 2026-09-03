-- Read-only role for reading the Gateway ledger (database `litellm`).
-- Idempotent. Needs three psql variables:
--   psql -v gw_role=gateway_readonly -v gw_password='...' -v gw_db=litellm \
--        -f docker/read-only-gateway.sql
--
-- WHY NOT REUSE docker/read-only-api.sql
-- -------------------------------------
-- That script REVOKEs privileges from PUBLIC across the schema and every table.
-- Running it against `litellm` would touch a database that LiteLLM migrates with
-- Prisma on every version bump. This script only GRANTs -- it never revokes -- so
-- a running Gateway cannot be affected by it.
--
-- ONE TABLE ONLY
-- --------------
-- `LiteLLM_SpendLogs` and nothing else. In particular NOT
-- `LiteLLM_VerificationToken`, which holds the SHA-256 hashes of the virtual keys.
-- The loader has no business reading those.

\set ON_ERROR_STOP on

BEGIN;

SELECT format('CREATE ROLE %I', :'gw_role')
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_catalog.pg_roles
    WHERE rolname = :'gw_role'
)
\gexec

ALTER ROLE :"gw_role" WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOCREATEROLE
    NOREPLICATION
    NOBYPASSRLS
    PASSWORD :'gw_password';

-- Belt and braces: even a query that tries to write is refused by the server,
-- not merely by convention in the loader.
ALTER ROLE :"gw_role" SET default_transaction_read_only TO on;

GRANT CONNECT ON DATABASE :"gw_db" TO :"gw_role";
GRANT USAGE ON SCHEMA public TO :"gw_role";
GRANT SELECT ON TABLE public."LiteLLM_SpendLogs" TO :"gw_role";

COMMIT;
