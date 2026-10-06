# Interfaces

Suncly has one CLI command and four HTTP endpoints (schema §6):

```text
CLI   suncly attest <card-url> --runs 50

API   POST /attestations               start an attestation
      GET  /attestations/{id}          status and results
      POST /contracts/{id}/approve     human approval
      GET  /agents/{id}/evidence       evidence history
```

The CLI and the API call the same core library, and the library is built
first (schema §6). The CLI arrives in stage 1, and the API in stage 5
([ROADMAP.md](ROADMAP.md)).

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md), **Proposed** marks what the schema does not
define, and `OQ-…` marks open questions.

## Conventions for the examples

The schema defines the commands and endpoints, but not their arguments,
bodies or status codes. Everything below beyond the command line and the paths
is **Proposed** ([OQ-P1](#open-questions)).

- Requests and responses are JSON. A field that corresponds to an entity
  field uses that field's name from [DATA_MODEL.md](DATA_MODEL.md). The request
  parameters `card_url` and `runs`, and the aggregates `results` and
  `decisions`, are proposals of this document.
- Ids are UUIDs. Timestamps are ISO 8601 in UTC. Cost fields are numbers whose
  unit is open ([OQ-D1](DATA_MODEL.md#open-questions)).
- A value in angle brackets, such as `"<card_hash>"`, is a placeholder for a
  format the schema does not define.
- All example data is fictional. Example hosts use the reserved domain
  `example.com`.
- API authentication is not defined ([OQ-P3](#open-questions)), so the
  examples leave it out.
- Credentials for the agent under test never appear in a command line, a
  request or a response
  ([DR-003](DECISIONS.md#dr-003-secrets-never-leave-the-runner),
  [OQ-P4](#open-questions)).
- Outcomes shown in the examples do not imply any numeric threshold.
  Thresholds are not defined yet ([OQ-PO1](POLICY.md#open-questions)).

## CLI

### suncly attest

```text
suncly attest <card-url> --runs 50
```

Example:

```bash
suncly attest https://agent.example.com/.well-known/agent-card.json --runs 50
```

| Argument | Meaning |
|---|---|
| `<card-url>` | The URL of the agent's Agent Card. A2A agents normally publish their card at `https://{server_domain}/.well-known/agent-card.json` (A2A §8.2). |
| `--runs` | The number of repetitions. Read as repetitions per test case ([OQ-P5](#open-questions)). 50 is the schema's example value. No default is defined. |

What it does depends on the stage:

- **This MVP.** Fetches the card, gets a contract approved (drafted or from a
  contract file), runs each test case `--runs` times against the declared
  sandbox or dry-run endpoint, judges each run with Layer 1, records a `flag`
  decision, signs the attestation, and writes a report that states what was
  NOT tested. Where the test cases come from is the OQ-R2 proposal
  ([ROADMAP.md](ROADMAP.md#open-questions)).
- **From stage 2.** Runs only an approved contract. If the card's hash is new,
  a draft contract is created and must be approved first.
- **Proposed:** an attestation started from the CLI has the trigger `manual`
  ([OQ-P5](#open-questions)).

The output is the file report. The console output format and the exit codes
are not defined ([OQ-P5](#open-questions)).

### CLI options (Proposed, OQ-P5)

The schema defines only `suncly attest <card-url> --runs 50`. The MVP adds the
options it cannot work without. All are proposals.

| Option | Meaning |
|---|---|
| `--sandbox` | Declares the endpoint a sandbox or dry-run endpoint. Required: without it nothing runs (DR-006, OQ-A2). |
| `--runs N` | Repetitions per test case. Default 5 (`SUNCLY_RUNS`). |
| `--budget N` | `attestation.budget_limit`, in attempts. Default 2 x planned runs. One attempt costs 1 (OQ-D1). |
| `--approve-as ID` | Approves the drafted contract as `ID` without a prompt; `ID` becomes `approved_by`. Without it, the CLI shows the draft and asks; with no terminal, it refuses. |
| `--contract FILE` | Uses a contract file instead of the drafter (see below). The imported contract becomes a new version and still needs approval. |
| `--export-draft FILE` | Writes the draft contract to `FILE` and stops. Nothing runs. When no declared skill has a usable example the draft is empty, and the command is refused (exit 3) with the same message as a run; write the contract file by hand in that case. |
| `--owner`, `--risk-level` | `agent.owner` and `agent.risk_level`, recorded on first sight of the card URL. Defaults: `unspecified` and `high`. |
| `--reports-dir DIR` | Where the report folder goes. Default `./suncly-reports`. |
| `--json` | Prints a machine-readable result: `kind`, `attestation`, `decision`, `results`, `not_tested`, `report_dir`, `exit_code`. |
| `--debug` | Shows tracebacks. |
| `--home DIR` (before the command) | Moves the whole state folder (store, transcripts, keys). Default `~/.suncly`. |

Other commands: `suncly demo`, `suncly verify <report-folder> [--public-key B64]`,
`suncly keys init [--new]`, `suncly db migrate`, `suncly db check`,
`suncly doctor [card-url]`.

**Exit codes (Proposed).** 0: the attestation completed, that is, it was
decided and signed; **0 never means the agent was approved**, and the output
says so. 1: internal error. 2: wrong arguments. 3: refused to start (no
sandbox declaration, no approval, unusable card or contract). 4: the
attestation ended `failed`. 5: the attestation ended `invalidated`. 6:
`suncly verify` or `suncly doctor` found a problem.

**Trigger.** An attestation started from the CLI has `trigger` `manual`, also
when CI calls the CLI.

### Contract file (Proposed, OQ-R2 and OQ-D7)

A hand-written or exported contract: one JSON document with the test cases of
one contract for one card. Field names are the data model's. The file carries
no approval fields: approval is recorded by `--approve-as` or the prompt.

```json
{
  "suncly_contract_file": 1,
  "card_hash": "sha256:…",
  "agent_name": "Order Status Agent",
  "skills_without_test_case": [],
  "test_cases": [
    {
      "skill_id": "order-status",
      "kind": "skill",
      "input": {"text": "Where is order 1234?"},
      "criteria": {
        "final_state": "TASK_STATE_COMPLETED",
        "latency_limit_ms": 10000,
        "response_present": true,
        "output_modes": ["text/plain"],
        "required_fields": ["/artifacts/0/parts/0/text"],
        "response_schema": {"type": "object", "required": ["artifacts"]},
        "model_checks": [],
        "accept_direct_message": false
      }
    }
  ]
}
```

- `card_hash` must equal the hash of the fetched card, or the file is refused.
- Every declared skill needs a test case, or must be listed under
  `skills_without_test_case` to acknowledge that it stays untested
  (invariant 1 is then reported as not satisfied for it).
- `input` is `{"text": …}` or `{"parts": [...]}` with A2A Part objects.
- `criteria` keys: `final_state` (a terminal task state, default
  `TASK_STATE_COMPLETED`); `latency_limit_ms` (required); `response_present`;
  `output_modes` (media types every output part must use; `null` disables
  the check); `required_fields` (JSON pointers that must exist and be
  non-empty in the final response); `response_schema` (a JSON Schema the
  final response must satisfy); `model_checks` (criteria for Layer 2, which
  does not exist yet, so any entry makes the run `inconclusive`);
  `accept_direct_message` (a direct Message reply counts as a completed task).
  Unknown keys are refused.

## HTTP API

### POST /attestations

Starts an attestation.

**Request** (Proposed)

```http
POST /attestations
Content-Type: application/json
```

```json
{
  "agent_id": "6f1c2d3e-4b5a-4c6d-8e7f-9a0b1c2d3e4f",
  "card_url": "https://agent.example.com/.well-known/agent-card.json",
  "runs": 50,
  "trigger": "ci",
  "budget_limit": 25.0
}
```

| Field | Meaning |
|---|---|
| `agent_id` | `agent.id`. How an agent gets registered is not defined ([OQ-P2](#open-questions)). |
| `card_url` | The API equivalent of the CLI's `<card-url>`. It is a request parameter only; the data model does not store it ([OQ-D2](DATA_MODEL.md#open-questions)). |
| `runs` | The API equivalent of `--runs` ([OQ-P5](#open-questions)). |
| `trigger` | `attestation.trigger`. **Proposed:** callers send `ci` or `manual`; `schedule` and `card_change` attestations start inside Suncly. |
| `budget_limit` | `attestation.budget_limit` ([OQ-D1](DATA_MODEL.md#open-questions)). |

**Response** (Proposed): `202 Accepted`. The attestation is created and runs
asynchronously.

```json
{
  "id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
  "contract_id": "7e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b",
  "card_version_id": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
  "trigger": "ci",
  "status": "queued",
  "started_at": "2026-10-01T09:00:00Z",
  "finished_at": null,
  "budget_limit": 25.0,
  "cost_total": 0,
  "signature": null,
  "signing_key_id": null
}
```

This example assumes the card's hash matches a card version that already has
an approved contract. If the hash is new, a draft contract is created and no
attestation exists until a human approves it ([OQ-F1](FLOW.md#open-questions),
decided 2026-10-04). The response for that case is open
([OQ-P1](#open-questions)).

### GET /attestations/{id}

Returns an attestation's status and results.

**Request**

```http
GET /attestations/3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f
```

**Response** (Proposed): `200 OK`. This is a completed attestation, as
returned before a human resolved its `flag`.

```json
{
  "id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
  "contract_id": "7e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b",
  "card_version_id": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
  "trigger": "ci",
  "status": "completed",
  "started_at": "2026-10-01T09:00:00Z",
  "finished_at": "2026-10-01T09:42:10Z",
  "budget_limit": 25.0,
  "cost_total": 3.42,
  "signature": "<signature>",
  "signing_key_id": "<signing_key_id>",
  "results": [
    {
      "test_case_id": "9b0c1d2e-3f4a-4b5c-9d6e-7f8a9b0c1d2e",
      "skill_id": "order-status",
      "kind": "skill",
      "pass": 49,
      "fail": 0,
      "inconclusive": 1
    },
    {
      "test_case_id": "2d3e4f5a-6b7c-4d8e-9f0a-1b2c3d4e5f6a",
      "skill_id": "order-status",
      "kind": "skill",
      "pass": 50,
      "fail": 0,
      "inconclusive": 0
    }
  ],
  "decisions": [
    {
      "id": "5a6b7c8d-9e0f-4a1b-8c2d-3e4f5a6b7c8d",
      "attestation_id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
      "outcome": "flag",
      "policy_version": "<policy_version>",
      "decided_by": "policy",
      "decided_at": "2026-10-01T09:42:09Z"
    }
  ]
}
```

- **`results`** are the per-test-case aggregated results named in schema §11:
  how many runs of each test case got each `run.verdict`. Their exact shape is
  open ([OQ-A8](ARCHITECTURE.md#open-questions)). `inconclusive` is reported
  separately and never counted as `pass`.
- **`decisions`** lists every `decision` record for the attestation, oldest
  first. It is empty for a `failed`, `cancelled` or `invalidated` attestation.

### POST /contracts/{id}/approve

A human approves a draft contract.

**Request** (Proposed): no body. The approver's identity comes from the
authenticated caller ([OQ-P3](#open-questions)).

```http
POST /contracts/7e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b/approve
```

**Response** (Proposed): `200 OK`.

```json
{
  "id": "7e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b",
  "card_version_id": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
  "version": 1,
  "status": "approved",
  "created_at": "2026-09-30T14:52:00Z",
  "approved_by": "reviewer@example.com",
  "approved_at": "2026-10-01T08:55:00Z"
}
```

- Only a `draft` contract can be approved. Approving never modifies an already
  approved contract, because approved contracts are immutable (schema §2). The
  error format is open ([OQ-P1](#open-questions)).
- Whether approving a new version supersedes earlier ones is open
  ([OQ-D5](DATA_MODEL.md#open-questions)).

### GET /agents/{id}/evidence

Returns an agent's evidence history.

**Request**

```http
GET /agents/6f1c2d3e-4b5a-4c6d-8e7f-9a0b1c2d3e4f/evidence
```

**Response** (Proposed): `200 OK`. The example shows two attestations, newest
first:

- the completed one above, after a reviewer resolved its `flag`;
- an earlier scheduled attestation, invalidated because the card changed
  during it.

Each `runs` array is shortened to one item.

```json
{
  "agent": {
    "id": "6f1c2d3e-4b5a-4c6d-8e7f-9a0b1c2d3e4f",
    "name": "Order Status Agent",
    "owner": "example-team",
    "risk_level": "low"
  },
  "attestations": [
    {
      "id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
      "trigger": "ci",
      "status": "completed",
      "started_at": "2026-10-01T09:00:00Z",
      "finished_at": "2026-10-01T09:42:10Z",
      "budget_limit": 25.0,
      "cost_total": 3.42,
      "signature": "<signature>",
      "signing_key_id": "<signing_key_id>",
      "card_version": {
        "id": "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
        "card_hash": "<card_hash>",
        "fetched_at": "2026-09-30T14:50:30Z"
      },
      "contract": {
        "id": "7e8f9a0b-1c2d-4e3f-9a4b-5c6d7e8f9a0b",
        "version": 1
      },
      "decisions": [
        {
          "id": "5a6b7c8d-9e0f-4a1b-8c2d-3e4f5a6b7c8d",
          "attestation_id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
          "outcome": "flag",
          "policy_version": "<policy_version>",
          "decided_by": "policy",
          "decided_at": "2026-10-01T09:42:09Z"
        },
        {
          "id": "4e5f6a7b-8c9d-4e0f-a1b2-c3d4e5f6a7b8",
          "attestation_id": "3c4d5e6f-7a8b-4c9d-8e0f-1a2b3c4d5e6f",
          "outcome": "approve",
          "policy_version": "<policy_version>",
          "decided_by": "reviewer@example.com",
          "decided_at": "2026-10-01T11:05:00Z"
        }
      ],
      "runs": [
        {
          "id": "8c9d0e1f-2a3b-4c4d-9e5f-6a7b8c9d0e1f",
          "test_case_id": "9b0c1d2e-3f4a-4b5c-9d6e-7f8a9b0c1d2e",
          "attempt": 17,
          "verdict": "inconclusive",
          "judge_layer": "model",
          "rationale": "<rationale>",
          "latency_ms": 1840,
          "cost": 0.0412,
          "transcript_ref": "<transcript_ref>",
          "started_at": "2026-10-01T09:11:02Z",
          "finished_at": "2026-10-01T09:11:05Z"
        }
      ]
    },
    {
      "id": "1f2e3d4c-5b6a-4978-8a9b-0c1d2e3f4a5b",
      "trigger": "schedule",
      "status": "invalidated",
      "started_at": "2026-09-30T14:00:00Z",
      "finished_at": "2026-09-30T14:50:30Z",
      "budget_limit": 25.0,
      "cost_total": 2.97,
      "signature": "<signature>",
      "signing_key_id": "<signing_key_id>",
      "card_version": {
        "id": "b1c2d3e4-f5a6-4b7c-8d9e-0f1a2b3c4d5e",
        "card_hash": "<card_hash>",
        "fetched_at": "2026-09-02T10:15:00Z"
      },
      "contract": {
        "id": "c2d3e4f5-a6b7-4c8d-9e0f-1a2b3c4d5e6f",
        "version": 2
      },
      "decisions": [],
      "runs": [
        {
          "id": "d3e4f5a6-b7c8-4d9e-8f0a-1b2c3d4e5f6a",
          "test_case_id": "e4f5a6b7-c8d9-4e0f-9a1b-2c3d4e5f6a7b",
          "attempt": 1,
          "verdict": "pass",
          "judge_layer": "deterministic",
          "rationale": null,
          "latency_ms": 920,
          "cost": 0.031,
          "transcript_ref": "<transcript_ref>",
          "started_at": "2026-09-30T14:00:04Z",
          "finished_at": "2026-09-30T14:00:06Z"
        }
      ]
    }
  ]
}
```

- **Card versions.** The invalidated attestation ran against card version
  `b1c2d3e4-…`. Its final re-fetch found a new hash, so card version
  `0a1b2c3d-…` and a new draft contract were created (schema §11). The
  `fetched_at` of a card version is when that hash was first fetched.
- **Contract versions.** The numbers here (2 for the old card version, 1 for
  the new one) assume versions are numbered per card version. That is open
  ([OQ-D5](DATA_MODEL.md#open-questions)).
- **Signature.** The invalidated attestation has no decision (schema §11). It
  is shown signed, because schema §2 says each attestation is signed. What its
  signature covers without a decision is open
  ([OQ-F7](FLOW.md#open-questions)).
- **Budget.** Where a `schedule` attestation's `budget_limit` comes from is
  open ([OQ-D2](DATA_MODEL.md#open-questions)).
- **Second decision.** The reviewer's decision is a second record; the first
  is unchanged (schema §11). No endpoint records that second decision yet
  ([OQ-P2](#open-questions)).
- **Pagination and filtering** are not defined ([OQ-P1](#open-questions)).

## Operations without an interface

The flow and data model need these operations, but no CLI command or endpoint
in schema §6 provides them. They are listed here, not designed
([OQ-P2](#open-questions)):

- Reject a contract, setting `contract.status` to `rejected`.
- Edit a contract, which creates a new version (schema §2).
- Record a human decision on a flagged attestation: the second `decision`
  (schema §11).
- Cancel an attestation, setting `attestation.status` to `cancelled`.
- Register an agent and set `agent.risk_level`.

## Open questions

- **OQ-P1 Payloads are not specified.** The schema defines the command and the
  four paths only. Request and response bodies, status codes, the error
  format, and pagination and filtering for the evidence history are all
  proposals in this document. That includes the response when an attestation
  must wait for a draft contract to be approved.
- **OQ-P2 Operations without an interface.** The list above: reject or edit a
  contract, record a human decision on a `flag`, cancel an attestation,
  register an agent and set its `risk_level`. Which of these need a CLI
  command or an endpoint, and in which stage?
- **OQ-P3 Authentication and reviewer identity.** How do API callers
  authenticate? Where do the identities in `approved_by` and `decided_by` come
  from? Building an identity system is out of scope (schema §10), so an
  external source has to supply them.
- **OQ-P4 Credentials for the Runner.** How do customer credentials for the
  agent under test reach the Runner, from the CLI and from the API, without
  appearing in command lines, request bodies, files or logs?
- **OQ-P5 CLI details.**
  - Is `--runs` the number of repetitions per test case (this document's
    reading) or the total number of runs?
  - Does it have a default?
  - What does the console output look like, and what exit codes does the CLI
    use, especially if CI calls it directly?
  - Where does a CLI attestation get its `budget_limit` and its agent? The
    command has neither, but budget caps are non-negotiable (schema §8), and
    `card_version.agent_id` is required.
  - If CI calls the CLI directly, this document's proposal records the
    attestation as `manual`, not `ci`.
