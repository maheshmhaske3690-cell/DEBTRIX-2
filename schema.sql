-- ============================================================
-- DEBTRIX MVP — PostgreSQL Schema
-- Design principle: ZERO RETENTION of raw source code.
-- We only ever store extracted METRICS, never file contents.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ------------------------------------------------------------
-- 1. COMPANIES (tenant boundary — everything is scoped to this)
-- ------------------------------------------------------------
CREATE TABLE companies (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    slug                VARCHAR(100) UNIQUE NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 2. USERS (people who log in — engineering managers, execs)
-- ------------------------------------------------------------
CREATE TABLE users (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    email               VARCHAR(255) UNIQUE NOT NULL,
    full_name           VARCHAR(255),
    role                VARCHAR(50) NOT NULL DEFAULT 'engineering_manager',
        -- 'admin' | 'engineering_manager' | 'executive'
    hashed_password     VARCHAR(255),          -- null if OAuth-only login
    github_access_token TEXT,                  -- encrypted at rest (see notes below)
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at       TIMESTAMPTZ
);

-- ------------------------------------------------------------
-- 3. FINANCIAL CONFIG (per-company assumptions for $ calculations)
--    This is what makes the Financial Loss Algorithm configurable
--    instead of a fixed guess.
-- ------------------------------------------------------------
CREATE TABLE financial_config (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id              UUID NOT NULL UNIQUE REFERENCES companies(id) ON DELETE CASCADE,
    avg_developer_hourly_rate  NUMERIC(10,2) NOT NULL DEFAULT 50.00,
    currency                VARCHAR(3) NOT NULL DEFAULT 'USD',
    working_hours_per_month NUMERIC(6,2) NOT NULL DEFAULT 160.00,
    risk_multiplier         NUMERIC(4,2) NOT NULL DEFAULT 1.00,
        -- lets a company weight "risk of breakage" heavier than raw time
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 4. REPOSITORIES (connected GitHub/GitLab repos)
-- ------------------------------------------------------------
CREATE TABLE repositories (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    provider            VARCHAR(20) NOT NULL DEFAULT 'github', -- 'github' | 'gitlab'
    external_repo_id    VARCHAR(100) NOT NULL,   -- provider's repo id
    full_name           VARCHAR(255) NOT NULL,   -- e.g. "org/repo"
    default_branch      VARCHAR(100) NOT NULL DEFAULT 'main',
    is_active           BOOLEAN NOT NULL DEFAULT true,
    connected_by_user_id UUID REFERENCES users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (company_id, provider, external_repo_id)
);

-- ------------------------------------------------------------
-- 5. SCAN JOBS (one row per scan run — tracks lifecycle of the
--    ephemeral clone → analyze → purge pipeline)
-- ------------------------------------------------------------
CREATE TABLE scan_jobs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    repository_id       UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    status               VARCHAR(20) NOT NULL DEFAULT 'queued',
        -- 'queued' | 'cloning' | 'analyzing' | 'completed' | 'failed' | 'purged'
    commit_sha           VARCHAR(40),
    triggered_by_user_id UUID REFERENCES users(id),
    started_at           TIMESTAMPTZ,
    completed_at         TIMESTAMPTZ,
    source_purged_at     TIMESTAMPTZ,   -- proof of zero-retention: when local clone was deleted
    error_message         TEXT,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 6. CODE METRICS (extracted per-file metrics — NEVER raw code)
-- ------------------------------------------------------------
CREATE TABLE code_metrics (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_job_id         UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    file_path            VARCHAR(1000) NOT NULL,
    language              VARCHAR(50),
    cyclomatic_complexity NUMERIC(10,2),
    maintainability_index NUMERIC(10,2),
    lines_of_code         INTEGER,
    churn_last_90_days     INTEGER DEFAULT 0,   -- commit count touching this file
    unique_authors_90_days INTEGER DEFAULT 0,
    last_modified_at       TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_code_metrics_scan_job ON code_metrics(scan_job_id);

-- ------------------------------------------------------------
-- 7. FINANCIAL LOSS RESULTS (computed $ + health score per scan)
-- ------------------------------------------------------------
CREATE TABLE financial_loss_results (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_job_id              UUID NOT NULL UNIQUE REFERENCES scan_jobs(id) ON DELETE CASCADE,
    overall_health_score      NUMERIC(5,2) NOT NULL,  -- 0-100
    monthly_financial_loss    NUMERIC(14,2) NOT NULL,
    currency                   VARCHAR(3) NOT NULL DEFAULT 'USD',
    estimated_dev_hours_wasted_monthly NUMERIC(10,2),
    time_to_market_delay_days  NUMERIC(6,2),
    computed_at                 TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------
-- 8. TOP PRIORITY FIXES (the "Top 3" noise-filtered list)
-- ------------------------------------------------------------
CREATE TABLE priority_fixes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_job_id          UUID NOT NULL REFERENCES scan_jobs(id) ON DELETE CASCADE,
    file_path             VARCHAR(1000) NOT NULL,
    rank                   SMALLINT NOT NULL,  -- 1, 2, 3
    estimated_monthly_loss NUMERIC(14,2) NOT NULL,
    reason_summary          TEXT NOT NULL,      -- human-readable "why this matters"
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_priority_fixes_scan_job ON priority_fixes(scan_job_id);

-- ============================================================
-- NOTES:
-- 1. github_access_token must be encrypted at the application
--    layer (e.g. AES-256 via a KMS-backed key) before insert —
--    never store plaintext tokens even in a private DB.
-- 2. Zero-retention enforcement: the worker MUST set
--    source_purged_at immediately after code_metrics rows are
--    written, and the local clone directory must be deleted in
--    the same transaction/step — this is an app-layer guarantee,
--    the schema just gives you an audit trail for it.
-- 3. financial_loss_results and priority_fixes are recomputed
--    every scan — treat them as derived/append-only, not edited.
-- ============================================================
