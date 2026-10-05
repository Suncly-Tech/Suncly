-- =============================================================================
-- Suncly - the hosted application layer (SCHEMA.md §12)
-- Migration: 0003_application_layer.sql
-- Target:    PostgreSQL 13+ (Cloud SQL, plain Postgres)
--
-- The seven entities of SCHEMA.md §3 stay exactly as 0001 created them, in the
-- public schema. Everything the hosted product needs around them lives in the
-- schema suncly_app: tenants and memberships, agent registrations, the durable
-- job queue (schema §7), the transactional outbox, the usage ledger, billing,
-- policy versions, decision notes, the trusted signing-key registry and the
-- re-evaluation schedule.
--
-- Rules carried over from the core:
--   * evidence-like records (usage_event, decision_note, signing-key history,
--     provider_event) are append-only; corrections are new records;
--   * nothing deletes a core record as a side effect (NO ACTION foreign keys);
--   * money is integer minor units, never floating point.
-- =============================================================================

BEGIN;

-- Applied after 0002 (row level security on the core tables). Recognised in the catalog
-- by the presence of its tables (adapters/postgres/migrate.py); no bookkeeping table.
CREATE SCHEMA IF NOT EXISTS suncly_app;

-- -----------------------------------------------------------------------------
-- Tenancy
-- -----------------------------------------------------------------------------

CREATE TYPE suncly_app.member_role AS ENUM ('administrator', 'reviewer', 'viewer');

CREATE TABLE suncly_app.organization (
    id                   uuid        PRIMARY KEY,
    slug                 text        NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9][a-z0-9-]*$'),
    name                 text        NOT NULL CHECK (length(trim(name)) > 0),
    created_at           timestamptz NOT NULL DEFAULT now(),
    max_concurrent_jobs  integer     NOT NULL DEFAULT 2 CHECK (max_concurrent_jobs BETWEEN 1 AND 64)
);

CREATE TABLE suncly_app.membership (
    id               uuid                   PRIMARY KEY,
    organization_id  uuid                   NOT NULL REFERENCES suncly_app.organization (id),
    subject          text                   NOT NULL CHECK (length(subject) > 0),
    email            text,
    role             suncly_app.member_role NOT NULL,
    created_at       timestamptz            NOT NULL DEFAULT now(),
    CONSTRAINT membership_one_per_subject UNIQUE (organization_id, subject)
);

CREATE TYPE suncly_app.deployment_mode AS ENUM ('public', 'private_network', 'local');

CREATE TABLE suncly_app.agent_registration (
    id                         uuid                        PRIMARY KEY,
    organization_id            uuid                        NOT NULL REFERENCES suncly_app.organization (id),
    agent_id                   uuid                        NOT NULL UNIQUE REFERENCES public.agent (id),
    name                       text                        NOT NULL CHECK (length(trim(name)) > 0),
    card_url                   text                        NOT NULL CHECK (length(card_url) > 0),
    risk_level                 public.risk_level           NOT NULL,
    owner                      text                        NOT NULL,
    sandbox_declared           boolean                     NOT NULL,
    sandbox_idempotent         boolean                     NOT NULL DEFAULT false,
    credential_provider        text                        NOT NULL CHECK (credential_provider IN ('secret-manager', 'env', 'none')),
    credential_ref             text                        NOT NULL DEFAULT '',
    deployment_mode            suncly_app.deployment_mode  NOT NULL DEFAULT 'public',
    bring_your_own_model_key   boolean                     NOT NULL DEFAULT false,
    created_at                 timestamptz                 NOT NULL DEFAULT now(),
    created_by                 text                        NOT NULL,
    archived_at                timestamptz
);
CREATE INDEX agent_registration_org_idx ON suncly_app.agent_registration (organization_id);

-- The application layer's view of one attestation: who owns it, what versions
-- judged it, and the issue/expiry window the signature binds (SCHEMA.md §12).
CREATE TABLE suncly_app.attestation_meta (
    attestation_id        uuid        PRIMARY KEY REFERENCES public.attestation (id),
    organization_id       uuid        NOT NULL REFERENCES suncly_app.organization (id),
    registration_id       uuid        NOT NULL REFERENCES suncly_app.agent_registration (id),
    created_by            text        NOT NULL,
    runs_planned          integer     NOT NULL CHECK (runs_planned >= 0),
    runs_per_test_case    integer     NOT NULL CHECK (runs_per_test_case >= 1),
    suite_version         text        NOT NULL,
    contract_content_hash text        NOT NULL,
    judge_version         text        NOT NULL,
    rubric_versions       jsonb       NOT NULL DEFAULT '{}'::jsonb,
    policy_version        text,
    policy_content_hash   text,
    environment           jsonb       NOT NULL DEFAULT '{}'::jsonb,
    deployment_identity   jsonb,
    issued_at             timestamptz,
    expires_at            timestamptz,
    payload_version       integer,
    decided_by_reviewer   text,
    CONSTRAINT attestation_meta_issue_window CHECK (expires_at IS NULL OR issued_at IS NULL OR expires_at > issued_at)
);
CREATE INDEX attestation_meta_org_idx ON suncly_app.attestation_meta (organization_id, registration_id);

