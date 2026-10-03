-- =============================================================================
-- Suncly - initial database schema
-- Migration: 0001_initial_schema.sql
-- Target:    PostgreSQL 13+ (works on Supabase, Neon, RDS, plain Postgres)
--
-- What Suncly does: it fetches an A2A agent's Agent Card, tests whether the
-- agent really does what the card claims, and issues a signed attestation.
--
-- Reading order (same as the data flow):
--   1. organizations, users, organization_members, api_keys   -> who uses Suncly
--   2. agents, card_snapshots                                 -> what is tested
--   3. check_definitions                                      -> which tests exist
--   4. runs, check_results, http_exchanges                    -> what happened
--   5. signing_keys, attestations                             -> the signed result
--   6. audit_log                                              -> who did what
--
-- Conventions:
--   * Primary keys are UUIDs (gen_random_uuid()), except check_definitions
--     (human-readable text id) and audit_log (bigint, append-only).
--   * All timestamps are timestamptz, stored in UTC.
--   * Test data (snapshots, results, exchanges, attestations) is append-only:
--     rows are inserted, never edited. A new test = a new run.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- Enum types
-- -----------------------------------------------------------------------------

CREATE TYPE member_role AS ENUM ('owner', 'admin', 'member');

CREATE TYPE run_status AS ENUM ('queued', 'running', 'completed', 'failed', 'cancelled');

CREATE TYPE check_category AS ENUM ('card', 'transport', 'capability', 'skill', 'error_handling', 'auth');

CREATE TYPE check_severity AS ENUM ('critical', 'major', 'minor');

-- pass    = the claim is true
-- fail    = the claim is false (the agent does not do what the card says)
-- warn    = works, but deviates from the spec in a non-breaking way
-- skipped = not applicable (e.g. the card does not claim streaming)
-- error   = Suncly could not finish the check (timeout, network problem)
CREATE TYPE check_outcome AS ENUM ('pass', 'fail', 'warn', 'skipped', 'error');

CREATE TYPE attestation_verdict AS ENUM ('pass', 'partial', 'fail');

-- -----------------------------------------------------------------------------
-- Helper: keep updated_at current
-- -----------------------------------------------------------------------------

CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;

-- =============================================================================
-- 1. WHO USES SUNCLY
-- =============================================================================

