-- =============================================================================
-- Suncly - initial database schema (roadmap stage 3)
-- Migration: 0001_initial_schema.sql
-- Target:    PostgreSQL 13+ (Supabase, Google Cloud SQL, plain Postgres)
--
-- This file implements docs/DATA_MODEL.md and nothing else:
--   * exactly the seven entities of schema §3 (agent, card_version, contract,
--     test_case, attestation, run, decision);
--   * entity, field and enum names exactly as in the schema;
--   * column types as proposed in DATA_MODEL.md (OQ-D1).
--
-- Where SCHEMA.md and this file disagree, SCHEMA.md wins.
--
-- How rules are marked in the comments below:
--   [schema §N]   the rule is taken from SCHEMA.md
--   [invariant N] the numbered invariant in DATA_MODEL.md
--   [Proposed]    the schema does not define it; DATA_MODEL.md proposes it and
--                 tracks it as an open question (OQ-...). If the question is
--                 decided differently, change it in a NEW migration.
--
-- Deliberately NOT in this file:
--   * the job table (OQ-D8: queue infrastructure, not part of the data model);
--   * users, organizations, API keys, signing keys (not among the seven
--     entities; identities come from elsewhere, schema §10);
--   * anything an open question has not decided (listed in db/README.md).
--
-- Foreign keys use the default NO ACTION everywhere: evidence is never deleted
-- as a side effect of deleting something else (DR-002).
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- Enumerations (names and values exactly as in DATA_MODEL.md: Enumerations)
-- -----------------------------------------------------------------------------

CREATE TYPE risk_level          AS ENUM ('low', 'medium', 'high');
CREATE TYPE contract_status     AS ENUM ('draft', 'approved', 'rejected', 'superseded');
CREATE TYPE test_case_kind      AS ENUM ('skill', 'probe_undeclared', 'probe_injection', 'probe_failure');
CREATE TYPE attestation_trigger AS ENUM ('ci', 'schedule', 'card_change', 'manual');
CREATE TYPE attestation_status  AS ENUM ('queued', 'running', 'completed', 'failed', 'cancelled', 'invalidated');
CREATE TYPE run_verdict         AS ENUM ('pass', 'fail', 'inconclusive');
CREATE TYPE judge_layer         AS ENUM ('deterministic', 'model');
CREATE TYPE decision_outcome    AS ENUM ('approve', 'flag', 'block');

-- =============================================================================
-- 1. agent - an agent under attestation, its owner and its risk level
-- =============================================================================

CREATE TABLE agent (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    name        text        NOT NULL CHECK (length(trim(name)) > 0),
    owner       text        NOT NULL CHECK (length(trim(owner)) > 0),
    risk_level  risk_level  NOT NULL
);
COMMENT ON TABLE  agent            IS 'An agent under attestation, its owner and its risk level (schema §3).';
COMMENT ON COLUMN agent.name       IS 'Human-readable name of the agent.';
COMMENT ON COLUMN agent.owner      IS 'Who owns the agent in the customer''s organization. The format is not defined.';
COMMENT ON COLUMN agent.risk_level IS 'low, medium or high. Drives the approval rules in POLICY.md.';

-- =============================================================================
-- 2. card_version - one fetched Agent Card, identified by its hash
-- =============================================================================

CREATE TABLE card_version (
    id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id    uuid        NOT NULL REFERENCES agent (id),
    card_hash   text        NOT NULL CHECK (length(card_hash) > 0),
    raw_json    text        NOT NULL,
    fetched_at  timestamptz NOT NULL DEFAULT now()
);
COMMENT ON TABLE  card_version            IS 'One fetched Agent Card: the raw JSON and its hash (schema §3). Proposed: never changes once written (OQ-D9).';
COMMENT ON COLUMN card_version.card_hash  IS 'Hash of the canonicalized Agent Card. Algorithm and canonicalization are open (OQ-A7).';
COMMENT ON COLUMN card_version.raw_json   IS 'The Agent Card exactly as fetched. text, not jsonb, so the bytes are preserved (OQ-D1).';
COMMENT ON COLUMN card_version.fetched_at IS 'When a card with this hash was first fetched (OQ-D9).';

