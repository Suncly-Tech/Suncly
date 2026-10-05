-- =============================================================================
-- Suncly - row level security and fixed function search paths
-- Migration: 0002_rls_and_search_path.sql
-- Target:    PostgreSQL 13+ (Supabase, Google Cloud SQL, plain Postgres)
--
-- Supabase's Security Advisor flagged two things in the schema of 0001:
--   * "RLS Disabled in Public": the seven tables had no row level security;
--   * "Function Search Path Mutable": the six trigger functions resolved table
--     and type names through the caller's search_path.
--
-- This file changes no entity, field, enum, constraint or trigger. It:
--   1. enables row level security on the seven tables, with NO policies. With
--      row level security on and no policies, every role sees no rows and can
--      write nothing, except the table owner (the role that ran 0001),
--      superusers and roles with the BYPASSRLS attribute (on Supabase: the
--      postgres role and service_role). Suncly's Postgres store connects as
--      the owner, so it keeps working. FORCE ROW LEVEL SECURITY is cleared:
--      it would apply the empty policy set to the owner too and lock the
--      store out.
--   2. gives each of the six trigger functions a fixed, empty search_path and
--      schema-qualifies every table and type they reference. Apart from that,
--      the function bodies are those of 0001. CREATE OR REPLACE keeps the
--      functions' identity, so the triggers of 0001 stay bound to them.
--
-- From this migration on, the schema lives in the schema "public". 0001 created
-- its objects in the connection's current schema; the qualified names below
-- assume that was public, as it is on Supabase, in CI and in the local setups.
--
-- Idempotent: safe on a fresh database right after 0001, on a database where
-- row level security was already enabled by hand, and when run twice. Suncly
-- re-applies it when a guard's body differs from this file, for example after
-- a hand-run ALTER FUNCTION ... SET search_path = '' on the bodies of 0001,
-- which would break the guards' table lookups.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 1. Row level security on the seven tables, with no policies
-- -----------------------------------------------------------------------------

ALTER TABLE public.agent        ENABLE ROW LEVEL SECURITY, NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.card_version ENABLE ROW LEVEL SECURITY, NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.contract     ENABLE ROW LEVEL SECURITY, NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.test_case    ENABLE ROW LEVEL SECURITY, NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.attestation  ENABLE ROW LEVEL SECURITY, NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.run          ENABLE ROW LEVEL SECURITY, NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.decision     ENABLE ROW LEVEL SECURITY, NO FORCE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- 2. A fixed search_path for the six trigger functions
-- -----------------------------------------------------------------------------

-- run and decision are append-only [invariant 12; schema §2, §8, §11; DR-002]

CREATE OR REPLACE FUNCTION public.suncly_forbid_change() RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    RAISE EXCEPTION '% on "%" is not allowed: evidence is append-only, corrections are new records (DR-002)',
        TG_OP, TG_TABLE_NAME;
END;
$$;

-- An approved contract never changes [invariant 2; schema §2]

CREATE OR REPLACE FUNCTION public.suncly_contract_guard() RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
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

-- Test cases of an approved contract never change [invariant 2; schema §2]

CREATE OR REPLACE FUNCTION public.suncly_test_case_guard() RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
    s public.contract_status;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        -- FOR SHARE: a concurrent approval of the contract waits for us, and we wait for it.
        SELECT status INTO s FROM public.contract WHERE id = OLD.contract_id FOR SHARE;
        IF s IN ('approved', 'superseded') THEN
            RAISE EXCEPTION 'test_case % belongs to a contract that is % and cannot be changed (schema §2)', OLD.id, s;
        END IF;
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        SELECT status INTO s FROM public.contract WHERE id = NEW.contract_id FOR SHARE;
        IF s IN ('approved', 'superseded') THEN
            RAISE EXCEPTION 'contract % is % and cannot receive test cases (schema §2)', NEW.contract_id, s;
        END IF;
        RETURN NEW;
    END IF;

    RETURN OLD;
END;
$$;

-- attestation rules

CREATE OR REPLACE FUNCTION public.suncly_attestation_guard() RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
    s public.contract_status;
BEGIN
    IF TG_OP = 'INSERT' THEN
        -- [invariant 4; schema §4, step 2] nothing runs against a contract
        -- that is not approved.
        SELECT status INTO s FROM public.contract WHERE id = NEW.contract_id FOR SHARE;
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
           AND EXISTS (SELECT 1 FROM public.decision d WHERE d.attestation_id = OLD.id)
        THEN
            RAISE EXCEPTION 'attestation % already has a decision and cannot become % (schema §11)', OLD.id, NEW.status;
        END IF;

        -- [Proposed, invariant 13, OQ-D6] a completed attestation has a decision.
        IF NEW.status = 'completed'
           AND NOT EXISTS (SELECT 1 FROM public.decision d WHERE d.attestation_id = OLD.id)
        THEN
            RAISE EXCEPTION 'attestation % has no decision and cannot become completed (invariant 13)', OLD.id;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

-- A run executes a test case of the attestation's own contract
-- (derived: an attestation is one execution of one contract, schema §3)

CREATE OR REPLACE FUNCTION public.suncly_run_guard() RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
    attestation_contract uuid;
    test_case_contract   uuid;
BEGIN
    SELECT contract_id INTO attestation_contract FROM public.attestation WHERE id = NEW.attestation_id;
    SELECT contract_id INTO test_case_contract   FROM public.test_case   WHERE id = NEW.test_case_id;

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

-- decision rules

CREATE OR REPLACE FUNCTION public.suncly_decision_guard() RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
    s public.attestation_status;
BEGIN
    -- Lock the attestation row so two decisions for the same attestation are
    -- checked one after the other, and its status cannot change underneath us.
    SELECT status INTO s FROM public.attestation WHERE id = NEW.attestation_id FOR NO KEY UPDATE;

    -- [invariant 10; schema §11] no decision for a failed or invalidated
    -- attestation. [Proposed, OQ-D6] nor for a cancelled one.
    IF s IN ('failed', 'invalidated', 'cancelled') THEN
        RAISE EXCEPTION 'attestation % is %: no decision is made for it (schema §11)', NEW.attestation_id, s;
    END IF;

    -- [invariant 11; schema §4, step 6] the first decision is the Policy engine's.
    IF NEW.decided_by <> 'policy'
       AND NOT EXISTS (SELECT 1 FROM public.decision d WHERE d.attestation_id = NEW.attestation_id)
    THEN
        RAISE EXCEPTION 'the first decision for attestation % must have decided_by = ''policy'' (schema §4)', NEW.attestation_id;
    END IF;

    RETURN NEW;
END;
$$;

COMMIT;
