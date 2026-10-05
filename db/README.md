# Database

The Postgres schema for Suncly's seven entities. It belongs to roadmap
**stage 3** ("Postgres, Evidence store, signing"); stages 1 and 2 do not need a
database.

| File | Contents |
|---|---|
| `migrations/0001_initial_schema.sql` | The seven tables, eight enums, constraints and triggers. |
| `migrations/0002_rls_and_search_path.sql` | Row level security on the seven tables, with no policies, and a fixed `search_path` for the six trigger functions. |
| `README.md` | This document: what the migrations enforce and what they leave open. |

**Source of truth.** This folder implements
[docs/DATA_MODEL.md](../docs/DATA_MODEL.md). It does not redefine the model:
entities, fields, enum values and the ER diagram live there. Where
[SCHEMA.md](../SCHEMA.md) and this folder disagree, the schema wins.

Conventions are as in [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md):
"schema §N" refers to SCHEMA.md, **Proposed** marks what the schema does not
define, and `OQ-…` marks open questions.

## Running it

Any PostgreSQL 13 or newer works: Supabase, Google Cloud SQL or a local
install. Apply the files in order; each runs in one transaction, so either
everything in it is created or nothing is:

```bash
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
```

`suncly db migrate` does the same and applies only what the database does not
hold yet; `suncly db check` verifies the result. On Supabase the files can
also be pasted into the SQL Editor, one after the other.

On Supabase, `DATABASE_URL` must use port 5432: the direct connection
(`postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres`,
which needs IPv6 or the IPv4 add-on) or the session pooler
(`postgresql://postgres.<project-ref>:<password>@aws-<n>-<region>.pooler.supabase.com:5432/postgres`).
Never the transaction pooler on port 6543: the store keeps one connection and
uses prepared statements, which transaction mode does not support.

To check the result by hand:

```sql
SELECT count(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- expected: 7
SELECT count(*) FROM pg_tables WHERE schemaname = 'public' AND rowsecurity;
-- expected: 7 (migration 0002)
SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname = 'public' AND p.proname LIKE 'suncly%' AND p.proconfig IS NOT NULL;
-- expected: 6 (migration 0002)
```

Never put the connection string or the database password in the repository.

## What is in the migration

Exactly the seven entities of schema §3, with the names, fields and enum
values of DATA_MODEL.md and the column types it proposes (OQ-D1):

`agent` · `card_version` · `contract` · `test_case` · `attestation` · `run` ·
`decision`

Not included, on purpose:

- **The job table.** OQ-D8 proposes that it is queue infrastructure, not part
  of the data model. It gets its own migration when the Orchestrator needs it.
- **Users, organizations, API keys, signing keys.** They are not among the
  seven entities. Reviewer identities come from elsewhere (schema §10), and
  how verifiers obtain public keys is open (OQ-A8).

## Rules the database enforces

Each rule below is a constraint or trigger in the migration. "Invariant N"
refers to the numbered list in DATA_MODEL.md.

### From the schema

| Rule | Source | Enforced by |
|---|---|---|
| `approved_by` and `approved_at` are null until the contract is approved, and filled in when it is. | Invariant 3, schema §11 | `CHECK` constraints on `contract` |
| An approved contract never changes and cannot be deleted. | Invariant 2, schema §2 | Trigger `contract_guard` |
| The test cases of an approved contract cannot be added to, changed or deleted. | Invariant 2, schema §2 | Trigger `test_case_guard` |
| An attestation can only be created for a contract whose `status` is `approved`. | Invariant 4, schema §4 | Trigger `attestation_guard` |
| `finished_at` is set exactly when the attestation is `completed`, `failed`, `cancelled` or `invalidated`. | Schema §11 | `CHECK` on `attestation` |
| `signature` and `signing_key_id` are both null until signed. | Schema §11 | `CHECK` on `attestation` |
| Only `status`, `cost_total`, `finished_at`, `signature` and `signing_key_id` of an attestation may change. | DATA_MODEL.md: Mutability | Trigger `attestation_guard` |
| `rationale` is present whenever `judge_layer` is `model`. | Invariant 7, schema §2 | `CHECK` on `run` |
| A `failed` or `invalidated` attestation has no decision. | Invariant 10, schema §11 | Triggers `decision_guard` and `attestation_guard` |
| The first decision for an attestation has `decided_by` = `policy`. | Invariant 11, schema §4 | Trigger `decision_guard` |
| `run` and `decision` records are never updated, deleted or truncated. | Invariant 12, DR-002 | Triggers `run_append_only`, `decision_append_only` and the `no_truncate` triggers |
| Nothing is deleted as a side effect: no foreign key cascades. | DR-002 | Foreign keys use `NO ACTION` |

