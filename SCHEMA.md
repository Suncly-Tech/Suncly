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
