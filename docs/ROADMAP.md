# Roadmap

Suncly is built in the six stages of schema §9. "Stage 1 is enough to run a
first pilot by hand" (schema §9). The CLI and the API call the same core
library, which is built first (schema §6).

**Status:** pre-prototype. No stage has started. This repository contains the
architecture documentation and an empty package skeleton.

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md), **Proposed** marks what the schema does not
define, and `OQ-…` marks open questions. A stage is done when every item in
its definition of done is true.

| Stage | Scope (schema §9) |
|---|---|
| 1 | Core library: runner + deterministic judge + CLI + file report. |
| 2 | Contract builder with human approval step. |
| 3 | Postgres, evidence store, signing. |
| 4 | Model-based judge and probes. |
| 5 | API, policy engine, CI adapter. |
| 6 | Registry adapters. |

The Orchestrator is not assigned to any stage ([OQ-R1](#open-questions)).

## Stage 1: Core library

**Scope:** the Runner, Layer 1 of the Judge, the CLI
`suncly attest <card-url> --runs 50`, and the file report. **Proposed:** the
file report is the first version of the Report adapter
([OQ-R6](#open-questions)).

**Definition of done**

- [ ] `suncly attest <card-url> --runs <n>` fetches the Agent Card from
      `<card-url>`, canonicalizes it and computes `card_hash`.
- [ ] The CLI holds no logic of its own. It calls the core library
      (schema §6).
- [ ] The Runner runs in its own process or container, with network access
      limited to the target (schema §2).
- [ ] The Runner works as an A2A client. It sends each test case's input as a
      Message, follows the Task to a terminal state, and captures every
      message, including a direct Message reply when the agent sends one
      instead of a Task. Which protocol versions and bindings it supports is
      open ([OQ-A4](ARCHITECTURE.md#open-questions)).
- [ ] The Runner calls only a sandbox or dry-run endpoint
      ([DR-006](DECISIONS.md#dr-006-tests-hit-a-sandbox-or-dry-run-endpoint)).
- [ ] Transcripts are redacted inside the Runner before they are returned
      ([DR-003](DECISIONS.md#dr-003-secrets-never-leave-the-runner)).
- [ ] Every run has a deterministic run key. Re-running a crashed or retried
      run never produces a second counted result
      ([DR-001](DECISIONS.md#dr-001-idempotent-runs)).
- [ ] Layer 1 of the Judge checks valid schema, final task state, required
      fields and the latency limit. It assigns `pass`, `fail` or
      `inconclusive`, and `inconclusive` is never counted as a pass.
- [ ] The file report shows the verdict counts for each test case and states
      what was NOT tested
      ([DR-007](DECISIONS.md#dr-007-reports-state-what-was-not-tested)).
- [ ] A person can run a pilot attestation by hand, from start to finish
      (schema §9).

**Not in this stage:** the Contract builder, Postgres, signing, Layer 2 and
the Policy engine. Stage 1 results are not signed and get no decision.

**Open:** [OQ-R1](#open-questions) (repetitions, and the non-negotiable budget
cap of [DR-005](DECISIONS.md#dr-005-budget-caps-live-in-the-orchestrator),
without an Orchestrator), [OQ-R2](#open-questions) (where test cases come from),
[OQ-P4](API.md#open-questions) (credentials), and A2A-T7, whether the Python
SDK supports protocol 1.0
([ARCHITECTURE.md](ARCHITECTURE.md#protocol-details-still-to-verify)).

## Stage 2: Contract builder with human approval

**Scope:** the Contract builder, including the human approval step.

**Definition of done**

- [ ] A card with a new `card_hash` gets a new `card_version` with
      `raw_json`, `card_hash` and `fetched_at`.
- [ ] A model drafts a `contract` with `status` `draft` and at least one
      `test_case` per declared skill, where `skill_id` is the skill's
      `AgentSkill.id`.
- [ ] Drafting uses the customer's own model keys (schema §7;
      [OQ-A1](ARCHITECTURE.md#open-questions)).
- [ ] Nothing runs against a contract until a human approves it. Approval sets
      `status` to `approved` and fills in `approved_by` and `approved_at`.
- [ ] An approved contract and its test cases cannot be changed. An edit
      creates a new contract version.
- [ ] A rejected draft gets `status` `rejected` and is never run.
- [ ] The CLI runs only approved contracts.

**Open:** [OQ-R3](#open-questions) (the approval interface and storage before
stages 3 and 5), [OQ-D5](DATA_MODEL.md#open-questions) (contract lifecycle),
[OQ-D7](DATA_MODEL.md#open-questions) (test case formats),
[OQ-P2](API.md#open-questions) (no interface yet for rejecting a contract), and
[OQ-A1](ARCHITECTURE.md#open-questions) (model keys).

## Stage 3: Postgres, Evidence store, signing

**Scope:** Postgres storage, the Evidence store, and attestation signing.

**Definition of done**

- [ ] The seven entities exist in Postgres with the fields, keys and enum
      values in [DATA_MODEL.md](DATA_MODEL.md).
- [ ] Transcripts are stored in object storage and referenced by
      `run.transcript_ref`.
- [ ] The Evidence store is append-only. `run` and `decision` records cannot
      be updated or deleted, and corrections are new records
      ([DR-002](DECISIONS.md#dr-002-evidence-is-immutable)).
- [ ] **Proposed**, to implement
      [DR-001](DECISIONS.md#dr-001-idempotent-runs): a second record with an
      existing run key is rejected.
- [ ] Attestations are signed with an asymmetric key of the Suncly deployment,
      over the canonicalized payload in schema §11. For the decision fields,
      see [OQ-R4](#open-questions). `signing_key_id` identifies the key, and
      the signature can be checked with the matching public key.

**Open:** [OQ-R4](#open-questions) (the payload includes a decision that
stage 3 cannot make yet), [OQ-D6](DATA_MODEL.md#open-questions),
[OQ-D8](DATA_MODEL.md#open-questions) and
[OQ-A8](ARCHITECTURE.md#open-questions).

## Stage 4: Model-based judge and probes

**Scope:** Layer 2 of the Judge, and probe test cases.

**Definition of done**

- [ ] Layer 2 judges only criteria that Layer 1 cannot decide, with a fixed
      rubric and a model pinned by version. Its rationale is stored on the
      run, and `judge_layer` is `model`.
- [ ] Changing the judge model or the rubric takes an explicit configuration
      change ([DR-004](DECISIONS.md#dr-004-judge-model-is-pinned)).
- [ ] A Layer 2 failure never produces `pass`.
- [ ] The Contract builder drafts probes with `kind` `probe_undeclared`,
      `probe_injection` and `probe_failure`. They go through the same human
      approval as skill test cases.
- [ ] Probes run only against the sandbox or dry-run endpoint
      ([DR-006](DECISIONS.md#dr-006-tests-hit-a-sandbox-or-dry-run-endpoint)).
- [ ] Model calls use the customer's own keys (schema §7).

**Open:** [OQ-A1](ARCHITECTURE.md#open-questions),
[OQ-D4](DATA_MODEL.md#open-questions),
[OQ-D7](DATA_MODEL.md#open-questions) and
[OQ-PO6](POLICY.md#open-questions).

## Stage 5: API, Policy engine, CI adapter

**Scope:** the four HTTP endpoints, the Policy engine and the CI adapter.

**Definition of done**

- [ ] The four endpoints in [API.md](API.md) work and call the same core
      library as the CLI (schema §6).
- [ ] The Policy engine applies the customer's per-risk-level thresholds to
      aggregated results. It writes a `decision` with `outcome` `approve`,
      `flag` or `block`, plus `policy_version`, `decided_by` `"policy"` and
      `decided_at`.
- [ ] It follows [POLICY.md](POLICY.md): it never approves a `high` risk agent
      automatically, it flags borderline and dropping results, and it never
      counts `inconclusive` as a pass.
- [ ] No decision is made for an attestation that is `failed` or
      `invalidated` (schema §11).
- [ ] A human resolution of a `flag` is stored as a second `decision`, and the
      first is never edited (schema §11).
- [ ] No numeric threshold is built into the code. Thresholds come from the
      customer's configuration (schema §5).
- [ ] The CI adapter returns pass or fail to the pipeline.

**Open:** [OQ-P1](API.md#open-questions), [OQ-P2](API.md#open-questions),
[OQ-P3](API.md#open-questions), [OQ-PO1](POLICY.md#open-questions) to
[OQ-PO7](POLICY.md#open-questions), and
[OQ-A9](ARCHITECTURE.md#open-questions).

## Stage 6: Registry adapters

**Scope:** adapters that write approval status into companies' agent
registries.

**Definition of done**

- [ ] Each Registry adapter in scope writes the approval status, derived from
      decisions, to its registry.
- [ ] Adapters stay thin and outside the core, with no decision logic of
      their own (schema §2).
- [ ] Suncly does not become a registry (schema §10).

**Open:** [OQ-A9](ARCHITECTURE.md#open-questions) and
[OQ-R5](#open-questions).

## Not on the roadmap

These are out of scope (schema §10): registry, gateway, identity system,
monitoring platform, universal score, payments. What that means for each
component is in
[ARCHITECTURE.md: Out of scope](ARCHITECTURE.md#out-of-scope).

## Open questions

- **OQ-R1 The Orchestrator has no stage.** Schema §9 never assigns the
  Orchestrator to a stage. But stage 1's repeated runs (`--runs`) already need
  the repetitions, timeouts and retries that schema §2 gives the
  Orchestrator, and the budget cap that schema §8 places there. The Postgres-backed job table cannot exist before stage 3.
  **Proposed:** a minimal Orchestrator inside the process in stage 1, and the
  job table in stage 3.
- **OQ-R2 Stage 1 test cases.** The Contract builder arrives in stage 2. Where
  do stage 1's test cases come from? **Proposed:** a contract file written by
  hand.
- **OQ-R3 Stages 2 to 4.** How does a human approve a contract before the API
  exists (stage 5)? And where are contracts and results stored before Postgres
  (stage 3)?
- **OQ-R4 Signing before decisions exist.** Signing arrives in stage 3, but
  the schema §11 payload includes the decision outcome and `policy_version`,
  which do not exist until the Policy engine in stage 5. What do stage 3 and 4
  signatures cover? And which component signs in those stages, given that the
  signer in schema §4, step 6 is the Policy engine?
- **OQ-R5 Which registries.** Schema §9 says "Registry adapters", plural.
  Which registry products does stage 6 target?
- **OQ-R6 The stage 1 file report.** Schema §9 lists the file report under the
  core library, while schema §2 places adapters outside the core. Is the file
  report the first version of the Report adapter (this document's reading),
  or part of the core library?