-- Plain index, not UNIQUE: whether a hash seen before (A, then B, then A)
-- reuses the earlier record or creates a new one is open (OQ-D9).
CREATE INDEX card_version_agent_id_card_hash_idx ON card_version (agent_id, card_hash);

-- =============================================================================
-- 3. contract - a versioned set of test cases for one card version
-- =============================================================================

CREATE TABLE contract (
    id               uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
    card_version_id  uuid            NOT NULL REFERENCES card_version (id),
    version          integer         NOT NULL CHECK (version >= 1),
    status           contract_status NOT NULL DEFAULT 'draft',
    created_at       timestamptz     NOT NULL DEFAULT now(),
    approved_by      text,
    approved_at      timestamptz,

    -- Lets attestation reference (id, card_version_id) together. See attestation.
    CONSTRAINT contract_id_card_version_id_key UNIQUE (id, card_version_id),

    -- [invariant 3, schema §11] approved_by and approved_at are null until the
    -- contract is approved. A draft or a rejected contract was never approved.
    CONSTRAINT contract_not_approved_has_no_approval
        CHECK (status NOT IN ('draft', 'rejected') OR (approved_by IS NULL AND approved_at IS NULL)),
    -- [schema §2, roadmap stage 2] approval fills in approved_by and approved_at.
    CONSTRAINT contract_approved_has_approval
        CHECK (status <> 'approved' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)),
    CONSTRAINT contract_approval_fields_together
        CHECK ((approved_by IS NULL) = (approved_at IS NULL)),
    CONSTRAINT contract_approved_by_not_blank
        CHECK (approved_by IS NULL OR length(trim(approved_by)) > 0)
);
COMMENT ON TABLE  contract             IS 'A versioned set of test cases for one card version, drafted by a model and approved by a human (schema §3). Immutable once approved (schema §2).';
COMMENT ON COLUMN contract.version     IS 'Contract version number. Not UNIQUE yet: whether numbers are per card version or per agent is open (OQ-D5).';
COMMENT ON COLUMN contract.status      IS 'draft, approved, rejected or superseded (schema §11).';
COMMENT ON COLUMN contract.approved_by IS 'Identifier of the human who approved the contract. Null until approved.';
COMMENT ON COLUMN contract.approved_at IS 'When it was approved. Null until approved.';

CREATE INDEX contract_card_version_id_idx ON contract (card_version_id);

-- =============================================================================
-- 4. test_case - one test in a contract, for a declared skill or a probe
-- =============================================================================