### Proposed in DATA_MODEL.md

These rules are proposals tied to open questions. They are enforced so the
database fails safe, and each can be removed with a new migration if its
question is decided differently.

| Rule | Open question | Enforced by | If decided otherwise |
|---|---|---|---|
| (`attestation_id`, `test_case_id`, `attempt`) is unique: the deterministic run key. | OQ-D3, DR-001 | `UNIQUE` constraint `run_key` | Replace the constraint with the new key. |
| `attestation.card_version_id` equals the contract's `card_version_id`. | OQ-D6 | Foreign key `attestation_card_version_matches_contract` | Drop the constraint. |
| A `completed` attestation has a decision and a signature. | OQ-D6 | `CHECK` `attestation_completed_is_signed` and trigger `attestation_guard` | Drop the check and the trigger branch. |
| A `cancelled` attestation has no decision. | OQ-D6 | Triggers `decision_guard` and `attestation_guard` | Remove `cancelled` from both lists. |
| The only change allowed to an approved contract is the move to `superseded`. | OQ-D5 | Trigger `contract_guard` | Adjust the trigger. |

### Derived

Two rules are not stated in the documents but follow from them. Please
confirm them.

| Rule | Reasoning | Enforced by |
|---|---|---|
| A run's test case belongs to the contract of the run's attestation. | An attestation is one execution of one contract (schema §3). | Trigger `run_guard` |
| A test case of kind `skill` has a `skill_id`. | Roadmap stage 2: "`skill_id` is the skill's `AgentSkill.id`". The column stays nullable for probes (OQ-D7). | `CHECK` on `test_case` |

## Rules the application must enforce

The database cannot check these, or checking them would decide an open
question.

| Rule | Source | Why not in the database |
|---|---|---|
| Every contract has at least one test case per declared skill. | Invariant 1, schema §2 | Needs the skills parsed out of `card_version.raw_json`. |
| `inconclusive` is never counted as a pass in any aggregation. | Invariant 8, schema §2 | Aggregation happens in the Policy engine. |
| No run is enqueued once `cost_total` has reached `budget_limit`. | Invariant 9, schema §11 | Enqueuing happens in the Orchestrator. |
| A human resolution follows a `flag`; later decisions are corrections. | Invariant 11, OQ-D11 | How many decisions are allowed, and which outcomes a human may choose, is open. |
| Transcripts are redacted before they are stored. | DR-003 | The database only holds `transcript_ref`. |
| A `card_version` record never changes once written. | OQ-D9 (Proposed) | Left out until OQ-D9 is decided. |
| An attestation is frozen once final and signed. | OQ-D6, OQ-F7 (Proposed) | Left out until those are decided. |

## Open questions this migration does not decide

Where a question is open, the migration takes the least restrictive form and
says so in a comment.

| Question | What the migration does |
|---|---|
| OQ-D1: types and cost units | Uses the proposed types (`uuid`, `numeric`, `text` for `raw_json`). Stores no unit. |
| OQ-D5: is `contract.version` numbered per card version or per agent? | No `UNIQUE` on `version`. |
| OQ-D7: `skill_id` for probes | Nullable for probes. |
| OQ-D9: is a card hash seen before reused? | (`agent_id`, `card_hash`) is indexed but not `UNIQUE`. |
| OQ-D2, OQ-D4: card URL, repetitions, judge model version | No columns added. The seven entities keep exactly the schema's fields. |
| OQ-A7, OQ-A8: hash and signature formats | `card_hash` and `signature` are plain `text` with no format check. |

