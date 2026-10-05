# SUNCLY — ARCHITECTURE SCHEMA
Agent attestation: prove an A2A agent does what its Agent Card claims.

## 1. SYSTEM LAYOUT

```text
 Agent Card ──┐   Trigger ──┐   Agent endpoint
              ▼             ▼          ▲
┌──────────────────────────────────────┼──────┐
│ SUNCLY CORE                          │      │
│                                      │      │
│  Contract ──► Orchestrator ──► Runner┘      │
│  builder      (job queue)     (isolated)    │
│                                  │          │
│  Policy  ◄── Evidence  ◄──── Judge          │
│  engine      store                          │
└────┬────────────────────────────────────────┘
     ▼
 Registry status · CI gate · Evidence report
```

## 2. COMPONENTS

### CONTRACT BUILDER
- Input: Agent Card JSON, canonicalized and hashed.
- Output: versioned contract, one or more test cases per declared skill.
- A model drafts the cases; a human approves them.
- Approved contracts are immutable. Any edit creates a new version.

### ORCHESTRATOR
- Expands a contract into runs (test case x repetitions).
- Owns concurrency limits, retries, timeouts, cost budget per attestation.
- Stateless workers pull from a queue; scales horizontally.

### RUNNER
- The only component holding customer credentials and calling the agent.
- Acts as an A2A client: sends the task, follows task state to the end,
  captures every message.
- Runs in its own process/container, network limited to the target.
- Designed so it can later run inside the customer's network.

### JUDGE
- Layer 1 (deterministic): valid schema, final task state,
  required fields, latency limit.
- Layer 2 (model-based): only for criteria layer 1 cannot decide;
  fixed rubric, stored rationale.
- Verdict per run: pass | fail | inconclusive.
- Inconclusive is never counted as a pass.

### EVIDENCE STORE
- Append-only.
- Per run: full transcript, verdict, timings, cost.
- Each attestation is signed and references card hash + contract version.

### POLICY ENGINE
- Applies per-risk-level thresholds to aggregated results.
- Outcome: approve | flag for human review | block.

### ADAPTERS (thin, outside the core)
- Registry: writes approval status.
- CI: returns pass/fail to the pipeline.
- Report: renders the evidence for a reviewer.

## 3. DATA MODEL

```text
agent         id, name, owner, risk_level
card_version  id, agent_id, card_hash, raw_json, fetched_at
contract      id, card_version_id, version, approved_by, approved_at
test_case     id, contract_id, skill_id, input, criteria, kind
attestation   id, contract_id, trigger, status, started_at, signature
run           id, attestation_id, test_case_id, attempt,
              verdict, latency_ms, cost, transcript_ref
decision      id, attestation_id, outcome, policy_version, decided_by
```

These seven entities are the complete list.

```text
test_case.kind:   skill | probe_undeclared | probe_injection | probe_failure
run.verdict:      pass | fail | inconclusive
decision.outcome: approve | flag | block
agent.risk_level: low | medium | high
```

policy_version identifies the version of the customer's policy
configuration (thresholds per risk level) that produced the decision.

## 4. MAIN FLOW

1. Trigger arrives (CI, schedule, or card change).
2. Fetch the card and hash it.
   New hash -> draft a contract -> wait for human approval.
3. Orchestrator enqueues the runs.
4. Runner executes each run, returns the transcript.
5. Judge scores each run, writes to the evidence store.
6. Policy engine aggregates, decides, signs the attestation.
7. Adapters push the result to registry, CI and report.

## 5. APPROVAL POLICY (DEFAULT)

```text
Risk     Example                      Approval
low      read-only lookup             automatic on pass
medium   writes to internal systems   automatic on pass, human on any drop
high     payments, personal data      human sign-off every time
```

Human is always required: first contract approval, new or changed
skills, borderline or dropping results.

Numeric pass thresholds are not defined yet. They are configured per
customer and per risk level. Treat the exact values as an open
question; do not invent numbers.

## 6. INTERFACES