CREATE TABLE test_case (
    id           uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id  uuid           NOT NULL REFERENCES contract (id),
    skill_id     text,
    input        jsonb          NOT NULL,
    criteria     jsonb          NOT NULL,
    kind         test_case_kind NOT NULL,

    -- A test of a declared skill names that skill (roadmap stage 2: "skill_id
    -- is the skill's AgentSkill.id"). For probes, nullability is open (OQ-D7),
    -- so the column itself is nullable.
    CONSTRAINT test_case_skill_kind_has_skill_id
        CHECK (kind <> 'skill' OR (skill_id IS NOT NULL AND length(skill_id) > 0))
);
COMMENT ON TABLE  test_case          IS 'One test in a contract, for a declared skill or a probe (schema §3). Immutable once its contract is approved (schema §2).';
COMMENT ON COLUMN test_case.skill_id IS 'The id of the declared AgentSkill this case exercises. Nullable because its value for probes is open (OQ-D7).';
COMMENT ON COLUMN test_case.input    IS 'What the Runner sends to the agent. Format is open (OQ-D7).';
COMMENT ON COLUMN test_case.criteria IS 'What the Judge checks, including Layer 1 checks such as the latency limit. Format is open (OQ-D7).';
COMMENT ON COLUMN test_case.kind     IS 'skill, probe_undeclared, probe_injection or probe_failure.';

CREATE INDEX test_case_contract_id_idx ON test_case (contract_id);

-- =============================================================================
-- 5. attestation - one execution of a contract against the agent
-- =============================================================================

CREATE TABLE attestation (
    id               uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
    contract_id      uuid                NOT NULL REFERENCES contract (id),
    card_version_id  uuid                NOT NULL REFERENCES card_version (id),
    trigger          attestation_trigger NOT NULL,
    status           attestation_status  NOT NULL DEFAULT 'queued',
    started_at       timestamptz         NOT NULL DEFAULT now(),
    finished_at      timestamptz,
    budget_limit     numeric             NOT NULL CHECK (budget_limit >= 0),
    cost_total       numeric             NOT NULL DEFAULT 0 CHECK (cost_total >= 0),
    signature        text,
    signing_key_id   text,

    -- [Proposed, invariant 5, OQ-D6] card_version_id equals the contract's
    -- card_version_id. If OQ-D6 is decided otherwise, drop this constraint.
    CONSTRAINT attestation_card_version_matches_contract
        FOREIGN KEY (contract_id, card_version_id)
        REFERENCES contract (id, card_version_id),

    -- [schema §11] finished_at is set exactly when the attestation has reached
    -- completed, failed, cancelled or invalidated; null until then.
    CONSTRAINT attestation_finished_at_matches_status
        CHECK ((status IN ('completed', 'failed', 'cancelled', 'invalidated')) = (finished_at IS NOT NULL)),
    CONSTRAINT attestation_finished_after_started
        CHECK (finished_at IS NULL OR finished_at >= started_at),

    -- [schema §11] signature and signing_key_id are both null until signed.
    CONSTRAINT attestation_signature_fields_together
        CHECK ((signature IS NULL) = (signing_key_id IS NULL)),

    -- [Proposed, invariant 13, OQ-D6] a completed attestation is signed.
    -- (That it also has a decision is checked by a trigger below.)
    CONSTRAINT attestation_completed_is_signed
        CHECK (status <> 'completed' OR signature IS NOT NULL)
);
COMMENT ON TABLE  attestation                 IS 'One execution of a contract against the agent, with its budget and signature (schema §3, §11). There is no policy outcome here: outcomes live in decision.';
COMMENT ON COLUMN attestation.card_version_id IS 'The card version fetched for this attestation. Proposed: always equal to the contract''s card_version_id (OQ-D6).';
COMMENT ON COLUMN attestation.started_at      IS 'Proposed: when the attestation record is created (OQ-D6).';
COMMENT ON COLUMN attestation.finished_at     IS 'When it reached completed, failed, cancelled or invalidated. Null until then.';
COMMENT ON COLUMN attestation.budget_limit    IS 'The cost cap. The unit is open (OQ-D1).';
COMMENT ON COLUMN attestation.cost_total      IS 'Cost accumulated so far. Proposed: includes every attempt, so it can exceed the sum of run.cost (OQ-D1).';
COMMENT ON COLUMN attestation.signature       IS 'Signature over the payload defined in schema §11. Null until signed. Encoding is open (OQ-A8).';
COMMENT ON COLUMN attestation.signing_key_id  IS 'Identifies the key of the Suncly deployment that signed. Null until signed.';

CREATE INDEX attestation_contract_id_idx     ON attestation (contract_id);
CREATE INDEX attestation_card_version_id_idx ON attestation (card_version_id);

-- =============================================================================
-- 6. run - one execution of one test case
-- =============================================================================

CREATE TABLE run (
    id              uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
    attestation_id  uuid        NOT NULL REFERENCES attestation (id),
    test_case_id    uuid        NOT NULL REFERENCES test_case (id),
    attempt         integer     NOT NULL CHECK (attempt >= 1),
    verdict         run_verdict NOT NULL,
    judge_layer     judge_layer NOT NULL,
    rationale       text,
    latency_ms      integer     CHECK (latency_ms >= 0),
    cost            numeric     NOT NULL CHECK (cost >= 0),
    transcript_ref  text        NOT NULL CHECK (length(transcript_ref) > 0),
    started_at      timestamptz NOT NULL,
    finished_at     timestamptz NOT NULL,

    -- [Proposed, invariant 6, DR-001, roadmap stage 3] the deterministic run
    -- key. A second record with an existing run key is rejected, so a retry
    -- can never be counted twice.
    CONSTRAINT run_key UNIQUE (attestation_id, test_case_id, attempt),

    -- [invariant 7, schema §2] a model verdict is never stored without its rationale.
    CONSTRAINT run_model_verdict_has_rationale
        CHECK (judge_layer <> 'model' OR (rationale IS NOT NULL AND length(trim(rationale)) > 0)),

    CONSTRAINT run_finished_after_started
        CHECK (finished_at >= started_at)
);
COMMENT ON TABLE  run                IS 'One execution of one test case: transcript reference, verdict, timings and cost (schema §3). Append-only: never updated or deleted (schema §2, §8).';
COMMENT ON COLUMN run.attempt        IS 'Repetition number of this test case within the attestation, from 1. Part of the run key. This reading is an interpretation (OQ-D3).';
COMMENT ON COLUMN run.verdict        IS 'pass, fail or inconclusive. inconclusive is never counted as a pass.';
COMMENT ON COLUMN run.judge_layer    IS 'deterministic when Layer 1 decided the verdict, model when Layer 2 did (OQ-D4).';
COMMENT ON COLUMN run.rationale      IS 'The Layer 2 rationale. Required when judge_layer is model.';
COMMENT ON COLUMN run.latency_ms     IS 'The agent''s response time. Proposed: null when there was no response (OQ-D10).';
COMMENT ON COLUMN run.cost           IS 'The cost of this run (OQ-D1).';
COMMENT ON COLUMN run.transcript_ref IS 'Reference to the redacted transcript in object storage (schema §7).';

CREATE INDEX run_test_case_id_idx ON run (test_case_id);

-- =============================================================================
-- 7. decision - a policy outcome for an attestation
-- =============================================================================

CREATE TABLE decision (
    id              uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
    attestation_id  uuid             NOT NULL REFERENCES attestation (id),
    outcome         decision_outcome NOT NULL,
    policy_version  text             NOT NULL CHECK (length(policy_version) > 0),
    decided_by      text             NOT NULL CHECK (length(trim(decided_by)) > 0),
    decided_at      timestamptz      NOT NULL DEFAULT now()
);
COMMENT ON TABLE  decision                IS 'A policy outcome for an attestation, made automatically or by a human (schema §3). Append-only: a resolution is a new record (schema §11).';
COMMENT ON COLUMN decision.outcome        IS 'approve, flag (for human review) or block.';
COMMENT ON COLUMN decision.policy_version IS 'Version of the customer''s policy configuration that produced the decision (OQ-D11).';
COMMENT ON COLUMN decision.decided_by     IS '"policy" for automatic decisions, otherwise the reviewer''s identifier. Not an enum.';

CREATE INDEX decision_attestation_id_decided_at_idx ON decision (attestation_id, decided_at);

-- =============================================================================
-- TRIGGERS: rules that a CHECK constraint cannot express
-- =============================================================================

-- -----------------------------------------------------------------------------
-- run and decision are append-only [invariant 12; schema §2, §8, §11; DR-002]
-- -----------------------------------------------------------------------------

CREATE FUNCTION suncly_forbid_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '% on "%" is not allowed: evidence is append-only, corrections are new records (DR-002)',
        TG_OP, TG_TABLE_NAME;
END;
$$;

CREATE TRIGGER run_append_only
    BEFORE UPDATE OR DELETE ON run
    FOR EACH ROW EXECUTE FUNCTION suncly_forbid_change();
CREATE TRIGGER run_no_truncate
    BEFORE TRUNCATE ON run
    FOR EACH STATEMENT EXECUTE FUNCTION suncly_forbid_change();

CREATE TRIGGER decision_append_only
    BEFORE UPDATE OR DELETE ON decision
    FOR EACH ROW EXECUTE FUNCTION suncly_forbid_change();
CREATE TRIGGER decision_no_truncate
    BEFORE TRUNCATE ON decision
    FOR EACH STATEMENT EXECUTE FUNCTION suncly_forbid_change();

-- -----------------------------------------------------------------------------
-- An approved contract never changes [invariant 2; schema §2]
-- -----------------------------------------------------------------------------

CREATE FUNCTION suncly_contract_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        IF OLD.status IN ('approved', 'superseded') THEN
            RAISE EXCEPTION 'contract % is % and cannot be deleted (schema §2)', OLD.id, OLD.status;
        END IF;
        RETURN OLD;
    END IF;

    -- An update that changes nothing is harmless.
    IF NEW IS NOT DISTINCT FROM OLD THEN
        RETURN NEW;
    END IF;

    IF OLD.status = 'approved' THEN
        -- [Proposed, OQ-D5] the only change allowed to an approved contract is
        -- the move to superseded, with every other field untouched.
        IF NEW.status = 'superseded'
           AND (NEW.id, NEW.card_version_id, NEW.version, NEW.created_at, NEW.approved_by, NEW.approved_at)
               IS NOT DISTINCT FROM
               (OLD.id, OLD.card_version_id, OLD.version, OLD.created_at, OLD.approved_by, OLD.approved_at)
        THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'contract % is approved and cannot be changed; an edit creates a new contract version (schema §2)', OLD.id;
    END IF;

    IF OLD.status = 'superseded' THEN
        RAISE EXCEPTION 'contract % is superseded and cannot be changed (schema §2)', OLD.id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER contract_guard
    BEFORE UPDATE OR DELETE ON contract
    FOR EACH ROW EXECUTE FUNCTION suncly_contract_guard();

-- -----------------------------------------------------------------------------
-- Test cases of an approved contract never change [invariant 2; schema §2]
-- -----------------------------------------------------------------------------

CREATE FUNCTION suncly_test_case_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    s contract_status;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        -- FOR SHARE: a concurrent approval of the contract waits for us, and we wait for it.
        SELECT status INTO s FROM contract WHERE id = OLD.contract_id FOR SHARE;
        IF s IN ('approved', 'superseded') THEN
            RAISE EXCEPTION 'test_case % belongs to a contract that is % and cannot be changed (schema §2)', OLD.id, s;
        END IF;
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO s FROM contract WHERE id = NEW.contract_id FOR SHARE;
        IF s IN ('approved', 'superseded') THEN
            RAISE EXCEPTION 'contract % is % and cannot receive test cases (schema §2)', NEW.contract_id, s;
        END IF;
        RETURN NEW;
    END IF;

    RETURN OLD;
END;
$$;

CREATE TRIGGER test_case_guard
    BEFORE INSERT OR UPDATE OR DELETE ON test_case
    FOR EACH ROW EXECUTE FUNCTION suncly_test_case_guard();

-- -----------------------------------------------------------------------------
-- attestation rules
-- -----------------------------------------------------------------------------

CREATE FUNCTION suncly_attestation_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    s contract_status;
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- [invariant 4; schema §4, step 2] nothing runs against a contract
        -- that is not approved.
        SELECT status INTO s FROM contract WHERE id = NEW.contract_id FOR SHARE;
        IF s IS NOT NULL AND s <> 'approved' THEN
            RAISE EXCEPTION 'contract % is %, not approved: an attestation cannot be created for it (schema §4)', NEW.contract_id, s;
        END IF;
        RETURN NEW;
    END IF;

    -- UPDATE.
    -- [DATA_MODEL.md: Mutability] only status, cost_total, finished_at,
    -- signature and signing_key_id change while the attestation runs.
    IF (NEW.id, NEW.contract_id, NEW.card_version_id, NEW.trigger, NEW.started_at, NEW.budget_limit)
       IS DISTINCT FROM
       (OLD.id, OLD.contract_id, OLD.card_version_id, OLD.trigger, OLD.started_at, OLD.budget_limit)
    THEN
        RAISE EXCEPTION 'attestation %: only status, cost_total, finished_at, signature and signing_key_id may change', OLD.id;
    END IF;

    IF NEW.status IS DISTINCT FROM OLD.status THEN
        -- [invariant 10; schema §11] a failed or invalidated attestation has
        -- no decision. [Proposed, OQ-D6] neither does a cancelled one.
        IF NEW.status IN ('failed', 'invalidated', 'cancelled')
           AND EXISTS (SELECT 1 FROM decision d WHERE d.attestation_id = OLD.id)
        THEN
            RAISE EXCEPTION 'attestation % already has a decision and cannot become % (schema §11)', OLD.id, NEW.status;
        END IF;

        -- [Proposed, invariant 13, OQ-D6] a completed attestation has a decision.
        IF NEW.status = 'completed'
           AND NOT EXISTS (SELECT 1 FROM decision d WHERE d.attestation_id = OLD.id)
        THEN
            RAISE EXCEPTION 'attestation % has no decision and cannot become completed (invariant 13)', OLD.id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER attestation_guard
    BEFORE INSERT OR UPDATE ON attestation
    FOR EACH ROW EXECUTE FUNCTION suncly_attestation_guard();

-- -----------------------------------------------------------------------------
-- A run executes a test case of the attestation's own contract
-- (derived: an attestation is one execution of one contract, schema §3)
-- -----------------------------------------------------------------------------

CREATE FUNCTION suncly_run_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    attestation_contract uuid;
    test_case_contract   uuid;
BEGIN
    SELECT contract_id INTO attestation_contract FROM attestation WHERE id = NEW.attestation_id;
    SELECT contract_id INTO test_case_contract   FROM test_case   WHERE id = NEW.test_case_id;

    -- If either parent is missing, the foreign key reports it.
    IF attestation_contract IS NOT NULL
       AND test_case_contract IS NOT NULL
       AND attestation_contract <> test_case_contract
    THEN
        RAISE EXCEPTION 'test_case % does not belong to the contract of attestation %', NEW.test_case_id, NEW.attestation_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER run_guard
    BEFORE INSERT ON run
    FOR EACH ROW EXECUTE FUNCTION suncly_run_guard();

-- -----------------------------------------------------------------------------
-- decision rules
-- -----------------------------------------------------------------------------

CREATE FUNCTION suncly_decision_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    s attestation_status;
BEGIN
    -- Lock the attestation row so two decisions for the same attestation are
    -- checked one after the other, and its status cannot change underneath us.
    SELECT status INTO s FROM attestation WHERE id = NEW.attestation_id FOR NO KEY UPDATE;

    -- [invariant 10; schema §11] no decision for a failed or invalidated
    -- attestation. [Proposed, OQ-D6] nor for a cancelled one.
    IF s IN ('failed', 'invalidated', 'cancelled') THEN
        RAISE EXCEPTION 'attestation % is %: no decision is made for it (schema §11)', NEW.attestation_id, s;
    END IF;

    -- [invariant 11; schema §4, step 6] the first decision is the Policy engine's.
    IF NEW.decided_by <> 'policy'
       AND NOT EXISTS (SELECT 1 FROM decision d WHERE d.attestation_id = NEW.attestation_id)
    THEN
        RAISE EXCEPTION 'the first decision for attestation % must have decided_by = ''policy'' (schema §4)', NEW.attestation_id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER decision_guard
    BEFORE INSERT ON decision
    FOR EACH ROW EXECUTE FUNCTION suncly_decision_guard();

COMMIT;