-- -----------------------------------------------------------------------------
-- Policy versions and decision notes (append-only)
-- -----------------------------------------------------------------------------

CREATE TABLE suncly_app.policy_record (
    id               uuid        PRIMARY KEY,
    organization_id  uuid        NOT NULL REFERENCES suncly_app.organization (id),
    policy_version   text        NOT NULL,
    content_hash     text        NOT NULL,
    configuration    jsonb       NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    created_by       text        NOT NULL,
    CONSTRAINT policy_version_unique UNIQUE (organization_id, policy_version)
);

CREATE TABLE suncly_app.decision_note (
    decision_id      uuid        PRIMARY KEY REFERENCES public.decision (id),
    organization_id  uuid        NOT NULL REFERENCES suncly_app.organization (id),
    attestation_id   uuid        NOT NULL REFERENCES public.attestation (id),
    reviewer_subject text        NOT NULL,
    rationale        text        NOT NULL CHECK (length(trim(rationale)) > 0),
    created_at       timestamptz NOT NULL DEFAULT now()
);

-- -----------------------------------------------------------------------------
-- Jobs, attempts and the outbox (SCHEMA.md §7: a Postgres-backed job table)
-- -----------------------------------------------------------------------------

CREATE TYPE suncly_app.job_kind   AS ENUM ('attestation', 'reevaluation', 'outbox_relay');
CREATE TYPE suncly_app.job_status AS ENUM ('queued', 'running', 'succeeded', 'failed', 'cancelled');
CREATE TYPE suncly_app.attempt_outcome AS ENUM ('running', 'succeeded', 'failed', 'lost', 'cancelled');

CREATE TABLE suncly_app.job (
    id                uuid                   PRIMARY KEY,
    organization_id   uuid                   NOT NULL REFERENCES suncly_app.organization (id),
    kind              suncly_app.job_kind    NOT NULL,
    logical_id        uuid                   NOT NULL,
    payload           jsonb                  NOT NULL DEFAULT '{}'::jsonb,
    status            suncly_app.job_status  NOT NULL DEFAULT 'queued',
    created_at        timestamptz            NOT NULL DEFAULT now(),
    run_after         timestamptz            NOT NULL DEFAULT now(),
    attempts          integer                NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    max_attempts      integer                NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 20),
    lease_owner       text,
    lease_expires_at  timestamptz,
    cancel_requested  boolean                NOT NULL DEFAULT false,
    progress          jsonb                  NOT NULL DEFAULT '{}'::jsonb,
    last_error        text,
    finished_at       timestamptz,
    CONSTRAINT job_one_per_logical UNIQUE (kind, logical_id),
    CONSTRAINT job_lease_fields_together CHECK ((lease_owner IS NULL) = (lease_expires_at IS NULL))
);
CREATE INDEX job_claimable_idx ON suncly_app.job (status, run_after) WHERE status = 'queued';
CREATE INDEX job_running_org_idx ON suncly_app.job (organization_id) WHERE status = 'running';

CREATE TABLE suncly_app.job_attempt (
    id                 uuid                        PRIMARY KEY,
    job_id             uuid                        NOT NULL REFERENCES suncly_app.job (id),
    number             integer                     NOT NULL CHECK (number >= 1),
    worker_id          text                        NOT NULL,
    started_at         timestamptz                 NOT NULL DEFAULT now(),
    last_heartbeat_at  timestamptz                 NOT NULL DEFAULT now(),
    finished_at        timestamptz,
    outcome            suncly_app.attempt_outcome  NOT NULL DEFAULT 'running',
    error              text,
    CONSTRAINT job_attempt_number_unique UNIQUE (job_id, number)
);