```text
CLI   suncly attest <card-url> --runs 50

API   POST /attestations               start an attestation
      GET  /attestations/{id}          status and results
      POST /contracts/{id}/approve     human approval
      GET  /agents/{id}/evidence       evidence history
```

CLI and API call the same core library. Build the library first.

## 7. STACK

```text
Language   Python (most mature A2A SDK)
Storage    Postgres for tables, object storage for transcripts
Queue      Postgres-backed job table first; real queue only when needed
Signing    asymmetric signatures over the canonicalized attestation
Models     customer brings own keys; judge model pinned by version
```

## 8. NON-NEGOTIABLE RULES

- Idempotent runs: deterministic key per run, retries never double count.
- Evidence is immutable: corrections are new records.
- Secrets never leave the runner: transcripts are redacted before storage.
- Judge model is pinned: results must not drift when the judge changes.
- Budget caps live in the orchestrator: no surprise bills.
- Tests hit a sandbox or dry-run endpoint: nothing real is booked,
  paid or deleted.
- Reports state what was NOT tested.

## 9. BUILD ORDER

1. Core library: runner + deterministic judge + CLI + file report.
2. Contract builder with human approval step.
3. Postgres, evidence store, signing.
4. Model-based judge and probes.
5. API, policy engine, CI adapter.
6. Registry adapters.

Stage 1 is enough to run a first pilot by hand.

## 10. OUT OF SCOPE

Registry, gateway, identity system, monitoring platform,
universal score, payments.

## 11. ADDENDUM — RESOLVED OPEN QUESTIONS

This section overrides section 3 where they differ.

### ADDED FIELDS
```text
contract      + status, created_at
              approved_by and approved_at are null until approved
attestation   + card_version_id, budget_limit, cost_total,
                finished_at, signing_key_id
run           + judge_layer, rationale (nullable),
                started_at, finished_at
decision      + decided_at
```

### ADDED ENUMS
```text
contract.status:     draft | approved | rejected | superseded
attestation.trigger: ci | schedule | card_change | manual
attestation.status:  queued | running | completed | failed |
                     cancelled | invalidated
run.judge_layer:     deterministic | model
decision.decided_by: "policy" for automatic decisions,
                     otherwise the reviewer's identifier
```

### RULES
- Policy outcome lives in the decision entity, not in attestation.
  A flagged attestation gets a second decision record when a human
  resolves it; the first record is never edited.
- Timings: latency_ms is the agent's response time; started_at and
  finished_at cover the whole run.
- Budget: the Orchestrator stops enqueuing runs when cost_total
  reaches budget_limit. The attestation ends as "failed" and no
  decision is made.
- Card changed mid-run: the Orchestrator re-fetches and hashes the
  card when all runs finish. If the hash differs from
  card_version.card_hash, the attestation becomes "invalidated",
  no decision is made, and a new draft contract is created.
- Signature: covers the canonicalized JSON of attestation id,
  card_hash, contract id and version, per-test-case aggregated
  results, the hash of every run transcript, the decision outcome
  and policy_version. Signed with the key of the Suncly deployment
  that ran it, identified by signing_key_id.

## 12. ADDENDUM — HOSTED PRODUCT (2026-10-05)

This section adds the commercial application layer around the seven
entities. It changes nothing in sections 1 to 11: the attestation core
stays the same library the CLI runs, and the application layer calls it.

### LAYERS
```text
attestation core   domain, ports, core, runner, report adapters.
                   Seven entities in Postgres schema "public".
                   No tenant, no money, no identity.
application layer  schema "suncly_app": organization, membership,
                   agent_registration, attestation_meta, policy_record,
                   decision_note, job, job_attempt, outbox, reservation,
                   usage_event, spending_limit, subscription,
                   provider_event, meter_report, signing_key,
                   external_artifact, reevaluation_schedule,
                   schema_migration.
processes          API (FastAPI), worker (Runner boundary, Judge,
                   Policy, signer, ledger), dispatcher (recovery,
                   schedules, outbox, meter), migrate.
```

