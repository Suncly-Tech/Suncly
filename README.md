# Suncly

Attestation for A2A agents: prove that an agent does what its Agent Card
claims.

> **Status: MVP.** From a card URL alone, `suncly attest` drafts test cases,
> records an explicit human approval, runs each test case repeatedly against
> the agent in an isolated Runner, judges every run deterministically, records
> a decision, signs the attestation and writes a report that states what was
> tested, what failed and what was NOT tested. See
> [docs/ROADMAP.md](docs/ROADMAP.md) for exactly what is and is not
> implemented. There is no policy configuration yet, so every decision is
> `flag`: Suncly never approves or blocks an agent in this version.

## The problem

An A2A (Agent2Agent protocol) agent publishes an Agent Card that describes it
and lists the skills it offers. Nothing in the protocol verifies those
claims:

- The A2A specification defines how an agent describes its skills. We found
  no mechanism in it for checking that the agent actually performs them.
- An Agent Card can be signed. A signature shows that the card was not altered,
  and who signed it. It says nothing about how the agent behaves (see
  [A2A protocol dependencies](docs/ARCHITECTURE.md#a2a-protocol-dependencies)).

## What Suncly does

Think of it as a roadworthiness inspection for AI agents. Suncly:

1. reads an agent's Agent Card;
2. generates test cases for each declared skill;
3. runs each test many times against the agent in a sandbox;
4. judges the results and stores signed evidence;
5. outputs an approval decision for a company's agent registry or CI pipeline.

It is built for platform and security teams that approve agents and
currently do that review by hand.

## Quickstart

You need Python 3.12 or newer. The same commands work on Windows PowerShell,
macOS and Linux; the one line that differs is marked.

```powershell
git clone https://github.com/Suncly-Tech/Suncly.git
cd Suncly
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -e .
suncly demo
```

`suncly demo` starts two bundled mock agents on this machine, an honest one and
a lying one, attests both, and shows the difference: the honest agent passes
every run, the lying agent fails the output modes its card declares, and both
end with `Decision: flag. No policy is configured, so a human must review this
result.` Reports land in `./suncly-reports/`.

To attest a sandbox agent from its card URL:

```powershell
suncly attest https://sandbox.example.com/.well-known/agent-card.json --sandbox
```

Suncly shows the drafted test cases and asks for your approval and your
identifier before anything runs. `--sandbox` is your declaration that the
endpoint is a sandbox or dry-run endpoint; without it, nothing runs.

The full walkthrough, including a credential, the contract file workflow,
Postgres and troubleshooting, is in [docs/QUICKSTART.md](docs/QUICKSTART.md).

## Commands

| Command | What it does |
|---|---|
| `suncly attest <card-url> --sandbox` | Attest the agent at the card URL. `--runs`, `--budget`, `--approve-as`, `--contract`, `--export-draft`, `--json`. |
| `suncly demo` | Attest the bundled honest and lying mock agents. |
| `suncly verify <report-folder>` | Check the signature, card hash, decision and every transcript of a report. |
| `suncly keys init` | Create the local Ed25519 deployment key. |
| `suncly db migrate`, `suncly db check` | Apply and check the Postgres schema (when `DATABASE_URL` is set). |
| `suncly doctor [card-url]` | Check Python, the key, the store configuration and a card URL. |

Exit code 0 means the attestation completed and was signed. It never means the
agent was approved. All codes are listed in [docs/API.md](docs/API.md).

## How it works

1. **A trigger arrives:** CI, a schedule, a card change, or a person.
2. **Suncly fetches the Agent Card and hashes it.** If the hash is new, the
   Contract builder drafts test cases for every declared skill, and a human
   approves them as a contract.
3. **The Orchestrator expands the contract into runs.** Each test case runs
   many times, within a cost budget.
4. **The Runner calls the agent's sandbox endpoint** as an A2A client and
   captures every message. It is the only component that holds the customer's
   credentials.
5. **The Judge scores each run.** Deterministic checks come first, and a
   pinned model is used only where those cannot decide. The verdict is
   `pass`, `fail` or `inconclusive`, and `inconclusive` never counts as a
   pass.
6. **The Policy engine decides and signs.** It applies the customer's policy
   for the agent's risk level, decides `approve`, `flag` (for human review) or
   `block`, and signs the attestation.
7. **Adapters publish the result:** a registry status, a CI gate, and an
   evidence report that states what was NOT tested.

The full flow, including the failure paths, is in
[docs/FLOW.md](docs/FLOW.md).

## System diagram

From [SCHEMA.md](SCHEMA.md) §1:

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

## Documentation

| Document | Contents |
|---|---|
| [SCHEMA.md](SCHEMA.md) | The architecture schema. **This is the source of truth.** |
| [docs/QUICKSTART.md](docs/QUICKSTART.md) | Install, run the demo, attest your own sandbox agent, read and verify a report. |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Each component's responsibility, inputs, outputs, what it must never do, and how it fails safely. Also the A2A protocol facts Suncly depends on. |
| [docs/CODE_ARCHITECTURE.md](docs/CODE_ARCHITECTURE.md) | How the code maps to the components: layers, dependency diagram, the Runner boundary, where to add what. |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | The seven entities, with fields, types, keys, relationships, enums and an ER diagram. |
| [docs/FLOW.md](docs/FLOW.md) | The attestation flow step by step, the failure paths, and sequence and state diagrams. |
| [docs/API.md](docs/API.md) | The CLI with its options and exit codes, the contract file format, and the HTTP endpoints. |
| [docs/POLICY.md](docs/POLICY.md) | Risk levels, approval rules, and when a human is required. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | The non-negotiable rules, as decision records. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | The six build stages, what this MVP implements, and what it does not. |
| [docs/IMPLEMENTATION_NOTES.md](docs/IMPLEMENTATION_NOTES.md) | Every proposal the code implements, the choices the founders decided, every choice that still needs a decision, and the facts that were verified. |
| [db/README.md](db/README.md) | What the migration enforces, and which open questions it leaves open. |

**How to read these documents.** Where a document and
[SCHEMA.md](SCHEMA.md) disagree, the schema wins. Each document ends with its
open questions: points the schema leaves undecided, which no document decides
silently. Protocol details that still need checking against the A2A
specification are marked `TODO: verify against spec`.

## Development

```powershell
pip install -e ".[dev]"
python tasks.py check        # ruff check, ruff format --check, mypy --strict, pytest with coverage
```

Or the individual steps, which are what `tasks.py` runs:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m pytest --cov
```

The database tests and the Postgres store tests run only when `DATABASE_URL`
points at a Postgres database (CI starts one); they are skipped otherwise.
`make check` works on macOS and Linux and delegates to `tasks.py`.

## Repository layout

```text
.
├── README.md
├── SCHEMA.md                  Architecture schema (source of truth)
├── docs/                      Architecture and implementation documentation
├── db/                        Postgres schema for the seven entities (stage 3)
├── src/suncly/
│   ├── domain/                The seven entities, Agent Card parsing, criteria, rules (no I/O)
│   ├── ports/                 Interfaces: store, transcripts, drafter, signer, clock, HTTP, executor
│   ├── core/                  Contract builder, Orchestrator, Judge, Policy engine, signing, use case
│   ├── runner/                The isolated Runner: its own process, the only credential holder
│   ├── adapters/              File and Postgres stores, keys, card fetcher, subprocess executor, report
│   ├── mock_agents/           Bundled mock A2A agents (the demo and the tests)
│   ├── cli/                   The suncly command
│   └── api.py                 Placeholder for the stage 5 HTTP API
├── tests/                     unit, stores (one suite for both stores), e2e (mock agents, real CLI), db
├── pyproject.toml, tasks.py, Makefile, .github/workflows/ci.yml
└── .env.example               Every environment variable Suncly reads
```

## Out of scope

Suncly does not build a registry, a gateway, an identity system, a monitoring
platform, a universal score, or payments (schema §10).

## License

No license has been chosen yet.