CREATE TABLE organizations (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text        NOT NULL CHECK (length(trim(name)) > 0),
    slug        text        NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'),
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE  organizations      IS 'A customer team. Every agent and run belongs to exactly one organization.';
COMMENT ON COLUMN organizations.slug IS 'URL-safe unique name, lowercase letters, digits and hyphens (e.g. "acme-ai").';

CREATE TRIGGER organizations_set_updated_at
    BEFORE UPDATE ON organizations
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE users (
    id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    email         text        NOT NULL CHECK (email LIKE '%_@_%'),
    display_name  text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE users IS 'A person who can log in. Passwords/sessions are handled by the auth provider, not stored here.';

-- Email is unique regardless of letter case.
CREATE UNIQUE INDEX users_email_lower_key ON users (lower(email));

CREATE TRIGGER users_set_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE organization_members (
    organization_id  uuid        NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    user_id          uuid        NOT NULL REFERENCES users (id)         ON DELETE CASCADE,
    role             member_role NOT NULL DEFAULT 'member',
    created_at       timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);
COMMENT ON TABLE organization_members IS 'Which user belongs to which organization, and with what role.';

CREATE INDEX organization_members_user_id_idx ON organization_members (user_id);

CREATE TABLE api_keys (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  uuid        NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    name             text        NOT NULL CHECK (length(trim(name)) > 0),
    key_prefix       text        NOT NULL CHECK (length(key_prefix) BETWEEN 4 AND 16),
    key_hash         text        NOT NULL UNIQUE CHECK (key_hash ~ '^[0-9a-f]{64}$'),
    created_by       uuid        REFERENCES users (id) ON DELETE SET NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    last_used_at     timestamptz,
    revoked_at       timestamptz
);
COMMENT ON TABLE  api_keys            IS 'Keys for calling the Suncly API from CI or scripts.';
COMMENT ON COLUMN api_keys.key_prefix IS 'First characters of the key, shown in the UI so the user can recognise it.';
COMMENT ON COLUMN api_keys.key_hash   IS 'SHA-256 (lowercase hex) of the full key. The key itself is NEVER stored.';

CREATE INDEX api_keys_organization_id_idx ON api_keys (organization_id);

-- =============================================================================
-- 2. WHAT IS TESTED
-- =============================================================================

CREATE TABLE agents (
    id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id  uuid        NOT NULL REFERENCES organizations (id) ON DELETE CASCADE,
    name             text        NOT NULL CHECK (length(trim(name)) > 0),
    card_url         text        NOT NULL CHECK (card_url ~ '^https://'),
    created_by       uuid        REFERENCES users (id) ON DELETE SET NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),
    updated_at       timestamptz NOT NULL DEFAULT now(),
    UNIQUE (organization_id, card_url)
);
COMMENT ON TABLE  agents          IS 'An A2A agent registered for testing. One row per agent per organization.';
COMMENT ON COLUMN agents.card_url IS 'Full https URL of the Agent Card. Only https is allowed (SSRF protection starts here).';

CREATE TRIGGER agents_set_updated_at
    BEFORE UPDATE ON agents
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE card_snapshots (
    id                 uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id           uuid        NOT NULL REFERENCES agents (id) ON DELETE CASCADE,
    raw_card           jsonb       NOT NULL,
    sha256             text        NOT NULL CHECK (sha256 ~ '^[0-9a-f]{64}$'),
    protocol_version   text,
    is_schema_valid    boolean     NOT NULL,
    validation_errors  jsonb       NOT NULL DEFAULT '[]'::jsonb
                                   CHECK (jsonb_typeof(validation_errors) = 'array'),
    fetched_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (agent_id, sha256),
    -- Lets runs reference (id, agent_id) so a run cannot point at another agent's card.
    UNIQUE (id, agent_id),
    -- A valid card has no validation errors.
    CHECK (NOT is_schema_valid OR validation_errors = '[]'::jsonb)
);
COMMENT ON TABLE  card_snapshots                   IS 'An exact copy of an Agent Card at the moment it was fetched. Immutable. A changed card = a new snapshot.';
COMMENT ON COLUMN card_snapshots.raw_card          IS 'The Agent Card JSON exactly as the agent served it.';
COMMENT ON COLUMN card_snapshots.sha256            IS 'SHA-256 (lowercase hex) of the raw response bytes. This hash goes into the attestation.';
COMMENT ON COLUMN card_snapshots.protocol_version  IS 'A2A protocol version the card declares, if any.';
COMMENT ON COLUMN card_snapshots.is_schema_valid   IS 'Whether the card passed JSON Schema validation for the A2A spec.';
COMMENT ON COLUMN card_snapshots.validation_errors IS 'JSON array of schema validation errors; empty array when valid.';

-- =============================================================================
-- 3. WHICH TESTS EXIST
-- =============================================================================

CREATE TABLE check_definitions (
    id           text           PRIMARY KEY CHECK (id ~ '^[a-z_]+(\.[a-z_]+)+$'),
    category     check_category NOT NULL,
    severity     check_severity NOT NULL,
    title        text           NOT NULL,
    description  text           NOT NULL,
    per_skill    boolean        NOT NULL DEFAULT false,
    is_active    boolean        NOT NULL DEFAULT true,
    created_at   timestamptz    NOT NULL DEFAULT now()
);
COMMENT ON TABLE  check_definitions           IS 'Catalog of all checks the test engine can run. Rows are added by migrations, not by users.';
COMMENT ON COLUMN check_definitions.id        IS 'Stable human-readable id, e.g. "capability.streaming". Never renamed once released.';
COMMENT ON COLUMN check_definitions.per_skill IS 'true = the check runs once for every skill on the card; false = once per run.';

INSERT INTO check_definitions (id, category, severity, title, description, per_skill) VALUES
    ('card.reachable',               'card',           'critical', 'Agent Card is reachable',
     'The Agent Card URL answers over https with a successful status and JSON content.', false),
    ('card.schema_valid',            'card',           'critical', 'Agent Card matches the A2A schema',
     'The Agent Card validates against the JSON Schema of the pinned A2A spec version.', false),
    ('transport.endpoint_reachable', 'transport',      'critical', 'Declared endpoint answers',
     'The service URL declared on the card accepts a well-formed request.', false),
    ('capability.streaming',         'capability',     'major',    'Streaming works as declared',
     'If the card declares streaming, a streaming request returns a valid event stream.', false),
    ('capability.push_notifications','capability',     'major',    'Push notifications work as declared',
     'If the card declares push notifications, a notification config can be registered.', false),
    ('skill.responds',               'skill',          'major',    'Skill responds to its own example',
     'Sending one of the skill''s declared examples produces a completed task or a message.', true),
    ('skill.output_modes',           'skill',          'major',    'Skill returns a declared output type',
     'The content type of the response is one of the output modes the card declares.', true),
    ('error_handling.invalid_request','error_handling','minor',    'Malformed request is rejected correctly',
     'A malformed request returns a proper protocol error instead of a crash or a 200.', false),
    ('error_handling.unknown_task',  'error_handling', 'minor',    'Unknown task id is rejected correctly',
     'Asking for a task id that does not exist returns the task-not-found error.', false),
    ('auth.enforced',                'auth',           'critical', 'Declared authentication is enforced',
     'If the card declares a security scheme, a request without credentials is rejected.', false);

-- =============================================================================
-- 4. WHAT HAPPENED
-- =============================================================================

CREATE TABLE runs (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id          uuid        NOT NULL REFERENCES agents (id) ON DELETE CASCADE,
    card_snapshot_id  uuid,
    status            run_status  NOT NULL DEFAULT 'queued',
    spec_version      text        NOT NULL,
    engine_version    text        NOT NULL,
    triggered_by      uuid        REFERENCES users (id) ON DELETE SET NULL,
    error_message     text,
    created_at        timestamptz NOT NULL DEFAULT now(),
    started_at        timestamptz,
    finished_at       timestamptz,

    -- The snapshot must belong to the same agent as the run.
    FOREIGN KEY (card_snapshot_id, agent_id)
        REFERENCES card_snapshots (id, agent_id) ON DELETE CASCADE,

    -- Timestamps must agree with the status.
    CHECK (status <> 'queued'  OR (started_at IS NULL AND finished_at IS NULL)),
    CHECK (status <> 'running' OR (started_at IS NOT NULL AND finished_at IS NULL)),
    CHECK ((status IN ('completed', 'failed', 'cancelled')) = (finished_at IS NOT NULL)),
    CHECK (status NOT IN ('completed', 'failed') OR started_at IS NOT NULL),
    CHECK (finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at),
    -- A completed run always has the card it tested; a failed run always says why.
    CHECK (status <> 'completed' OR card_snapshot_id IS NOT NULL),
    CHECK (status <> 'failed'    OR error_message IS NOT NULL)
);
COMMENT ON TABLE  runs                  IS 'One execution of the test engine against one agent.';
COMMENT ON COLUMN runs.card_snapshot_id IS 'The card version this run tested. NULL until the card is fetched (or if fetching failed).';
COMMENT ON COLUMN runs.status           IS 'queued -> running -> completed | failed | cancelled. "failed" means Suncly itself broke, NOT that the agent failed checks.';
COMMENT ON COLUMN runs.spec_version     IS 'A2A spec version the checks were run against.';
COMMENT ON COLUMN runs.engine_version   IS 'Version (git tag or commit) of the Suncly test engine.';
COMMENT ON COLUMN runs.error_message    IS 'Why the run failed. Filled only when status = failed.';

CREATE INDEX runs_agent_id_created_at_idx ON runs (agent_id, created_at DESC);
CREATE INDEX runs_card_snapshot_id_idx    ON runs (card_snapshot_id);
-- Lets the worker find the next job quickly.
CREATE INDEX runs_queued_idx ON runs (created_at) WHERE status = 'queued';

CREATE TABLE check_results (
    id                   uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id               uuid          NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    check_definition_id  text          NOT NULL REFERENCES check_definitions (id) ON DELETE RESTRICT,
    skill_id             text          NOT NULL DEFAULT '',
    claim                text          NOT NULL,
    outcome              check_outcome NOT NULL,
    message              text,
    duration_ms          integer       CHECK (duration_ms >= 0),
    created_at           timestamptz   NOT NULL DEFAULT now(),
    UNIQUE (run_id, check_definition_id, skill_id),
    -- Anything other than a pass must explain itself.
    CHECK (outcome = 'pass' OR message IS NOT NULL)
);
COMMENT ON TABLE  check_results          IS 'The outcome of one check in one run. One row per check (and per skill for per-skill checks).';
COMMENT ON COLUMN check_results.skill_id IS 'Skill id from the Agent Card for per-skill checks; empty string for run-level checks.';
COMMENT ON COLUMN check_results.claim    IS 'What the card claimed, in plain words, e.g. "capabilities.streaming = true".';
COMMENT ON COLUMN check_results.message  IS 'What Suncly observed. Required unless the outcome is pass.';

CREATE INDEX check_results_check_definition_id_idx ON check_results (check_definition_id);

CREATE TABLE http_exchanges (
    id                uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    check_result_id   uuid        NOT NULL REFERENCES check_results (id) ON DELETE CASCADE,
    seq               integer     NOT NULL CHECK (seq >= 1),
    request_method    text        NOT NULL CHECK (request_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS')),
    request_url       text        NOT NULL,
    request_headers   jsonb       NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(request_headers) = 'object'),
    request_body      text,
    response_status   integer     CHECK (response_status BETWEEN 100 AND 599),
    response_headers  jsonb       CHECK (jsonb_typeof(response_headers) = 'object'),
    response_body     text,
    body_truncated    boolean     NOT NULL DEFAULT false,
    error             text,
    duration_ms       integer     CHECK (duration_ms >= 0),
    sent_at           timestamptz NOT NULL DEFAULT now(),
    UNIQUE (check_result_id, seq),
    -- Every exchange ends in either a response or an error.
    CHECK (response_status IS NOT NULL OR error IS NOT NULL)
);
COMMENT ON TABLE  http_exchanges                 IS 'Evidence: the raw requests Suncly sent and the raw responses the agent returned.';
COMMENT ON COLUMN http_exchanges.seq             IS 'Order of the exchange within its check, starting at 1.';
COMMENT ON COLUMN http_exchanges.request_headers IS 'Credentials (Authorization, API keys, cookies) MUST be redacted by the app before insert.';
COMMENT ON COLUMN http_exchanges.response_body   IS 'Stored as text because it may be JSON, an SSE stream or an error page.';
COMMENT ON COLUMN http_exchanges.body_truncated  IS 'true if the response body was cut at the size limit.';
COMMENT ON COLUMN http_exchanges.error           IS 'Network-level failure (timeout, DNS, TLS, blocked by SSRF guard) when no response arrived.';

-- =============================================================================
-- 5. THE SIGNED RESULT
-- =============================================================================

CREATE TABLE signing_keys (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    key_id      text        NOT NULL UNIQUE,
    algorithm   text        NOT NULL DEFAULT 'ed25519' CHECK (algorithm = 'ed25519'),
    public_key  text        NOT NULL UNIQUE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    retired_at  timestamptz
);
COMMENT ON TABLE  signing_keys            IS 'PUBLIC keys used to verify attestations. Private keys live in the secret manager, NEVER in this database.';
COMMENT ON COLUMN signing_keys.key_id     IS 'Short public identifier of the key, included in each attestation (e.g. "suncly-2026-10").';
COMMENT ON COLUMN signing_keys.public_key IS 'Base64-encoded Ed25519 public key.';
COMMENT ON COLUMN signing_keys.retired_at IS 'Set when the key stops signing new attestations. Old attestations stay verifiable.';

CREATE TABLE attestations (
    id                 uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id             uuid                NOT NULL UNIQUE REFERENCES runs (id) ON DELETE CASCADE,
    signing_key_id     uuid                NOT NULL REFERENCES signing_keys (id) ON DELETE RESTRICT,
    public_id          text                NOT NULL UNIQUE CHECK (public_id ~ '^[A-Za-z0-9_-]{16,64}$'),
    verdict            attestation_verdict NOT NULL,
    payload            jsonb               NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
    payload_sha256     text                NOT NULL CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    signature          text                NOT NULL,
    issued_at          timestamptz         NOT NULL DEFAULT now(),
    expires_at         timestamptz,
    revoked_at         timestamptz,
    revocation_reason  text,
    CHECK (expires_at IS NULL OR expires_at > issued_at),
    CHECK ((revoked_at IS NULL) = (revocation_reason IS NULL))
);
COMMENT ON TABLE  attestations                IS 'The signed report for one completed run. At most one per run. The app must only issue it for runs with status = completed.';
COMMENT ON COLUMN attestations.public_id      IS 'Random unguessable id used in the public verification URL.';
COMMENT ON COLUMN attestations.verdict        IS 'pass = all checks passed; partial = only minor checks failed; fail = a critical or major check failed.';
COMMENT ON COLUMN attestations.payload        IS 'The report: card hash, spec version, engine version, check outcomes, timestamps.';
COMMENT ON COLUMN attestations.payload_sha256 IS 'SHA-256 (lowercase hex) of the exact canonical bytes that were signed.';
COMMENT ON COLUMN attestations.signature      IS 'Base64-encoded Ed25519 signature over the canonical payload bytes.';

CREATE INDEX attestations_signing_key_id_idx ON attestations (signing_key_id);

-- =============================================================================
-- 6. WHO DID WHAT
-- =============================================================================

CREATE TABLE audit_log (
    id               bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    organization_id  uuid        REFERENCES organizations (id) ON DELETE SET NULL,
    actor_user_id    uuid        REFERENCES users (id)         ON DELETE SET NULL,
    action           text        NOT NULL CHECK (action ~ '^[a-z_]+(\.[a-z_]+)+$'),
    target_type      text,
    target_id        text,
    metadata         jsonb       NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(metadata) = 'object'),
    created_at       timestamptz NOT NULL DEFAULT now(),
    CHECK ((target_type IS NULL) = (target_id IS NULL))
);
COMMENT ON TABLE  audit_log               IS 'Append-only log of important actions. Rows are never updated or deleted by the app.';
COMMENT ON COLUMN audit_log.actor_user_id IS 'NULL when the action was done by the system or an API key.';
COMMENT ON COLUMN audit_log.action        IS 'Dotted name, e.g. "agent.created", "run.started", "attestation.revoked".';

