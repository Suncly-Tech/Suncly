# Architecture

Suncly proves that an A2A agent does what its Agent Card claims. This document
expands the architecture schema in [SCHEMA.md](../SCHEMA.md) component by
component.

**Source of truth.** [SCHEMA.md](../SCHEMA.md) wins over this document. Schema
§11 overrides schema §3 where they differ. Anything this document says that the
schema does not is either derived directly from a schema rule or marked
**Proposed**.

**Conventions used in all documents**

- "schema §N" means section N of [SCHEMA.md](../SCHEMA.md).
- "A2A §N" means section N of the A2A specification v1.0.1. See
  [A2A protocol dependencies](#a2a-protocol-dependencies).
- **Proposed** marks behaviour the schema does not define. Every proposal is
  tracked as an open question: either one of its own, or as an entry in the
  list of fail-safe defaults ([OQ-A11](#open-questions)).
- `OQ-…` identifiers are open questions. Each one is listed in the document
  that owns it: OQ-A here, OQ-D in [DATA_MODEL.md](DATA_MODEL.md), OQ-F in
  [FLOW.md](FLOW.md), OQ-P in [API.md](API.md), OQ-PO in
  [POLICY.md](POLICY.md), OQ-R in [ROADMAP.md](ROADMAP.md).
- `TODO: verify against spec` marks a protocol detail that could not be
  confirmed. These are listed under [A2A protocol dependencies](#a2a-protocol-dependencies).
- Entity, field and enum names are written exactly as in the schema, in code
  font: `attestation.status`, `inconclusive`.

## System layout

The layout from schema §1:

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

- **Inputs.** The Agent Card, and a trigger (`attestation.trigger`: `ci`,
  `schedule`, `card_change` or `manual`). An Agent Card is normally published
  at `https://{server_domain}/.well-known/agent-card.json` (A2A §8.2).
- **Suncly core.** The Contract builder, Orchestrator, Runner, Judge, Evidence
  store and Policy engine.
- **Agent endpoint.** Only the Runner talks to it.
- **Outputs.** Thin adapters outside the core turn results into a registry
  status, a CI gate and an evidence report.
- **Interfaces.** The CLI and the HTTP API call the same core library
  (schema §6). See [API.md](API.md).

The end-to-end sequence is in [FLOW.md](FLOW.md), the entities in
[DATA_MODEL.md](DATA_MODEL.md), and the approval rules in
[POLICY.md](POLICY.md).

## Components

Each component is described by its responsibility, inputs, outputs, what it
must never do, and how it fails safely. "Fails safely" means that a fault can
make Suncly approve less, never more.

### Contract builder

**Responsibility** (schema §2)

- Turns an Agent Card into a versioned `contract` with one or more `test_case`
  records per declared skill.
- A model drafts the test cases; a human approves them.
- Approved contracts are immutable. Any edit creates a new contract version.
- From stage 4 it also drafts probes. This is derived: probes are `test_case`
  records with `kind` `probe_undeclared`, `probe_injection` or `probe_failure`,
  and test cases belong to contracts.

**Inputs**

- The Agent Card JSON, stored exactly as fetched (`card_version.raw_json`),
  then canonicalized and hashed (`card_version.card_hash`).
- Access to a drafting model. Customers bring their own model keys (schema §7);
  see [OQ-A1](#open-questions).
- A human approval, recorded as `approved_by` and `approved_at`.

**Outputs**

- A `contract` with `status` `draft`. After human review it becomes `approved`
  or `rejected`; an approved contract can later become `superseded`
  ([OQ-D5](DATA_MODEL.md#open-questions)).
- The contract's `test_case` records: `skill_id`, `input`, `criteria`, `kind`.

**Must never**

- Mark a contract `approved` without a human approval.
- Change an approved contract or its test cases. An edit creates a new version.
- Leave a declared skill without at least one test case.
- Call the agent endpoint, or hold credentials for the agent under test. Only
  the Runner does that (schema §2). Whether the customer's model keys count as
  customer credentials is open ([OQ-A1](#open-questions)).

**Fails safely**

- If drafting fails or the model is unavailable, no contract is approved, and
  without an approved contract nothing runs (schema §4, step 2).
- **Proposed:** if the card cannot be parsed or canonicalized, no
  `card_version` or `contract` is created and the trigger fails visibly
  ([OQ-A11](#open-questions)).
- **Proposed:** if the card declares no skills, no contract is drafted and the
  card is reported as not attestable ([OQ-A11](#open-questions)). A2A §5.7
  appears to require a non-empty `skills` array, but the spec contradicts
  itself on this (TODO: verify against spec, A2A-T5).

### Orchestrator

**Responsibility** (schema §2, §4, §7, §11)

- Expands an approved contract into runs: every test case times the number of
  repetitions.
- Owns concurrency limits, retries, timeouts and the cost budget per
  attestation.
- Runs stateless workers that pull from a queue and scale horizontally. The
  queue starts as a D1-backed job table; a real queue is added only when
  needed (schema §7).
- Tracks `attestation.cost_total` against `attestation.budget_limit` and stops
  enqueuing runs when `cost_total` reaches `budget_limit`. The attestation then
  ends as `failed` and no decision is made (schema §11).
- When all runs finish, re-fetches and re-hashes the Agent Card. If the hash
  differs from `card_version.card_hash`, the attestation becomes
  `invalidated`, no decision is made, and a new draft contract is created
  (schema §11).
- **Proposed:** also performs the initial card fetch and hash, and creates the
  `attestation` record. Schema §4, step 2 does not name a component for this
  (OQ-A7).

**Inputs**

- A trigger, and an approved contract with its test cases.
- The number of repetitions per test case (the CLI's `--runs`;
  [OQ-P5](API.md#open-questions)).
- `budget_limit`. Where it comes from for CLI, `schedule` and `card_change`
  attestations is open ([OQ-D2](DATA_MODEL.md#open-questions),
  [OQ-P5](API.md#open-questions)).
- The Agent Card URL, which the data model does not store
  ([OQ-D2](DATA_MODEL.md#open-questions)).
- The cost of every attempt, including retried attempts
  ([OQ-D1](DATA_MODEL.md#open-questions)).

**Outputs**

- Runs on the queue for the Runner.
- **Proposed:** new `card_version` records and the `attestation` record
  ([OQ-A7](#open-questions)).
- Changes to `attestation.status` (`queued`, `running`, `failed`,
  `invalidated`) and to `cost_total`.
- A request to the Contract builder for a new draft contract when the card has
  changed.

**Must never**

- Start runs for a contract that is not `approved`.
- Enqueue a run once `cost_total` has reached `budget_limit` (schema §8,
  §11).
- Count a run twice. Every run has a deterministic run key and retries reuse it
  ([DR-001](DECISIONS.md#dr-001-idempotent-runs)).
- Keep attestation state only in a worker's memory. Workers are stateless
  (schema §2).
- Call the agent endpoint, or hold credentials for the agent under test.

**Fails safely**

- If a worker crashes, its run returns to the queue and is retried under the
  same run key, so it is counted at most once.
- If the budget is reached, the attestation ends as `failed` and no decision is
  made (schema §11). Runs already in flight are an open question
  ([OQ-F4](FLOW.md#open-questions)).
- If the card has changed, the attestation becomes `invalidated` and no
  decision is made (schema §11).
- **Proposed:** if the card cannot be re-fetched at the end, the attestation
  makes no decision, because the card cannot be confirmed unchanged
  ([OQ-F5](FLOW.md#open-questions)).

### Runner

**Responsibility** (schema §2, §8)

- The only component that holds customer credentials and calls the agent.
- Acts as an A2A client. It sends the task, follows task state to the end and
  captures every message. In A2A terms:
  - The client sends a Message (for example with `SendMessage`). The agent
    creates the Task and generates its id.
  - "The end" is a terminal Task state: `TASK_STATE_COMPLETED`,
    `TASK_STATE_FAILED`, `TASK_STATE_CANCELED` or `TASK_STATE_REJECTED`.
  - The agent may answer with a Message instead of a Task (A2A §3.1.1). Then
    there is no task state to follow ([OQ-A4](#open-questions)).
  - The Runner records what it receives directly. It does not rely on
    `Task.history`, because not every Message is guaranteed to be kept there
    (A2A §3.7).
- Removes secrets from the transcript before the transcript leaves the Runner
  (schema §8).
- Runs in its own process or container, with network access limited to the
  target (schema §2).
- Targets only a sandbox or dry-run endpoint, so that nothing real is booked,
  paid or deleted (schema §8; [OQ-A2](#open-questions)).
- Is designed so that it can later run inside the customer's network
  (schema §2). This is why its inputs are limited to what one run needs (the
  run, the agent interface and credentials), and its only outputs are redacted
  transcripts and measurements.
- When it uses the agent's own Agent Card, it picks the first entry in
  `supportedInterfaces` that it supports (A2A §8.3.2). Which bindings and
  protocol versions it supports is open ([OQ-A4](#open-questions)), and so is
  which card and endpoint serve as the sandbox ([OQ-A2](#open-questions)). It
  sends the `A2A-Version` service parameter (A2A §3.6).

**Inputs**

- One run: the test case's `input` and the run key.
- The agent interface from the Agent Card.
- Customer credentials ([OQ-P4](API.md#open-questions)).
- Timeouts from the Orchestrator.

**Outputs** (to the Judge)

- The redacted transcript.
- `latency_ms`, `started_at`, `finished_at` and `cost`
  ([OQ-D1](DATA_MODEL.md#open-questions),
  [OQ-D10](DATA_MODEL.md#open-questions)).

**Must never**

- Let a secret leave the Runner, whether in a transcript, a log or an error
  message (schema §8).
- Call anything other than the target (schema §2).
- Call a production endpoint. It calls only a sandbox or dry-run endpoint
  (schema §8).
- Judge results or write evidence. The Judge does that (schema §4, step 5).
- **Proposed:** answer an interrupted state (`TASK_STATE_INPUT_REQUIRED`,
  `TASK_STATE_AUTH_REQUIRED`) with input that the test case does not contain
  ([OQ-A4](#open-questions)).

**Fails safely**

- **Proposed:** if the agent is unreachable or a timeout expires, the Runner
  returns a transcript that records the failure, and the run can never be
  judged a pass ([FLOW.md: Agent unreachable](FLOW.md#agent-unreachable)).
- **Proposed:** on an interrupted state, the Runner stops and records the
  state; the Judge applies the criteria ([OQ-A4](#open-questions)).
- **Proposed:** if redaction fails, the transcript is withheld and the run is
  not recorded, so it counts as not executed ([OQ-A11](#open-questions)).
- If the Runner crashes there is no transcript, and the Orchestrator retries
  under the same run key.

### Judge

**Responsibility** (schema §2, §4, §7, §8)

- **Layer 1 (deterministic)** checks valid schema, final task state, required
  fields and the latency limit.
  - A final task state is one of the four terminal states listed under Runner.
    The interrupted states are not final. The spec does not classify
    `TASK_STATE_UNSPECIFIED`; **Proposed:** it is not final
    ([OQ-A11](#open-questions)).
  - What "valid schema" is validated against is an open question
    ([OQ-A6](#open-questions)).
  - The latency limit is a judged criterion. It is separate from the
    Orchestrator's timeouts, which stop a run. **Proposed:** a timeout is never
    shorter than the latency limit, so a run stopped by a timeout fails the
    latency check ([OQ-F3](FLOW.md#open-questions)).
- **Layer 2 (model-based)** is used only for criteria that Layer 1 cannot
  decide. It uses a fixed rubric, stores its rationale, and the model is pinned
  by version.
- Gives each run a verdict: `pass`, `fail` or `inconclusive`. An
  `inconclusive` verdict is never counted as a pass.
- Writes each run to the Evidence store (schema §4, step 5). `judge_layer`
  records the layer that decided the verdict
  ([OQ-D4](DATA_MODEL.md#open-questions)).

**Inputs**

- From the Runner: the redacted transcript, `latency_ms`, timings and `cost`.
- The test case's `criteria` and `kind`.
- For Layer 2: the fixed rubric and the pinned model.

**Outputs**

- A `run` record: `verdict`, `judge_layer`, `rationale` (required when
  `judge_layer` is `model`), `latency_ms`, `cost`, `transcript_ref`,
  `started_at`, `finished_at` and `attempt`.

**Must never**

- Count `inconclusive` as a pass.
- Use Layer 2 for a criterion that Layer 1 can decide.
- Use a model or rubric other than the pinned ones (schema §8,
  [DR-004](DECISIONS.md#dr-004-judge-model-is-pinned)).
- Store a model verdict without its rationale.
- Change an existing run record. Corrections are new records (schema §8).
- Call the agent.

**Fails safely**

- A response that fails a Layer 1 check is a `fail`. That is the check working
  as intended.
- **Proposed:** if the Layer 2 model is unavailable, returns an error or gives
  an unusable answer, the verdict is `inconclusive`, with `judge_layer`
  `model` and a `rationale` saying that no model verdict was available
  ([OQ-D4](DATA_MODEL.md#open-questions)).
- **Proposed:** if Suncly cannot read the transcript because of its own fault,
  the verdict is `inconclusive`, never `pass` ([OQ-A11](#open-questions)).

### Evidence store

**Responsibility** (schema §2, §7, §8, §11)

- An append-only store of evidence.
- Per run, it keeps the full transcript, the verdict, timings and cost. Tables
  live in Postgres and transcripts in object storage, referenced by
  `run.transcript_ref` (schema §7).
- Each attestation is signed and references the card hash and the contract
  version. The signature covers the canonicalized JSON of:
  - the attestation id
  - `card_hash`
  - the contract id and version
  - the per-test-case aggregated results
  - the hash of every run transcript
  - the decision outcome
  - `policy_version`

  It is signed with the key of the Suncly deployment that ran the attestation,
  identified by `signing_key_id` (schema §11; [OQ-A8](#open-questions)). What
  the signature covers for an attestation without a decision is open
  ([OQ-F7](FLOW.md#open-questions)).
- Corrections are new records (schema §8).

**Inputs**

- Run records from the Judge.
- Decisions and signatures from the Policy engine.
- **Proposed:** the `attestation` record from the Orchestrator
  ([OQ-A7](#open-questions)).

Card versions, contracts and test cases live in the same database but are not
run evidence. [DATA_MODEL.md: Mutability](DATA_MODEL.md#mutability) shows which
component writes each entity.

**Outputs**

- Run records (verdicts, costs, transcript references) for the Policy engine,
  which aggregates them (schema §4, step 6).
- Evidence for the Report adapter and for the API
  (`GET /attestations/{id}`, `GET /agents/{id}/evidence`).

**Must never**

- Update or delete a `run` or `decision` record (schema §2, §8, §11).
- Store unredacted secrets. It only receives transcripts that the Runner has
  already redacted (schema §8).
- **Proposed:** accept a second run record with an existing run key
  ([DR-001](DECISIONS.md#dr-001-idempotent-runs)).

**Fails safely**

- **Proposed:** if a write fails, the run is not recorded and counts as not
  executed, never as a pass. The Orchestrator may retry it under the same run
  key ([OQ-A11](#open-questions)).
- **Proposed:** if the transcript cannot be written to object storage, the run
  record is not written either, because a run record must point to its
  transcript ([OQ-A11](#open-questions)).
- Because records cannot be rewritten, a fault cannot silently change past
  evidence. Corrections appear as new records.

### Policy engine

**Responsibility** (schema §2, §4, §5, §11)

- Aggregates the attestation's run results per test case (schema §4, step 6)
  and applies the per-risk-level thresholds. The thresholds come from the
  customer's policy configuration, identified by `policy_version`.
- Produces a decision outcome: `approve`, `flag` or `block`. Schema §2 calls
  `flag` "flag for human review" ([OQ-A10](#open-questions)).
- Writes the `decision` record, with `decided_by` set to `"policy"` and a
  `decided_at` timestamp.
- Signs the attestation (schema §4, step 6), using the payload defined in
  schema §11.
- Applies the approval rules in [POLICY.md](POLICY.md).
- Makes no decision for an attestation that ended `failed` or `invalidated`
  (schema §11).

**Inputs**

- The attestation's run records from the Evidence store.
- `agent.risk_level`.
- The customer's policy configuration (`policy_version`).
- The deployment's signing key.

**Outputs**

- A `decision` record.
- `attestation.signature` and `signing_key_id`.
- **Proposed:** `attestation.status` set to `completed`, and `finished_at`,
  once the decision is recorded and the attestation signed
  ([OQ-D6](DATA_MODEL.md#open-questions)).
- The result for the adapters.

**Must never**

- Count `inconclusive` as a pass.
- Approve automatically when a human is required: every time for high risk,
  and whenever results are borderline or dropping (schema §5).
- Edit an existing decision. A human resolution is a second decision record
  (schema §11).
- Make a decision for an attestation that is `failed` or `invalidated`
  (schema §11).
- Use numbers it was not given. Numeric thresholds are customer configuration
  and are not defined yet ([OQ-PO1](POLICY.md#open-questions)).

**Fails safely**

- **Proposed:** if the policy configuration is missing or unreadable, the
  outcome is `flag`, never `approve`. What `policy_version` that decision
  carries is open ([OQ-PO5](POLICY.md#open-questions)).
- **Proposed:** if signing fails, the attestation is not marked `completed`,
  and the adapters do not report it as approved, even though its decision is
  already recorded ([OQ-A9](#open-questions), [OQ-A11](#open-questions)).

### Adapters

Adapters are thin and sit outside the core (schema §2). They translate core
results into other systems. They never decide anything.

#### Registry adapter

- **Responsibility:** writes approval status to the company's agent registry
  (schema §2). It is built in stage 6, which the schema calls "Registry
  adapters".
- **Inputs:** the decisions for an attestation, and the agent.
- **Outputs:** the approval status in the registry.
- **Must never:** decide on its own, or turn Suncly into a registry, which is
  out of scope (schema §10). **Proposed:** it never writes an approved status
  unless the attestation is `completed` and its latest decision is `approve`
  ([OQ-A9](#open-questions)).
- **Fails safely:** **Proposed:** if the write fails, the adapter retries and
  reports the failure, and never reports success. A failed write can leave a
  stale status in the registry, including a stale approval. How to fail closed
  in that case is open ([OQ-A9](#open-questions)).

#### CI adapter

- **Responsibility:** returns pass or fail to the pipeline (schema §2). It is
  built in stage 5.
- **Inputs:** the attestation status and its decisions.
- **Outputs:** pass or fail.
- **Must never:** **Proposed:** return pass unless the attestation is
  `completed` (decided and signed) and its latest decision is `approve`
  ([OQ-A9](#open-questions)).
- **Fails safely:** **Proposed:** the pipeline gets fail in every other case:
  a `flag` or `block` decision, an attestation that is not `completed`
  (`failed`, `invalidated`, `cancelled`, or signing failed), or no answer.

#### Report adapter

- **Responsibility:** renders the evidence for a reviewer (schema §2), and
  states what was NOT tested (schema §8,
  [DR-007](DECISIONS.md#dr-007-reports-state-what-was-not-tested)).
  **Proposed:** stage 1's "file report" is its first version
  ([OQ-R6](ROADMAP.md#open-questions)).
- **Inputs:** the attestation, its runs, decisions, card version, contract and
  test cases.
- **Outputs:** a report for a human reviewer. In stage 1 it is a file.
- **Must never:** leave out what was not tested, present `inconclusive` as a
  pass, or show secrets. Only redacted transcripts reach it.
- **Fails safely:** if evidence is missing or incomplete, the report says so
  instead of leaving a silent gap.
- **Proposed:** examples of "not tested" are runs never executed because the
  budget stopped them, `inconclusive` runs, declared capabilities that no test
  exercised (such as streaming or push notifications), protocol bindings that
  were not used, and the production endpoint itself, because tests run against
  a sandbox ([OQ-A11](#open-questions)).

## Cross-cutting rules

The non-negotiable rules from schema §8, and the components that enforce them.
Each rule is written up as a decision record in [DECISIONS.md](DECISIONS.md).

| Rule (schema §8) | Enforced by | Record |
|---|---|---|
| Idempotent runs: deterministic key per run, retries never double count. | Orchestrator, Evidence store | [DR-001](DECISIONS.md#dr-001-idempotent-runs) |
| Evidence is immutable: corrections are new records. | Evidence store, Policy engine | [DR-002](DECISIONS.md#dr-002-evidence-is-immutable) |
| Secrets never leave the runner: transcripts are redacted before storage. | Runner | [DR-003](DECISIONS.md#dr-003-secrets-never-leave-the-runner) |
| Judge model is pinned: results must not drift when the judge changes. | Judge | [DR-004](DECISIONS.md#dr-004-judge-model-is-pinned) |
| Budget caps live in the orchestrator: no surprise bills. | Orchestrator | [DR-005](DECISIONS.md#dr-005-budget-caps-live-in-the-orchestrator) |
| Tests hit a sandbox or dry-run endpoint: nothing real is booked, paid or deleted. | Runner | [DR-006](DECISIONS.md#dr-006-tests-hit-a-sandbox-or-dry-run-endpoint) |
| Reports state what was NOT tested. | Report adapter | [DR-007](DECISIONS.md#dr-007-reports-state-what-was-not-tested) |

## Stack

From schema §7:

| Concern | Choice |
|---|---|
| Language | Python. The schema's reason is that it has the most mature A2A SDK. Whether that SDK supports A2A protocol version 1.0 is unconfirmed (TODO: verify SDK support, A2A-T7). |
| Storage | Cloudflare D1 for tables, R2 object storage for transcripts. |
| Queue | A D1-backed job table first; a real queue only when needed ([OQ-D8](DATA_MODEL.md#open-questions)). |
| Signing | Asymmetric signatures over the canonicalized attestation. |
| Models | Customers bring their own keys. The judge model is pinned by version. |

## Interfaces

The CLI command `suncly attest <card-url> --runs 50` and four HTTP endpoints.
Both call the same core library, and the library is built first (schema §6).
Details and examples are in [API.md](API.md).

## A2A protocol dependencies

These protocol facts were checked on 2026-10-03 against the
**A2A specification v1.0.1**, the latest release (GitHub release of
2026-05-28). Its protocol version is `1.0`, because A2A identifies protocol
versions as Major.Minor (A2A §3.6). The normative data model is `a2a.proto`
(A2A §1.4). Sources:

- [A2A specification v1.0.1](https://a2a-protocol.org/v1.0.1/specification/)
- [specification.md at tag v1.0.1](https://github.com/a2aproject/A2A/blob/v1.0.1/docs/specification.md)
- [a2a.proto at tag v1.0.1](https://github.com/a2aproject/A2A/blob/v1.0.1/specification/a2a.proto)

`https://a2a-protocol.org/latest/specification/` is built from the unreleased
main branch, so cite the versioned pages instead.

| Topic | What the specification says | Where Suncly depends on it |
|---|---|---|
| Discovery | Agent Cards are published at `https://{server_domain}/.well-known/agent-card.json` (A2A §8.2). | `<card-url>` in the CLI |
| Agent Card | Has exactly 14 fields: `name`, `description`, `supportedInterfaces`, `provider`, `version`, `documentationUrl`, `capabilities`, `securitySchemes`, `securityRequirements`, `defaultInputModes`, `defaultOutputModes`, `skills`, `signatures`, `iconUrl` (A2A §4.4.1). There is no top-level `url` or `protocolVersion`. The spec's prose calls one of these fields by another name (A2A-T4). | `card_version.raw_json`, `card_hash`, Contract builder |
| Skills | `AgentSkill` has `id`, `name`, `description` and `tags` (required), and `examples`, `inputModes`, `outputModes` and `securityRequirements` (optional) (A2A §4.4.5). Skills declare no input or output schema; descriptions and examples are free text. | Drafting test cases, `test_case.skill_id`, human approval of contracts |
| Interfaces | `supportedInterfaces` is ordered, with the first entry preferred. Each `AgentInterface` has `url`, `protocolBinding` (core values `JSONRPC`, `GRPC`, `HTTP+JSON`), `protocolVersion` and an optional `tenant`. Clients pick the first entry they support (A2A §8.3.2). | Runner |
| Operations | `SendMessage`, `SendStreamingMessage`, `GetTask`, `ListTasks`, `CancelTask`, `SubscribeToTask`, four push-notification config operations, and `GetExtendedAgentCard`. In JSON-RPC the method names are these PascalCase names (A2A §9.1); v0.3 used names like `message/send`. | Runner |
| Replies | A reply to `SendMessage` is either a Task or a Message (A2A §3.1.1). Task ids are generated by the agent; a client cannot create one. | Runner, Judge |
| Task states | Terminal: `TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`, `TASK_STATE_CANCELED`, `TASK_STATE_REJECTED`. Interrupted: `TASK_STATE_INPUT_REQUIRED`, `TASK_STATE_AUTH_REQUIRED`. Also `TASK_STATE_SUBMITTED` and `TASK_STATE_WORKING`, and `TASK_STATE_UNSPECIFIED`, which the spec does not classify. JSON uses these names as strings (A2A §5.5); v0.3 used lowercase strings such as `completed`. | Judge Layer 1 ("final task state") |
| Message history | Not every Message is guaranteed to be kept in `Task.history` (A2A §3.7). | The Runner captures messages directly |
| Versioning | Clients MUST send `A2A-Version`. An empty value means version 0.3 (A2A §3.6). | Runner |
| Card signatures | Cards MAY carry JSON Web Signatures in `signatures`. Before signing, the card is canonicalized with RFC 8785 (JCS), and `signatures` itself is excluded (A2A §8.4, §8.4.1). A signature shows integrity and who signed the card. It says nothing about the agent's behaviour. | `card_hash` design ([OQ-A7](#open-questions)) |
| Extended card | When `capabilities.extendedAgentCard` is true, the agent offers an extended Agent Card through `GetExtendedAgentCard`, which MUST require authentication (A2A §13.3). | Card fetching ([OQ-A7](#open-questions)) |
| Attestation | We found no mechanism in the v1.0.1 specification, proto or topic documents for verifying that an agent performs its declared skills. | Suncly's purpose |

### Protocol details still to verify

The specification is unclear or contradicts itself on these points, or the
point is not a spec question at all (A2A-T7). Suncly does not take a side until
each one is checked:

- **A2A-T1** TODO: verify against spec. Requests appear to have no way to
  address a particular skill. No request message has a skill identifier, so
  routing appears to happen inside the agent, based on message content. This is
  inferred from the missing field, not stated in the spec
  ([OQ-A5](#open-questions)).
- **A2A-T2** TODO: verify against spec. Does a stream close at an interrupted
  state? A2A §3.1.2 and §3.1.6 say it closes at a terminal state, while §11.7
  says it closes at a terminal or interrupted state. This matters if the Runner
  uses streaming.
- **A2A-T3** TODO: verify against spec. Does `SendMessage` block? A2A §3.1.1
  and §3.3.3 say operations return immediately, while §3.2.2 makes blocking
  until a terminal or interrupted state the default.
- **A2A-T4** TODO: verify against spec. Is the security requirement field
  called `security` or `securityRequirements`? The prose in A2A §3.1.11 and
  §13.3 says `AgentCard.security`, but the proto and the field table say
  `securityRequirements`. Suncly reads `securityRequirements`.
- **A2A-T5** TODO: verify against spec. Can a card have an empty `skills`
  array? A2A §5.7 says required arrays must have at least one element, while
  the canonicalization example in §8.4.1 uses `"skills": []`.
- **A2A-T6** TODO: verify against spec. Which HTTP method does
  `SubscribeToTask` use? A2A §5.3 and §11.3.2 say `POST /tasks/{id}:subscribe`,
  while the proto declares `GET`. This matters only for the `HTTP+JSON`
  binding.
- **A2A-T7** TODO: verify SDK support. Does the Python A2A SDK support
  protocol version 1.0? Version 1.0 renamed methods, task states and card
  fields.

## Out of scope

From schema §10. Suncly does not build any of these:

- **Registry.** Suncly writes approval status into a company's existing
  registry through the Registry adapter. It is not a registry.
- **Gateway.** Suncly does not sit in the path of production traffic between
  agents.
- **Identity system.** Reviewer identities (`approved_by`, `decided_by`) come
  from elsewhere ([OQ-P3](API.md#open-questions)).
- **Monitoring platform.** Suncly attests when a trigger arrives. It does not
  watch agents continuously ([OQ-F2](FLOW.md#open-questions)).
- **Universal score.** The outcome is a decision under one customer's policy,
  not a score that compares agents.
- **Payments.**

## Open questions

- **OQ-A1 Model keys versus the Runner's credential rule.** Customers bring
  their own model keys (schema §7), so the Contract builder (drafting) and the
  Judge (Layer 2) would hold customer credentials. Schema §2 says the Runner is
  the only component holding customer credentials. Does that rule cover only
  credentials for the agent under test, or do model calls also have to go
  through the Runner?
- **OQ-A2 Sandbox enforcement and which card is attested.** How does Suncly
  know, or enforce, that an endpoint is a sandbox or dry-run endpoint? A2A has
  no such concept. And which Agent Card is attested: the production card, or
  the sandbox's own card? If the production card is attested, how is it
  confirmed that the sandbox runs the same agent? The card's `version` field
  is one possible signal.
- **OQ-A3 Redaction rules.** What counts as a secret? Schema §2 keeps the "full
  transcript" and schema §8 requires redaction. This document reads that as
  every message, with secrets removed. A2A payloads can carry credentials by
  design, for example the authentication in a push-notification configuration,
  or credentials exchanged while a task is in `TASK_STATE_AUTH_REQUIRED`.
- **OQ-A4 How the Runner follows a task.**
  - Which protocol bindings (`JSONRPC`, `GRPC`, `HTTP+JSON`) and protocol
    versions (only 1.0, or also 0.3) are supported?
  - Does the Runner use a blocking `SendMessage`, poll with `GetTask`, or
    stream (A2A-T2, A2A-T3)?
  - Push notifications would need the agent to call back to an inbound webhook,
    which a network-limited Runner cannot receive, and they put credentials in
    payloads. **Proposed:** the Runner does not use push notifications.
  - How are interrupted states and direct Message replies handled?
- **OQ-A5 Skill targeting.** If A2A requests carry no skill identifier
  (A2A-T1), how does a test case exercise one specific skill, and how is a
  result attributed to `test_case.skill_id`?
- **OQ-A6 What Layer 1 validates "valid schema" against.** The A2A response
  structure, an output schema in the test case's `criteria`, or both?
- **OQ-A7 Card fetching and hashing.**
  - Which component performs the initial fetch? **Proposed:** the
    Orchestrator, which already re-fetches the card under schema §11.
  - An authenticated extended card can only be fetched with credentials, which
    only the Runner may hold.
  - Which canonicalization scheme and hash algorithm produce `card_hash`?
  - Is the `signatures` field excluded from the hash? If it is not, re-signing
    an unchanged card produces a new hash, a new contract and a new human
    approval.
- **OQ-A8 Attestation signature details.**
  - Which canonicalization scheme is used?
  - How is the signature encoded in `attestation.signature`?
  - What exactly are the "per-test-case aggregated results"?
  - How do verifiers obtain and trust the public key for `signing_key_id`, and
    how are keys rotated?
  - The human decision that resolves a `flag` is not covered by any signature.
- **OQ-A9 Adapter mappings.**
  - How do decisions map to CI pass or fail, and to a registry status? This
    matters most for `flag`, and for attestations that are not `completed`.
    **Proposed:** only a `completed` attestation whose latest decision is
    `approve` produces pass or approved. The decision is written before
    signing, so a decision alone is not enough.
  - If a human later resolves a `flag`, the CI run that saw it has already
    ended.
  - If a registry write fails, the registry may keep a stale approval. How
    should the Registry adapter fail closed?
- **OQ-A10 Naming.** Schema §2 says "flag for human review" and schema §3 has
  the enum value `flag`. These documents treat them as the same thing and use
  `flag` everywhere. Please confirm.
- **OQ-A11 Fail-safe defaults.** This document proposes these fail-safe
  defaults. Each one makes Suncly approve less, never more. Please confirm
  them:
  - A card that cannot be parsed or canonicalized creates no records, and the
    trigger fails visibly.
  - A card with no skills is reported as not attestable (see also A2A-T5).
  - If redaction fails, the transcript is withheld and the run is not
    recorded.
  - `TASK_STATE_UNSPECIFIED` is not a final task state.
  - If Suncly cannot read a transcript because of its own fault, the verdict
    is `inconclusive`.
  - If an evidence write or a transcript upload fails, the run is not recorded
    and counts as not executed.
  - If signing fails, the attestation is not marked `completed` and is not
    reported as approved.
  - The examples of what a report lists as NOT tested (see Report adapter).
