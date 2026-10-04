-- Slothdev GrowthOS: Postgres / Supabase schema.
-- Run it yourself in Supabase (the app never executes DDL). Tables are split by owner:
-- data_engine (backend-1) and decision_engine (backend-2) never write each other's tables.

-- ============================== data_engine (backend-1) ==============================

CREATE TABLE IF NOT EXISTS business (
    business_id   TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    category      TEXT,
    city          TEXT,
    currency      TEXT NOT NULL DEFAULT 'INR',
    timezone      TEXT NOT NULL DEFAULT 'Asia/Kolkata',
    constraints   JSONB NOT NULL DEFAULT '{}'::jsonb,   -- budget, forbidden actions, SLA
    capacity      JSONB NOT NULL DEFAULT '{}'::jsonb,   -- weekly minutes, owners
    synthetic     BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS goal (
    goal_id       TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    statement     TEXT NOT NULL,
    primary_kpi   TEXT NOT NULL,
    horizon_days  INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS product (
    sku           TEXT NOT NULL,
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    name          TEXT NOT NULL,
    price         NUMERIC(12,2) NOT NULL,
    unit_cost     NUMERIC(12,2),
    PRIMARY KEY (business_id, sku)
);

CREATE TABLE IF NOT EXISTS campaign (
    campaign_id   TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    channel       TEXT NOT NULL,
    name          TEXT,
    started_on    DATE,
    ended_on      DATE
);

CREATE TABLE IF NOT EXISTS lead (
    lead_id       TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    campaign_id   TEXT REFERENCES campaign(campaign_id),
    channel       TEXT,
    created_at    TIMESTAMPTZ NOT NULL,
    first_response_at TIMESTAMPTZ,
    stage         TEXT NOT NULL DEFAULT 'new',          -- new | qualified | won | lost
    expected_value NUMERIC(12,2),
    attributes    JSONB NOT NULL DEFAULT '{}'::jsonb,
    synthetic     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS customer (
    customer_id   TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    first_order_at TIMESTAMPTZ,
    acquisition_channel TEXT,
    email_opt_in  BOOLEAN NOT NULL DEFAULT FALSE,
    synthetic     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id      TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    customer_id   TEXT REFERENCES customer(customer_id),
    campaign_id   TEXT REFERENCES campaign(campaign_id), -- NULL = unattributed
    ordered_at    TIMESTAMPTZ NOT NULL,
    revenue       NUMERIC(12,2) NOT NULL,
    shipping_cost NUMERIC(12,2),
    synthetic     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS order_item (
    order_id      TEXT NOT NULL REFERENCES orders(order_id),
    business_id   TEXT NOT NULL,
    sku           TEXT NOT NULL,
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(12,2) NOT NULL,
    PRIMARY KEY (order_id, sku)
);

CREATE TABLE IF NOT EXISTS import_job (
    import_id     TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    kind          TEXT NOT NULL,                        -- campaigns | leads | orders
    status        TEXT NOT NULL,                        -- uploaded | confirmed | loaded | failed
    mapping       JSONB,
    report        JSONB,                                -- data_quality.json import shape
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS quarantine_row (
    id            BIGSERIAL PRIMARY KEY,
    import_id     TEXT NOT NULL REFERENCES import_job(import_id),
    row_number    INTEGER NOT NULL,
    reason        TEXT NOT NULL,
    raw           JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS kpi_snapshot (
    business_id   TEXT NOT NULL REFERENCES business(business_id),
    fact_id       TEXT NOT NULL,
    snapshot      TEXT NOT NULL DEFAULT 'baseline',     -- baseline | day7
    period_from   DATE NOT NULL,
    period_to     DATE NOT NULL,
    fact          JSONB NOT NULL,                       -- KPI fact shape (contract 2.1)
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (business_id, fact_id, snapshot, period_from)
);

CREATE TABLE IF NOT EXISTS lead_score (
    lead_id       TEXT NOT NULL REFERENCES lead(lead_id),
    business_id   TEXT NOT NULL,
    model_id      TEXT NOT NULL,
    score         JSONB NOT NULL,                       -- lead score shape (contract 2.2)
    scored_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (lead_id, model_id)
);

-- ============================ decision_engine (backend-2) ============================
-- Documents are stored as JSONB in their contract shape; key columns are pulled out
-- for lookups.

CREATE TABLE IF NOT EXISTS context_snapshot (
    id            BIGSERIAL PRIMARY KEY,
    business_id   TEXT NOT NULL,
    taken_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    context       JSONB NOT NULL                        -- context + facts used for a run
);

CREATE TABLE IF NOT EXISTS intervention_template (
    template_id   TEXT PRIMARY KEY,
    version       TEXT NOT NULL,
    template      JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS signal (
    signal_id     TEXT NOT NULL,
    business_id   TEXT NOT NULL,
    type          TEXT NOT NULL CHECK (type IN ('bottleneck', 'opportunity', 'anomaly')),
    signal        JSONB NOT NULL,
    detected_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (business_id, signal_id)
);

CREATE TABLE IF NOT EXISTS recommendation (
    recommendation_id TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('proposed', 'approved', 'rejected', 'blocked')),
    priority      NUMERIC(5,1),
    recommendation JSONB NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS plan (
    plan_id       TEXT PRIMARY KEY,
    business_id   TEXT NOT NULL,
    week_from     DATE NOT NULL,
    week_to       DATE NOT NULL,
    plan          JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS task (
    task_id       TEXT PRIMARY KEY,
    plan_id       TEXT NOT NULL REFERENCES plan(plan_id),
    recommendation_id TEXT REFERENCES recommendation(recommendation_id),
    status        TEXT NOT NULL CHECK (status IN ('todo', 'doing', 'done')),
    task          JSONB NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS outcome (
    plan_id       TEXT NOT NULL REFERENCES plan(plan_id),
    recommendation_id TEXT NOT NULL REFERENCES recommendation(recommendation_id),
    effectiveness TEXT CHECK (effectiveness IN ('promising', 'inconclusive', 'not_effective')),
    outcome       JSONB NOT NULL,
    evaluated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (plan_id, recommendation_id)
);