### IDENTITY AND TENANCY
- Every request carries a bearer token verified against the configured
  OpenID Connect issuer (signature, issuer, audience, expiry). A local
  HS256 verifier exists for development and tests and refuses to start in
  production.
- The organization comes from the URL, the principal from the token; a
  request body never names either. A non-member sees "not found", never
  "forbidden".
- Roles: administrator ⊃ reviewer ⊃ viewer. Reviewers register agents,
  draft and approve contracts, start and cancel attestations and resolve
  flags. Administrators also manage members, policies, limits, billing,
  schedules and keys.

### JOBS
- An attestation is a job with a stable logical id (the attestation id)
  and numbered execution attempts. Workers claim atomically under the
  tenant's concurrency limit, hold a lease, heartbeat, persist progress
  after every run, and finish or fail the attempt. An expired lease is
  recovered: the attempt is marked lost and the job requeued with
  backoff, up to max_attempts.
- Delivery is at least once. Evidence and ledger lines are keyed by run,
  so a resumed execution records nothing twice. A run whose outcome is
  unknown (the Runner died after sending) is repeated only when the
  registration declares the sandbox idempotent; otherwise it is reported
  as unknown and the reservation stays held for a person to reconcile.
- Cancellation is a request on the job that the worker sees at its next
  heartbeat; runs not started are reported as cancelled; no decision is
  made.

### TESTS, JUDGE, POLICY
- Result categories: protocol, semantic, security, operational.
- Behavioural suite format "suncly-behavioral-suite/2": reference
  examples, deterministic assertions, rubrics (versioned statements),
  negative cases, acknowledged coverage gaps, optional sandbox-state
  verification. Compiled into format-2 criteria. A model may draft a
  suite; a human approves it before anything runs.
- Judge Layer 2 is a model behind a port with pinned configuration and
  structured output. Model identity, parameters, usage and rationale are
  recorded on the run. A model failure is "inconclusive". The judge holds
  no tool and no agent credential.
- Policy: a versioned customer configuration per risk level (thresholds,
  required categories, inconclusive handling, regression and freshness
  rules). Without a policy the only outcome is flag. High-risk agents are
  never approved automatically; that setting cannot be turned off. A
  human resolution is a second decision plus an append-only note.
- External tools (A2A TCK, Promptfoo pack) contribute normalized checks
  and kept artifacts; a failed or undecided external check can only flag.

### SIGNED PAYLOAD VERSION 2
```text
payload_version, issuer, attestation_id, card_hash,
contract {id, version, content_hash}, policy {version, content_hash},
versions {suite, judge, rubrics}, results, transcript_hashes,
artifact_hashes, environment, deployment_identity, issued_at,
expires_at, decision {outcome, policy_version, decided_by, reviewer}
```
- Verification is layered and each layer is reported separately:
  cryptographic validity, issuer trust (a registry of keys with
  revocation), freshness (expiry), policy acceptability. A valid
  signature never implies approval. Version 1 payloads still verify.
- The CI gate answers three questions separately: did the attestation
  complete, does it verify, does its latest decision approve.

### MONEY
- The ledger is append-only, in integer minor units of one currency.
  Reservations are taken under a hard spending limit before a job starts,
  settled from the ledger lines when it ends, released when it is
  cancelled before running, and held for reconciliation when an outcome
  is unknown.
- Plans carry an included allowance; usage beyond it is overage reported
  once per ledger line to the billing provider's meter. The provider
  adapter runs in test mode; it refuses live keys unless told otherwise.
  Webhooks are verified, recorded once, and applied in event order.

### RULES (ADDED)
- The API process holds no Runner, no agent credential, no signing key.
- Only the worker resolves agent credentials, and only into the Runner
  child process (stdin) or an external tool's process (one variable).
- A worker whose lease is gone finalizes nothing.
- Nothing in this addendum counts an inconclusive run or an undecided
  check as a pass.