## Row level security and function search paths (migration 0002)

Supabase's Security Advisor reports two things about the schema of 0001:
`RLS Disabled in Public` for the seven tables, and `Function Search Path
Mutable` for the six trigger functions. Migration 0002 answers both without
changing the model:

- **Row level security is enabled on all seven tables, with no policies.**
  Every role sees no rows and can write nothing until a policy is added in a
  later migration, except the table owner (the role that ran the migrations),
  superusers and roles with the `BYPASSRLS` attribute; on Supabase those are
  the `postgres` role, which owns the tables, and `service_role`. Postgres
  applies row security to the owner only under `FORCE ROW LEVEL SECURITY`,
  which the migration clears. Suncly's Postgres store connects as the owner.
  The Security Advisor then shows one INFO entry per table, `RLS Enabled No
  Policy`: that is the intended state until policies exist, not a failure.
- **Each trigger function runs with `SET search_path = ''`** and names every
  table and type it uses as `public.…`, so an object planted in another
  schema can never be picked up instead. From 0002 on, the schema lives in
  `public`.

The migration is idempotent: it is safe on a database where row level
security was already enabled by hand, and when run twice. `suncly db check`
reports a table without row level security, a table where it is forced, a
function without a fixed `search_path`, and a function whose body is not the
one in 0002 (for example after a hand-run `ALTER FUNCTION ... SET search_path
= ''` on the bodies of 0001, which would break every guard that reads another
table). `suncly db migrate` repairs each of these by applying 0002 again.

The guards run as `SECURITY INVOKER`: they read `contract`, `attestation`,
`test_case` and `decision` under the writing role's own policies, and treat a
parent row they cannot see as absent. A later migration that lets another role
write must therefore also give that role `SELECT` (and, for the row locks the
guards take, `UPDATE`) policies on those tables, or the guards would pass
where they should refuse.

## Changing the schema

A migration file is never edited once it has been run anywhere. Every change
is a new file: `0002_...sql`, `0003_...sql` and so on.

Postgres superusers can disable triggers, so the append-only triggers protect
against application bugs, not against someone with full database access.
Until policies exist (migration 0002), the application has to connect as the
table owner; a separate, non-superuser role with its own policies is the next
step.

## Migration 0003: the application layer

`migrations/0003_application_layer.sql` creates schema `suncly_app` for the
hosted product (SCHEMA.md §12, docs/DATA_MODEL.md "Application layer"). It
touches nothing in `public`: the seven entities stay the complete list of
evidence, and every application row points at them by id.

| Group | Tables |
|---|---|
| Tenancy | `organization`, `membership` |
| Agents and runs | `agent_registration`, `attestation_meta`, `external_artifact`, `reevaluation_schedule` |
| Policy | `policy_record` (append-only), `decision_note` (append-only) |
| Jobs | `job`, `job_attempt`, `outbox` |
| Money | `reservation`, `usage_event` (append-only, one line per run and operation), `spending_limit`, `subscription`, `provider_event`, `meter_report` |
| Keys | `signing_key` (revocation is a column, never a delete) |

Apply the three files in order; `suncly db migrate` does, and recognises
from the catalog which ones a database already holds (0003: the
`suncly_app` tables exist):

```bash
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$f"; done
```

**Roles.** Migration 0002 enables row level security on the seven core
tables with no policies, so every role except the table owner sees no rows.
The hosted processes therefore connect as the owner role today
(deploy/terraform/sql.tf creates one application role); separate API,
worker and migrate roles need policies first and are the next step. The
migration files grant nothing, so they run unchanged on a single-role local
database.

**Retention and deletion.** Evidence rows and transcripts are immutable and
are not deleted by any code path. Deleting an organization is not
implemented; the honest answer today is that an operator removes its rows
by hand, in dependency order, after exporting what the customer is owed.
The evidence bucket (deploy/terraform/storage.tf) keeps objects for the
configured retention period and versions them; that period is the only
deletion schedule that exists.
