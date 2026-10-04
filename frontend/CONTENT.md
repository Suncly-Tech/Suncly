# Suncly website — content source

Every headline, paragraph, label and code snippet on the site lives here first.
Components import copy from `lib/content.ts`, which mirrors this file. Nothing is
improvised inside JSX.

## Sources

The repository now carries the architecture documentation. Tags used below:

| Tag | Document |
| --- | --- |
| `README` | `README.md` |
| `SCHEMA` | `SCHEMA.md` (source of truth; §N = section) |
| `ARCH` | `docs/ARCHITECTURE.md` |
| `FLOW` | `docs/FLOW.md` |
| `API` | `docs/API.md` (example payloads are marked *Proposed* there and are fictional) |
| `POLICY` | `docs/POLICY.md` |
| `DR` | `docs/DECISIONS.md` |
| `ROADMAP` | `docs/ROADMAP.md` |
| `DATA` | `docs/DATA_MODEL.md` |
| `A2A` | A2A specification v1.0.1, as quoted in `docs/ARCHITECTURE.md` |
| `BRIEF` | the website brief (contact email, city, early-access status) |
| `ILLUSTRATIVE` | sample output whose format the docs leave open; marked in code |

Nothing on the site states pricing, customers, logos, testimonials, usage numbers
or pass thresholds. The schema says: "do not invent numbers" (SCHEMA §5).

The logo lockups come from `assets/`; see `scripts/generate-logo.mjs`.

---

## Global

- Mission: *Prove that an A2A agent does what its Agent Card claims.* — `README`, `SCHEMA` title
- Meta title: *Suncly — Attestation for A2A agents* — `README`
- Meta description: *Suncly proves that an A2A agent does what its Agent Card claims: it tests every declared skill many times in a sandbox, judges the results, and hands your reviewers signed evidence to approve on.* — `README` "What Suncly does"
- Contact `team@suncly.com`, Tallinn, Estonia, © 2026 Suncly — `BRIEF`
- Repo is private → no GitHub link.

## Nav

Product · How it works · Architecture · Policy · Docs · **Get early access**

## Hero

Candidates: (1) *Does your agent do what its card says?* ← chosen; (2) *Prove it before you approve it.*; (3) *A roadworthiness inspection for AI agents.* (used as the section headline for "What Suncly does").

- Eyebrow: *Early access · for platform and security teams* — `README` ("built for platform and security teams")
- Subhead: *Suncly reads an A2A Agent Card, tests every declared skill many times in a sandbox, judges the results, and hands your reviewers signed evidence to approve on.* — `README` steps 1–5
- CTAs: Get early access / Read the docs — `BRIEF`

### Attestation window — `API` (GET /attestations/{id} and GET /agents/{id}/evidence examples)

- Agent: Order Status Agent · owner example-team · risk low
- Trigger ci · status completed · card `agent.example.com/.well-known/agent-card.json`
- Contract v1 · approved by reviewer@example.com
- Results: test case 9b0c1d2e, skill order-status, kind skill: 49 pass / 0 fail / 1 inconclusive; test case 2d3e4f5a: 50 / 0 / 0
- Decisions: policy → flag (09:42); reviewer@example.com → approve (11:05)
- Budget: cost_total 3.42 of budget_limit 25.0
- Signed · signing_key_id
- Not tested: capabilities.streaming; production endpoint — `ARCH` Report adapter (proposed examples), `DR-007`

## The gap — `README` "The problem"

Headline: *The protocol describes. Nothing verifies.*

1. *A card is a list of claims.* The spec defines how to describe a skill; no mechanism checks that the agent performs it.
2. *A signature is not a test.* A signature shows the card was not altered and who signed it; nothing about behaviour.
3. *So approval is done by hand.* Built for platform and security teams that approve agents by hand today.

## What Suncly does — `README`

Headline: *A roadworthiness inspection for AI agents.* Five steps quoted from the README.

## How it works — `README` "How it works" (7 steps)

Steps 1–7 as in the README. Terminal: command from `API`; console output `ILLUSTRATIVE` (format not defined, OQ-P5). Sample values in the output are the `API` example values.

## Architecture — `SCHEMA` §1–2, `ARCH` Components

Headline: *Six components in the core. Three thin adapters outside it.* "A fault can make Suncly approve less, never more." — `ARCH` Components intro.
Each component: responsibility from `SCHEMA` §2 / `ARCH`; "never" line from the component's *Must never* list in `ARCH`.
Diagram: the system layout from `SCHEMA` §1.

## Product 01–06

- 01 Contract — `SCHEMA` §2 Contract builder, §4 step 2
- 02 Runs — `SCHEMA` §2 Orchestrator, §8 (idempotent runs, sandbox, budget)
- 03 Probes — `SCHEMA` §3 test_case.kind; `ROADMAP` stage 4; `DATA` value meanings (working definitions)
- 04 Judge — `SCHEMA` §2 Judge
- 05 Evidence — `SCHEMA` §2 Evidence store, §11 signature payload, §8 reports state what was NOT tested
- 06 Decision — `SCHEMA` §2 Policy engine and Adapters

## Approval policy — `SCHEMA` §5, `POLICY`

Risk table (low / medium / high) verbatim. "Human is always required: first contract approval, new or changed skills, borderline or dropping results" + high-risk every time. Outcomes approve / flag / block from `POLICY` Decision outcomes. "No decision is never an approval." — `POLICY` When no decision is made. Thresholds: "configured per customer and per risk level"; no numbers — `SCHEMA` §5.

## Non-negotiable — `SCHEMA` §8, `DR` DR-001…DR-007

Seven rules verbatim; one-line reasons condensed from each record's *Reason*.

## Open standard — `ARCH` A2A protocol dependencies, `API`

Reads: card location, skills fields, supportedInterfaces, capabilities, securitySchemes, signatures — `A2A`. Emits: results, decisions, signature, report — `API`, `SCHEMA` §11. JSON: shortened GET /attestations/{id} response — `API` (Proposed).

## Interfaces — `SCHEMA` §6, `API`

CLI `suncly attest <card-url> --runs 50`; four endpoints; POST /attestations example body — `API` (Proposed).

## Where we are — `ROADMAP`, `SCHEMA` §7, §9, §10

Status pre-prototype; six stages; stack; out of scope.

## Documentation — `README` Documentation table

Eight documents with the README's descriptions. Shown as "With early access" since the repository is private. `/docs` is a hub page describing them.

## Early access — `BRIEF`, `README`

*Run the first pilot with us.* "Stage 1 is enough to run a first pilot by hand" — `SCHEMA` §9.

## FAQ — all answers from `README`, `SCHEMA`, `ARCH`, `POLICY`, `DR`, `ROADMAP`

Twelve questions; see `lib/content.ts`.

## Footer

Product · Developers · Company · Legal groups; Tallinn, Estonia; © 2026 Suncly.
