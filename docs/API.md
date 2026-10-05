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
| `--export-draft FILE` | Writes the draft contract to `FILE` and stops. Nothing runs. |
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

The hosted API is a thin FastAPI adapter (`src/suncly/adapters/api/app.py`)
over the same services the worker runs. The OpenAPI document is served at
`/openapi.json` and `/docs`, and can be written without a server with
`suncly api openapi --out openapi.json`. Everything below is implemented and
covered by `tests/unit/test_api_workflow.py`.

### Conventions

- **Authentication.** Every route except `/v1/health`, `/v1/ready`,
  `/v1/keys`, `/v1/billing/plans` and the Stripe webhook needs
  `Authorization: Bearer <token>`. Tokens are verified against the
  configured OpenID Connect issuer (signature against its JWKS, issuer,
  audience, expiry). Outside production a local HS256 verifier can be
  enabled (`suncly auth local-token`).
- **Tenancy.** The organization is the `{organization_id}` of the URL; the
  caller's role comes from their membership. A body never names an
  organization or a reviewer; an unknown field is a `422`. A non-member
  gets `404` for every organization route, so other tenants' ids are
  indistinguishable from unknown ones.
- **Roles.** `viewer` reads; `reviewer` also registers agents, drafts,
  approves and rejects contracts, starts and cancels attestations and
  resolves flags; `administrator` also manages members, policies,
  spending limits, billing, schedules and keys.
- **Errors.** One envelope for every error, including validation:

```json
{"error": {"code": "quota_exceeded", "message": "The hard spending limit would be exceeded.",
           "detail": "...", "next_step": "...", "request_id": "..."}}
```

  Codes and statuses: `unauthenticated` 401, `forbidden` 403, `not_found`
  404, `conflict` 409, `quota_exceeded` 402, `validation_failed`,
  `contract_invalid`, `card_unusable`, `refused` 422, `billing_provider` 502,
  `internal_error` 500. The response carries `X-Request-Id`; a client may
  send one.

### Routes

| Method and path | Role | What it does |
|---|---|---|
| `GET /v1/health`, `GET /v1/ready` | none | Liveness; readiness touches the database. |
| `GET /v1/keys` | none | The trusted signing-key registry (issuer, key ids, public keys, revocations) for `suncly gate --trusted-keys`. |
| `GET /v1/me` | any | The principal and its organizations with roles. |
| `POST /v1/organizations` | any | Creates an organization; the caller becomes its administrator. |
| `GET /v1/organizations/{id}` | viewer | The organization and the caller's role. |
| `GET`/`POST /v1/organizations/{id}/members` | viewer / administrator | List members; add a member by subject and role. |
| `POST /v1/organizations/{id}/agents` | reviewer | Registers a sandbox agent: name, card URL (checked against the network mode), risk level, sandbox declaration, idempotency declaration, credential reference (`secret-manager`, `env` outside production, or `none`), BYOK flag. |
| `GET /v1/organizations/{id}/agents[/{registration_id}]` | viewer | List or read registrations. |
| `DELETE /v1/organizations/{id}/agents/{registration_id}` | reviewer | Archives a registration; archived agents do not run. |
| `POST .../agents/{registration_id}/contracts/draft` | reviewer | Drafts a contract from the card: `deterministic` (default), `model` (a model drafts a behavioural suite), `suite` (a suite the caller wrote) or `contract_file`. The same content yields the same draft. |
| `GET .../agents/{registration_id}/contracts`, `GET /v1/organizations/{id}/contracts/{contract_id}` | viewer | Contracts of an agent; one contract with its test cases, coverage and suite. |
| `POST /v1/organizations/{id}/contracts/{contract_id}/approve` or `/reject` | reviewer | Human approval or rejection; the approver is the verified caller. |
| `POST /v1/organizations/{id}/attestations` | reviewer | Starts an attestation (`202`): reserves money under the hard limit, creates the record and a durable job. Body: `registration_id`, `contract_id`, `runs`, `budget_limit`, `trigger` (`ci` or `manual`), `external_tools` (`a2a-tck`, `promptfoo`). Refused for drafts, archived or undeclared sandboxes (`409`) and over the limit (`402`). |
| `GET /v1/organizations/{id}/attestations[?registration_id=]`, `GET .../attestations/{attestation_id}` | viewer | Attestations with job state and live progress (planned and recorded runs, phase, unknown outcomes, external tool results). |
| `POST .../attestations/{attestation_id}/cancel` | reviewer | Requests cancellation; a queued job is cancelled at once and its reservation released. |
| `GET .../attestations/{attestation_id}/evidence` | viewer | The result document (`suncly-result/1`), the redacted transcripts and a summary. |
| `GET .../attestations/{attestation_id}/verification` | viewer | The four verification layers for the evidence as stored. |
| `POST .../attestations/{attestation_id}/decisions` | reviewer | Resolves a `flag` with `approve` or `block` and a rationale of at least 20 characters; the reviewer is the caller. A second decision is recorded; the first is never edited. |
| `GET`/`POST /v1/organizations/{id}/policies`, `GET .../policies/{policy_id}` | viewer / administrator | Versioned policy configurations (`suncly-policy/1`). `high_risk_requires_human` cannot be false. |
| `GET /v1/organizations/{id}/usage` | viewer | Entitlement, the period's ledger lines and reservations. |
| `PUT /v1/organizations/{id}/spending-limit` | administrator | The hard limit in minor units. |
| `GET /v1/billing/plans` | none | The test plan catalog and price table version. |
| `GET /v1/organizations/{id}/subscription` | viewer | Subscription and entitlement. |
| `POST .../billing/checkout`, `POST .../billing/portal`, `GET .../billing/reconciliation` | administrator | A checkout session for a plan; the customer portal; held reservations and stale provider events. |
| `POST /v1/webhooks/stripe` | signature | Verified provider events, recorded once, applied in event order. |
| `GET`/`POST /v1/organizations/{id}/schedules` | viewer / administrator | Scheduled re-evaluations of a registration. |

### The CI gate

`suncly gate <report-folder> [--trusted-keys keys.json] [--issuer NAME]
[--policy-hash HASH] [--json]` answers three questions separately and exits
0 only when all three are yes:

| Exit code | Meaning |
|---|---|
| 0 | completed, verified, and the latest decision approves |
| 10 | the attestation did not complete |
| 11 | verification failed (signature, hashes, counts, issuer trust, freshness) |
| 12 | not approved by policy (flag, block, or no decision) |
| 13 | the report cannot be read |

`suncly attest` keeps its exit codes: 0 there means completed and signed,
never approved. `keys.json` is the body of `GET /v1/keys` or the output of
`suncly trust list`.

### Hosted commands

| Command | What it does |
|---|---|
| `suncly api serve` / `suncly api openapi` | Serve the API; write the OpenAPI document. |
| `suncly worker run [--once]` / `suncly worker tick` | Run jobs in the Runner boundary; one dispatcher pass (recover leases, enqueue due re-evaluations, relay the outbox, report usage). |
| `suncly auth local-token --subject S` | A development token (never in production). |
| `suncly trust list` / `revoke KEY --reason R` / `rotate` | The signing-key registry. |
| `suncly judge calibrate DATASET [--provider fake\|configured]` | Judge calibration against the human-labelled dataset. |
| `suncly db migrate` | Apply pending migrations in order. |

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