CREATE INDEX audit_log_organization_id_created_at_idx ON audit_log (organization_id, created_at DESC);

-- =============================================================================
-- VIEW: one line per run with counted outcomes (what the dashboard lists)
-- =============================================================================

CREATE VIEW run_summaries AS
SELECT
    r.id                AS run_id,
    r.agent_id,
    a.organization_id,
    r.status,
    r.created_at,
    r.started_at,
    r.finished_at,
    count(cr.id)                                      AS checks_total,
    count(cr.id) FILTER (WHERE cr.outcome = 'pass')    AS checks_passed,
    count(cr.id) FILTER (WHERE cr.outcome = 'fail')    AS checks_failed,
    count(cr.id) FILTER (WHERE cr.outcome = 'warn')    AS checks_warned,
    count(cr.id) FILTER (WHERE cr.outcome = 'skipped') AS checks_skipped,
    count(cr.id) FILTER (WHERE cr.outcome = 'error')   AS checks_errored
FROM runs r
JOIN agents a               ON a.id = r.agent_id
LEFT JOIN check_results cr  ON cr.run_id = r.id
GROUP BY r.id, a.organization_id;

COMMENT ON VIEW run_summaries IS 'Per-run totals of check outcomes. Computed live, so it can never disagree with check_results.';

COMMIT;
