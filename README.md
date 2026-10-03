# Suncly

Attestation for A2A agents: prove that an agent does what its Agent Card
claims.

> **Status: pre-prototype.** This repository holds the architecture
> documentation and an empty package skeleton. There is no application code
> yet.

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

## How it works

1. **A trigger arrives:** CI, a schedule, a card change, or a person.
2. **Suncly fetches the Agent Card and hashes it.** If the hash is new, a model
   drafts test cases for every declared skill, and a human approves them as a
   contract.
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

## Getting started

Clone the repository:

```bash
git clone https://github.com/Kristjanh2/Suncly.git
cd Suncly
```

Setup and usage instructions will be added as the
implementation develops.

## Documentation

| Document | Contents |
|---|---|
| [SCHEMA.md](SCHEMA.md) | The architecture schema. **This is the source of truth.** |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Each component's responsibility, inputs, outputs, what it must never do, and how it fails safely. Also the A2A protocol facts Suncly depends on. |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | The seven entities, with fields, types, keys, relationships, enums and an ER diagram. |
| [docs/FLOW.md](docs/FLOW.md) | The attestation flow step by step, the failure paths, and sequence and state diagrams. |
| [docs/API.md](docs/API.md) | The CLI command and the HTTP endpoints, with examples. |
| [docs/POLICY.md](docs/POLICY.md) | Risk levels, approval rules, and when a human is required. |
| [docs/DECISIONS.md](docs/DECISIONS.md) | The non-negotiable rules, as decision records. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | The six build stages, with a definition of done for each. |
| [db/README.md](db/README.md) | What the migration enforces, and which open questions it leaves open. |

**How to read these documents.** Where a document and
[SCHEMA.md](SCHEMA.md) disagree, the schema wins. Each document ends with its
open questions: points the schema leaves undecided, which no document decides
silently. Protocol details that still need checking against the A2A
specification are marked `TODO: verify against spec`.

## Repository layout

```text
.
├── README.md
├── SCHEMA.md                  Architecture schema (source of truth)
├── docs/                      Architecture documentation
├── db/                        Postgres schema for the seven entities (stage 3)
└── src/suncly/                Package skeleton: one placeholder per component, no logic yet
    ├── cli.py                 CLI (stage 1)
    ├── api.py                 HTTP API (stage 5)
    ├── contract_builder.py    Contract builder
    ├── orchestrator.py        Orchestrator
    ├── runner.py              Runner
    ├── judge.py               Judge
    ├── evidence_store.py      Evidence store
    ├── policy_engine.py       Policy engine
    └── adapters/              Registry, CI and Report adapters
```

## Out of scope

Suncly does not build a registry, a gateway, an identity system, a monitoring
platform, a universal score, or payments (schema §10).

## License

No license has been chosen yet.
