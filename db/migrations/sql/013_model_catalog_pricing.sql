-- Additive only. No facts, quotas, routes or legacy prices are changed.
CREATE TABLE ref_model_catalog (
    catalog_key TEXT PRIMARY KEY,
    local_model_id INT UNIQUE REFERENCES dim_model(model_id),
    openrouter_id TEXT UNIQUE,
    provider TEXT NOT NULL,
    display_name TEXT NOT NULL,
    available BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ,
    price_last_verified_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    revision BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE ref_model_price_version (
    id BIGSERIAL PRIMARY KEY,
    catalog_key TEXT NOT NULL REFERENCES ref_model_catalog(catalog_key),
    source TEXT NOT NULL CHECK(source IN ('openrouter','manual')),
    mode TEXT NOT NULL CHECK(mode IN ('price','auto')),
    valid_from DATE NOT NULL,
    valid_to DATE CHECK(valid_to > valid_from),
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    pricing JSONB NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('valid','missing','unsupported')),
    principal TEXT NOT NULL,
    reason TEXT NOT NULL,
    CHECK(source='manual' OR mode='price')
);
CREATE INDEX model_price_day ON ref_model_price_version(catalog_key,valid_from,id);
CREATE TABLE ref_price_sync_state (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton),
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    interval_hours INT NOT NULL DEFAULT 24 CHECK(interval_hours BETWEEN 1 AND 168),
    last_attempt TIMESTAMPTZ,
    last_success TIMESTAMPTZ,
    last_worker_seen TIMESTAMPTZ,
    next_due TIMESTAMPTZ,
    requested BOOLEAN NOT NULL DEFAULT FALSE,
    lease_token TEXT,
    lease_until TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'disabled',
    last_error_class TEXT,
    generation BIGINT NOT NULL DEFAULT 0,
    revision BIGINT NOT NULL DEFAULT 0,
    principal TEXT
);
INSERT INTO ref_price_sync_state(singleton) VALUES(TRUE);
INSERT INTO ref_model_catalog(catalog_key,local_model_id,provider,display_name)
SELECT 'local:' || model_id,model_id,COALESCE(provider,'unknown'),name FROM dim_model;

-- Keep incremental ingestion visible without waiting for an external sync.
-- Invoker privileges: model-ingest roles need INSERT on the pricing catalog.
CREATE FUNCTION register_local_pricing_model() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO ref_model_catalog(catalog_key,local_model_id,provider,display_name)
    VALUES ('local:' || NEW.model_id,NEW.model_id,COALESCE(NEW.provider,'unknown'),NEW.name)
    ON CONFLICT DO NOTHING;
    RETURN NEW;
END;
$$;
CREATE TRIGGER register_local_pricing_model AFTER INSERT ON dim_model
FOR EACH ROW EXECUTE FUNCTION register_local_pricing_model();