CREATE TABLE suncly_app.outbox (
    id               uuid        PRIMARY KEY,
    organization_id  uuid        NOT NULL REFERENCES suncly_app.organization (id),
    topic            text        NOT NULL,
    dedup_key        text        NOT NULL UNIQUE,
    payload          jsonb       NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    delivered_at     timestamptz,
    attempts         integer     NOT NULL DEFAULT 0,
    last_error       text
);
CREATE INDEX outbox_pending_idx ON suncly_app.outbox (created_at) WHERE delivered_at IS NULL;

-- -----------------------------------------------------------------------------
-- Usage ledger (append-only), reservations, limits
-- -----------------------------------------------------------------------------

CREATE TYPE suncly_app.usage_operation  AS ENUM ('agent_call', 'draft', 'judge', 'probe', 'external_tool', 'adjustment');
CREATE TYPE suncly_app.usage_outcome    AS ENUM ('settled', 'unknown', 'failed');
CREATE TYPE suncly_app.settlement_state AS ENUM ('pending', 'reported', 'not_billable');
CREATE TYPE suncly_app.reservation_state AS ENUM ('held', 'settled', 'released');

CREATE TABLE suncly_app.reservation (
    id               uuid                          PRIMARY KEY,
    organization_id  uuid                          NOT NULL REFERENCES suncly_app.organization (id),
    attestation_id   uuid                          REFERENCES public.attestation (id),
    amount_minor     bigint                        NOT NULL CHECK (amount_minor >= 0),
    currency         text                          NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    state            suncly_app.reservation_state  NOT NULL DEFAULT 'held',
    created_at       timestamptz                   NOT NULL DEFAULT now(),
    settled_minor    bigint                        NOT NULL DEFAULT 0 CHECK (settled_minor >= 0),
    closed_at        timestamptz,
    note             text                          NOT NULL DEFAULT ''
);
CREATE INDEX reservation_org_state_idx ON suncly_app.reservation (organization_id, state);

CREATE TABLE suncly_app.usage_event (
    id                    uuid                         PRIMARY KEY,
    organization_id       uuid                         NOT NULL REFERENCES suncly_app.organization (id),
    attestation_id        uuid                         REFERENCES public.attestation (id),
    logical_run_id        uuid,
    execution_attempt_id  uuid                         REFERENCES suncly_app.job_attempt (id),
    reservation_id        uuid                         REFERENCES suncly_app.reservation (id),
    provider              text                         NOT NULL,
    provider_request_id   text,
    model                 text,
    operation             suncly_app.usage_operation   NOT NULL,
    outcome               suncly_app.usage_outcome     NOT NULL,
    measured              jsonb                        NOT NULL DEFAULT '{}'::jsonb,
    currency              text                         NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
    provider_cost_minor   bigint,
    price_table_version   text                         NOT NULL,
    billable_minor        bigint                       NOT NULL CHECK (billable_minor >= 0),
    allowance_minor       bigint                       NOT NULL CHECK (allowance_minor >= 0 AND allowance_minor <= billable_minor),
    settlement            suncly_app.settlement_state  NOT NULL,
    recorded_at           timestamptz                  NOT NULL DEFAULT now(),
    note                  text                         NOT NULL DEFAULT '',
    CONSTRAINT usage_unknown_has_no_cost CHECK (outcome <> 'unknown' OR provider_cost_minor IS NULL)
);
CREATE INDEX usage_event_org_time_idx ON suncly_app.usage_event (organization_id, recorded_at);

-- One ledger line per recorded run and operation: a resumed execution that bills a run
-- the dead attempt already billed is refused by the database, not only by the worker.
CREATE UNIQUE INDEX usage_event_one_line_per_run
    ON suncly_app.usage_event (logical_run_id, operation)
    WHERE logical_run_id IS NOT NULL AND operation = 'agent_call';
CREATE UNIQUE INDEX usage_event_provider_request_idx
    ON suncly_app.usage_event (provider, provider_request_id) WHERE provider_request_id IS NOT NULL;

CREATE TABLE suncly_app.spending_limit (
    id                  uuid        PRIMARY KEY,
    organization_id     uuid        NOT NULL REFERENCES suncly_app.organization (id),
    currency            text        NOT NULL,
    period_limit_minor  bigint      NOT NULL CHECK (period_limit_minor >= 0),
    set_by              text        NOT NULL,
    set_at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX spending_limit_org_idx ON suncly_app.spending_limit (organization_id, set_at DESC);

-- -----------------------------------------------------------------------------
-- Billing
-- -----------------------------------------------------------------------------

CREATE TYPE suncly_app.subscription_status AS ENUM ('none', 'trialing', 'active', 'past_due', 'canceled', 'unpaid');

CREATE TABLE suncly_app.subscription (
    organization_id           uuid                            PRIMARY KEY REFERENCES suncly_app.organization (id),
    plan_id                   text                            NOT NULL,
    status                    suncly_app.subscription_status  NOT NULL,
    provider                  text                            NOT NULL DEFAULT 'stripe',
    provider_customer_id      text,
    provider_subscription_id  text,
    current_period_start      timestamptz,
    current_period_end        timestamptz,
    provider_updated_at       timestamptz,
    updated_at                timestamptz                     NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX subscription_provider_customer_idx
    ON suncly_app.subscription (provider, provider_customer_id) WHERE provider_customer_id IS NOT NULL;

CREATE TABLE suncly_app.provider_event (
    provider             text        NOT NULL,
    event_id             text        NOT NULL,
    event_type           text        NOT NULL,
    provider_created_at  timestamptz NOT NULL,
    received_at          timestamptz NOT NULL DEFAULT now(),
    processed            boolean     NOT NULL DEFAULT false,
    result               text        NOT NULL DEFAULT '',
    PRIMARY KEY (provider, event_id)
);

CREATE TABLE suncly_app.meter_report (
    usage_event_id        uuid        PRIMARY KEY REFERENCES suncly_app.usage_event (id),
    provider              text        NOT NULL,
    identifier            text        NOT NULL UNIQUE,
    reported_at           timestamptz NOT NULL DEFAULT now(),
    provider_response_id  text
);

-- -----------------------------------------------------------------------------
-- Trusted signing keys, external tool artifacts, re-evaluation schedule
-- -----------------------------------------------------------------------------

CREATE TABLE suncly_app.signing_key (
    key_id             text        PRIMARY KEY,
    issuer             text        NOT NULL,
    public_key         bytea       NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    revoked_at         timestamptz,
    revocation_reason  text
);

CREATE TABLE suncly_app.external_artifact (
    id              uuid        PRIMARY KEY,
    organization_id uuid        NOT NULL REFERENCES suncly_app.organization (id),
    attestation_id  uuid        NOT NULL REFERENCES public.attestation (id),
    tool            text        NOT NULL,
    tool_version    text        NOT NULL,
    kind            text        NOT NULL,
    storage_ref     text        NOT NULL,
    sha256          text        NOT NULL,
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX external_artifact_attestation_idx ON suncly_app.external_artifact (attestation_id);

CREATE TABLE suncly_app.reevaluation_schedule (
    id               uuid        PRIMARY KEY,
    organization_id  uuid        NOT NULL REFERENCES suncly_app.organization (id),
    registration_id  uuid        NOT NULL REFERENCES suncly_app.agent_registration (id),
    interval_hours   integer     NOT NULL CHECK (interval_hours >= 1),
    runs_per_test_case integer   NOT NULL CHECK (runs_per_test_case >= 1),
    budget_limit     numeric     NOT NULL CHECK (budget_limit >= 0),
    next_run_at      timestamptz NOT NULL,
    enabled          boolean     NOT NULL DEFAULT true,
    created_by       text        NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX reevaluation_due_idx ON suncly_app.reevaluation_schedule (next_run_at) WHERE enabled;

-- -----------------------------------------------------------------------------
-- Append-only guards
-- -----------------------------------------------------------------------------

CREATE TRIGGER usage_event_append_only
    BEFORE UPDATE OR DELETE ON suncly_app.usage_event
    FOR EACH ROW EXECUTE FUNCTION public.suncly_forbid_change();
CREATE TRIGGER usage_event_no_truncate
    BEFORE TRUNCATE ON suncly_app.usage_event
    FOR EACH STATEMENT EXECUTE FUNCTION public.suncly_forbid_change();
CREATE TRIGGER decision_note_append_only
    BEFORE UPDATE OR DELETE ON suncly_app.decision_note
    FOR EACH ROW EXECUTE FUNCTION public.suncly_forbid_change();
CREATE TRIGGER policy_record_append_only
    BEFORE UPDATE OR DELETE ON suncly_app.policy_record
    FOR EACH ROW EXECUTE FUNCTION public.suncly_forbid_change();
CREATE TRIGGER provider_event_no_delete
    BEFORE DELETE ON suncly_app.provider_event
    FOR EACH ROW EXECUTE FUNCTION public.suncly_forbid_change();
CREATE TRIGGER spending_limit_append_only
    BEFORE UPDATE OR DELETE ON suncly_app.spending_limit
    FOR EACH ROW EXECUTE FUNCTION public.suncly_forbid_change();

COMMIT;
