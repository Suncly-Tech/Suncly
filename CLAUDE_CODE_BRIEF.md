# Claude Code brief: bring Suncly to a working stage 1

You are working in the `suncly` repository. It currently holds architecture
documentation and an empty Python package skeleton. Your job is to clean up
the repository, set up the project tooling, and implement roadmap **stage 1**
completely, with tests, so that a person can run a pilot attestation by hand.

Work through the phases in order. Do not skip ahead. At the end of each phase,
run the checks listed for it and commit.

---

## 0. Ground rules (read before doing anything)

### 0.1 Read these first, in this order

1. `SCHEMA.md` — the architecture schema. **This is the source of truth.**
2. `docs/ARCHITECTURE.md` — components, what each must never do, A2A protocol facts.
3. `docs/DATA_MODEL.md` — the seven entities, fields, enums, invariants.
4. `docs/FLOW.md` — the attestation flow and failure paths.
5. `docs/DECISIONS.md` — the non-negotiable rules DR-001 to DR-007.
6. `docs/ROADMAP.md` — the six stages and each stage's definition of done.
7. `docs/API.md` and `docs/POLICY.md` — the CLI, the HTTP endpoints, the approval rules.

Do not write code until you have read all of them.

### 0.2 Precedence

- Where any document and `SCHEMA.md` disagree, `SCHEMA.md` wins.
- Schema §11 overrides schema §3 where they differ.
- Where this brief and the repository documents disagree, the repository
  documents win. Stop and report the disagreement instead of guessing.

### 0.3 Open questions: never decide one silently

The documents track open questions as `OQ-…` and unverified protocol details
as `A2A-T…`. When your work touches one:

- If the documents contain a **Proposed** answer, implement the proposal, keep
  it behind one clearly named function, constant or config value so it is easy
  to change, and record it in `docs/IMPLEMENTATION_NOTES.md` (see 0.6).
- If there is no proposal, choose the option that makes Suncly **approve less,
  never more**, record it the same way, and mark it `NEEDS DECISION`.
- Never edit `SCHEMA.md`. Never mark an open question as resolved. Only the
  founders resolve open questions.

### 0.4 Names

Entity, field and enum names are exactly the schema's: `card_version`,
`card_hash`, `test_case`, `attestation`, `run`, `decision`, `inconclusive`,
`cancelled`, and so on. Do not rename, pluralise or abbreviate them in code,
files, reports or messages.

### 0.5 Things you must never do

- Never call a real production agent endpoint. All tests run against the local
  mock agents you build in phase 3.
- Never commit secrets, API keys, tokens, connection strings or `.env` files.
- Never print or log a credential, including in error messages and test output.
- Never add an entity, table or field that the data model does not define.
- Never count `inconclusive` as a pass, anywhere.
- Never use `git push --force`, and never rewrite published history.
- Do not start stages 2 to 6. They are out of scope for this brief (see phase 6).

### 0.6 `docs/IMPLEMENTATION_NOTES.md`

Create this file in phase 1 and keep it current. It has three sections:

1. **Proposals implemented** — a table: open question id, what was
   implemented, where in the code, how to change it.
2. **Needs decision** — choices you had to make with no proposal in the
   documents.
3. **Verified facts** — things you checked (for example A2A-T7), with the date,
   the exact version checked and the source.

### 0.7 Language and style

- Everything in the repository is in English: code, comments, docs, commit
  messages, CLI output.
- Small, focused commits with imperative messages ("Add card canonicalization").
- Every module has tests. No phase is done while a test fails.

---

## 1. Phase 1 — Repository cleanup

The repository went through a mistaken switch to Cloudflare D1 and back.
Storage is **Postgres** (schema §7). Leave it consistent.

### 1.1 Restore Postgres wording

Run:

```bash
git grep -n -i -P "(?<!OQ-)\bD1\b|Cloudflare|wrangler|R2 object storage" -- SCHEMA.md docs
```

For every hit in `SCHEMA.md` or `docs/`, restore the original Postgres wording.
The known damaged lines are:

| File | Wrong | Correct |
|---|---|---|
| `docs/ARCHITECTURE.md` (Orchestrator) | `The queue starts as a D1-backed job table` | `The queue starts as a Postgres-backed job table` |
| `docs/ARCHITECTURE.md` (Stack, Storage) | `Cloudflare D1 for tables, R2 object storage for transcripts.` | `Postgres for tables, object storage for transcripts.` |
| `docs/ARCHITECTURE.md` (Stack, Queue) | `A D1-backed job table first` | `A Postgres-backed job table first` |
| `SCHEMA.md` §7, if affected | `Cloudflare D1 for tables, R2 object storage` / `D1-backed` | `Postgres for tables, object storage` / `Postgres-backed` |

This is the one case where you may touch `SCHEMA.md`: only to undo those exact
substitutions. Use `git log -p -- SCHEMA.md` to confirm the original text and
restore it byte for byte. Change nothing else in that file.

### 1.2 Verify the `db/` folder

`db/` must contain exactly two files:

- `db/migrations/0001_initial_schema.sql`
- `db/README.md`

Check that the migration:

- has the header line `-- Target:    PostgreSQL 13+ (Supabase, Google Cloud SQL, plain Postgres)`;
- creates exactly seven tables: `agent`, `card_version`, `contract`,
  `test_case`, `attestation`, `run`, `decision`;
- creates the eight enum types listed in `docs/DATA_MODEL.md`: Enumerations;
- matches every field, type and nullability in `docs/DATA_MODEL.md`: Entities.

If the file targets Cloudflare D1 or SQLite, or contains tables such as
`organizations`, `check_definitions` or `http_exchanges`, it is an obsolete
draft. **Stop and tell the user** to supply the correct Postgres version. Do
not write a replacement from memory.

If you find a difference between the migration and `DATA_MODEL.md`, report it.
Do not change the migration silently.

### 1.3 Update the root `README.md`

In "Repository layout", add the `db/` folder:

```text
├── db/                        Postgres schema for the seven entities (stage 3)
```

In the "Documentation" table, add a row for `db/README.md`: "What the
migration enforces, and which open questions it leaves open."

Fix the clone URL only if `git remote get-url origin` shows a different one.

### 1.4 Phase 1 checks

```bash
# Decided 2026-10-04: the check excludes the open-question ids OQ-D1, OQ-D10 and
# OQ-D11 (lookbehind and word boundaries) and this brief, which quotes the names.
git grep -n -i -P "(?<!OQ-)\bD[1]\b|Cloud[f]lare|wrang[l]er" -- . ':!CLAUDE_CODE_BRIEF.md'   # must print nothing
git grep -n -i "postgres" | wc -l              # must be greater than 0
```

Commit: `Restore Postgres wording and document the db folder`.

---

## 2. Phase 2 — Project tooling

### 2.1 Package setup

> **Decided (2026-10-04):** the pinned minimum is Python 3.12
> (`requires-python = ">=3.12"`), what the founders' machines run; CI tests 3.12,
> 3.13 and 3.14, the newest version every dependency ships wheels for. The two
> requests below are met by that pair.

- `pyproject.toml` with the package `suncly` under `src/`, a `suncly` console
  script pointing at `suncly.cli:main`, and a pinned minimum Python version.
  Pick the newest Python version that all dependencies support, and record
  the choice in `IMPLEMENTATION_NOTES.md`.
- Dependencies pinned to compatible ranges. Keep the list short. Expected:
  an HTTP client (`httpx`), a validation library (`pydantic`), a CLI library
  (`typer` or `click`), and an RFC 8785 canonicalization library if a
  maintained one exists (otherwise implement and test it yourself).
- Dev dependencies: `pytest`, `pytest-asyncio` if you use async, `ruff`,
  `mypy`.
- `.gitignore` covering Python artefacts, virtual environments, `.env`,
  report output folders and editor files.
- `.env.example` listing every environment variable the code reads, with
  placeholder values and one-line explanations. No real values.

### 2.2 Quality gates

- `ruff` for linting and formatting, configured in `pyproject.toml`.
- `mypy` in strict mode for `src/suncly`.
- `pytest` with coverage reporting.
- A `Makefile` or `justfile` with: `install`, `lint`, `typecheck`, `test`,
  `check` (all three). Also document the equivalent plain commands in the root
  `README.md` under "Getting started", because the developers use Windows
  PowerShell.

### 2.3 Continuous integration

`.github/workflows/ci.yml`, on push and pull request:

1. Lint, type-check and test on the pinned Python version.
2. A separate job that starts a Postgres service container, applies
   `db/migrations/0001_initial_schema.sql` with `psql -v ON_ERROR_STOP=1`, and
   runs the database tests from 2.4.

### 2.4 Database tests

Add `tests/db/` with tests that run only when `DATABASE_URL` is set (skip
otherwise). They apply the migration to an empty database and assert, with
real inserts and updates, that the database rejects each of the following:

- an attestation for a contract that is not `approved`;
- any change to, or deletion of, an `approved` contract (other than the move
  to `superseded`), and any insert, update or delete of its test cases;
- an attestation whose `card_version_id` differs from its contract's;
- a second run with an existing (`attestation_id`, `test_case_id`, `attempt`);
- a run with `judge_layer` `model` and no `rationale`;
- a run whose test case belongs to a different contract than its attestation;
- `UPDATE`, `DELETE` and `TRUNCATE` on `run` and on `decision`;
- a decision for a `failed`, `invalidated` or `cancelled` attestation;
- a first decision whose `decided_by` is not `policy`;
- a `completed` attestation without a decision or without a signature;
- a final attestation status without `finished_at`, and the reverse.

Also assert that `card_version.raw_json` is returned byte for byte as
inserted, including whitespace.

### 2.5 Phase 2 checks

`make check` (or the plain commands) passes. CI is green.

Commit: `Add project tooling, CI and database tests`.

---

## 3. Phase 3 — Stage 1: the core library

Implement the **definition of done of stage 1** in `docs/ROADMAP.md`. Every
item in that list must be demonstrably true at the end. The list below is how
to get there; the roadmap list is what counts.

Stage 1 has **no database, no signing, no Layer 2, no Policy engine and no
Contract builder**. Results are written to files. Stage 1 results are not
signed and get no decision.

> **Decided (2026-10-04):** the implemented MVP goes beyond this scope. Every
> attestation is signed, a completed one records a `flag` decision, evidence
> lives in the file store or in Postgres, and a deterministic Contract builder
> drafts the contract. The statements in 3.8 and 3.10 that stage 1 results are
> unsigned and carry no decision are superseded: the report and the CLI say that
> the decision is `flag` and that exit code 0 is not an approval. See
> `docs/ROADMAP.md` for what is and is not implemented.

### 3.1 Verify the A2A Python SDK first (A2A-T7)

> **Decided (2026-10-04):** the SDK does support protocol 1.0 (`a2a-sdk` 1.2.1,
> see `docs/IMPLEMENTATION_NOTES.md`, Verified facts). Suncly nevertheless uses
> its own minimal JSON-RPC client behind the `A2ATransport` port, limited to
> `SendMessage` and `GetTask` polling. Reason: the Runner's isolation (one target
> host) and its redaction are easier to audit in Suncly's own few hundred lines
> than through the SDK and its dependencies inside the one process that holds
> credentials. Revisit when streaming or push notifications are needed; the
> switch is one new adapter for the port. The instruction below to use the SDK
> is superseded by this decision.

Before writing the Runner, check whether the Python A2A SDK supports protocol
version 1.0 (the PascalCase method names, the `TASK_STATE_…` names and the
14-field Agent Card described in `docs/ARCHITECTURE.md`: A2A protocol
dependencies).

- Check the SDK's current release, its changelog and its source. Record the
  exact version, the date and what you found in `IMPLEMENTATION_NOTES.md`
  under "Verified facts".
- If it supports 1.0: use it, pinned to that version.
- If it does not, or you cannot confirm it: write a minimal client of your own
  behind an interface (see 3.5), limited to what stage 1 needs. Do not mix the
  two approaches.

Treat `docs/ARCHITECTURE.md` as the reference for protocol facts. Where it
says `TODO: verify against spec`, check the versioned specification (v1.0.1,
not the `latest` page) and record what you find. Do not take a side the
documents have not taken.

### 3.2 Domain models (`src/suncly/models.py`)

In-memory models for the seven entities, with exactly the fields, enum values
and nullability of `docs/DATA_MODEL.md`. Enforce in the models every invariant
that can be checked without a database: 3, 6, 7, and the rule that a `skill`
test case has a `skill_id`. These models are what stage 3 will later persist,
so do not add or rename fields.

### 3.3 Agent Card handling (`src/suncly/card.py`)

- Fetch the card from `<card-url>` over https with a timeout and a response
  size limit. Reject non-https URLs. Reject redirects to non-https URLs.
- Keep the body exactly as fetched for `card_version.raw_json`.
- Canonicalize and hash to produce `card_hash`. The scheme is open (OQ-A7).
  Implement RFC 8785 (JCS) canonicalization and SHA-256, with the `signatures`
  field excluded, as **one** function, and record it as a proposal for OQ-A7.
  State in the report file which scheme produced the hash.
- Parse the card far enough to read `skills` and `supportedInterfaces`.
- Fail-safe (OQ-A11): a card that cannot be parsed or canonicalized creates no
  records and fails visibly with a clear message. A card with no skills is
  reported as not attestable.

Tests: identical cards with different key order and whitespace give the same
hash; a changed value gives a different hash; a changed `signatures` field
gives the same hash; invalid JSON, a non-https URL, an oversized body and a
timeout each fail with a distinct, clear error.

### 3.4 Contract file (OQ-R2)

> **Decided (2026-10-04):** the format is JSON, documented in `docs/API.md`
> under "Contract file". A file carries no approval: approval is recorded by
> `--approve-as` or the interactive prompt, never asserted by a file. A declared
> skill without a test case must be listed under `skills_without_test_case`, or
> the file is refused; the drafter lists skills without examples the same way
> and never invents input. No `examples/` folder is shipped:
> `suncly attest <card-url> --sandbox --export-draft FILE` writes the example
> from any card. The bullets below that say otherwise are superseded.

The Contract builder arrives in stage 2. For stage 1, test cases come from a
contract file written by hand (the proposal in OQ-R2).

- Define one documented file format (YAML or JSON) holding a contract and its
  test cases, with the data model's field names: `skill_id`, `input`,
  `criteria`, `kind`.
- The format of `input` and `criteria` is open (OQ-D7). Define the minimum
  stage 1 needs and record it as a proposal: `input` is the message to send;
  `criteria` holds the Layer 1 checks (expected final task state, required
  fields, latency limit in milliseconds, and an optional JSON Schema for the
  response).
- Stage 1 runs only contracts whose `status` is `approved` with `approved_by`
  and `approved_at` filled in. A contract file without them is refused.
- Refuse a contract that leaves a declared skill of the fetched card without a
  test case (invariant 1).
- Refuse a contract whose `card_hash` does not match the fetched card.
- Ship one example contract file under `examples/` that works against the
  honest mock agent from 3.9, and document the format in `docs/API.md` under
  a "Stage 1 contract file" heading marked **Proposed**.

### 3.5 Runner (`src/suncly/runner.py`)

Follow `docs/ARCHITECTURE.md`: Runner exactly, including its "must never" and
"fails safely" lists.

- Runs in its own process (a subprocess started by the orchestrator), and
  receives only what one run needs: the test case input, the run key, the
  agent interface, credentials and timeouts.
- Network access limited to the target: the Runner refuses any request whose
  host is not the target agent's host. Enforce this in one place in the HTTP
  layer, and test it.
- Acts as an A2A client: sends the test case input as a `Message`, follows the
  `Task` to a terminal state, and records every message it receives directly.
  It does not rely on `Task.history`. It handles a direct `Message` reply.
- Sends the `A2A-Version` service parameter.
- Picks the first entry in `supportedInterfaces` that it supports. Stage 1
  supports one binding; choose JSON-RPC over HTTP unless the SDK check in 3.1
  gives a reason not to, and record the choice (OQ-A4).
- Does not use push notifications (the proposal in OQ-A4).
- On an interrupted state (`TASK_STATE_INPUT_REQUIRED`,
  `TASK_STATE_AUTH_REQUIRED`) it stops and records the state. It never invents
  input.
- **Sandbox only (DR-006).** The Runner calls an endpoint only when the user
  has explicitly declared it a sandbox or dry-run endpoint, through a required
  CLI flag or the contract file. With no such declaration, it refuses to run.
  How Suncly verifies a sandbox is open (OQ-A2); record this as the stage 1
  proposal.
- **Redaction (DR-003).** Secrets are removed inside the Runner before the
  transcript is returned. What counts as a secret is open (OQ-A3). Implement:
  the credentials the Runner was given, `Authorization` and cookie headers,
  and a small documented list of patterns. If redaction raises an error, the
  transcript is withheld and the run is not recorded (OQ-A11).
- Credentials come from environment variables only (OQ-P4), never from
  command-line arguments or files in the repository.
- Returns to the caller: the redacted transcript, `latency_ms`, `started_at`,
  `finished_at`, `cost`. What `latency_ms` measures is open (OQ-D10): measure
  from sending the message to reaching a terminal state, null when there was
  no response, and record it as a proposal.
- If the agent is unreachable or a timeout expires, return a transcript that
  records the failure. Such a run can never be judged `pass`.

### 3.6 Minimal Orchestrator (`src/suncly/orchestrator.py`) (OQ-R1)

Implement the proposal in OQ-R1: a minimal Orchestrator inside the process.

- Expands the contract into runs: every test case times `--runs`.
- Every run has the deterministic run key (`attestation_id`, `test_case_id`,
  `attempt`), where `attempt` is the repetition number from 1 (OQ-D3).
- Retries a crashed or timed-out run under the **same** run key. A run is
  recorded at most once (DR-001). Test this by killing a Runner subprocess.
- Timeouts per run, and a concurrency limit.
- **Budget cap (DR-005).** Tracks `cost_total` against `budget_limit` and stops
  starting runs when it is reached. The attestation then ends as `failed` and
  the report says how many planned runs were not executed.
- At the end, re-fetches and re-hashes the card. If the hash differs, the
  attestation ends as `invalidated`. If the card cannot be re-fetched, no
  result is reported as passing (OQ-F5).
- Holds no credentials and never calls the agent itself.

### 3.7 Judge, Layer 1 (`src/suncly/judge.py`)

- Deterministic checks only: valid schema, final task state, required fields,
  latency limit.
- A final task state is one of `TASK_STATE_COMPLETED`, `TASK_STATE_FAILED`,
  `TASK_STATE_CANCELED`, `TASK_STATE_REJECTED`. Interrupted states and
  `TASK_STATE_UNSPECIFIED` are not final.
- Verdict is `pass`, `fail` or `inconclusive`, with `judge_layer`
  `deterministic`.
- A response that fails a check is `fail`. If Suncly cannot read the transcript
  because of its own fault, the verdict is `inconclusive`, never `pass`.
- A criterion Layer 1 cannot decide gives `inconclusive` in stage 1, because
  Layer 2 does not exist yet. The report must say so.
- The Judge never calls the agent and never changes a recorded run.

### 3.8 File report (`src/suncly/adapters/`) (DR-007)

The first version of the Report adapter (OQ-R6). One attestation produces one
output folder containing:

- a machine-readable result file (JSON) with the attestation, its runs and the
  card version, using the data model's field names;
- the redacted transcripts, one file per run, referenced by `transcript_ref`;
- a human-readable report (Markdown).

The human-readable report must show:

- the card URL, `card_hash` and the hashing scheme used;
- the contract version and who approved it;
- for each test case: counts of `pass`, `fail` and `inconclusive`. Never a
  single combined score, and never `inconclusive` added to passes;
- the attestation status, `cost_total` and `budget_limit`;
- a section titled **"What was NOT tested"**, listing at least: runs never
  executed because the budget stopped them, `inconclusive` runs, declared
  capabilities that no test exercised (such as streaming or push
  notifications), protocol bindings that were not used, and the production
  endpoint itself, because tests ran against a sandbox;
- a clear statement that stage 1 results are **not signed and carry no
  decision**.

If evidence is missing or incomplete, the report says so explicitly.

### 3.9 Mock A2A agents (`tests/mock_agents/`)

Small local HTTP servers that speak the A2A binding the Runner uses, each with
its own Agent Card. Build at least:

| Mock | Behaviour | Expected result |
|---|---|---|
| honest | Does what its card says. | All runs `pass`. |
| lying | Declares a skill, returns a wrong or malformed result. | Runs `fail`. |
| flaky | Succeeds on some calls, fails on others, deterministically by call count. | A mix of `pass` and `fail`; counts are exact. |
| slow | Answers after the latency limit. | Runs `fail` the latency check. |
| unreachable | Refuses connections or never answers. | No run is `pass`. |
| direct-message | Replies with a `Message` instead of a `Task`. | Handled without error. |
| interrupted | Stops at `TASK_STATE_INPUT_REQUIRED`. | Recorded; never `pass`. |
| leaky | Echoes the credential it was sent back in its reply. | The credential does not appear in any transcript, report or log. |
| card-changer | Serves a different card on the second fetch. | Attestation ends `invalidated`. |

### 3.10 CLI (`src/suncly/cli.py`)

- The command is `suncly attest <card-url> --runs <n>`, as in `docs/API.md`.
- The CLI holds no logic of its own. It parses arguments and calls the core
  library (schema §6). Keep every decision in the library so the stage 5 API
  can call the same functions.
- Add only the options stage 1 cannot work without, and document each in
  `docs/API.md` as **Proposed** (OQ-P5): the contract file path, the budget
  limit, the sandbox declaration, the output folder.
- Exit codes: 0 only when the attestation ran to the end and the card was
  unchanged. A distinct non-zero code for each of: `failed` (budget),
  `invalidated` (card changed), refused to start (no approved contract, no
  sandbox declaration, card not attestable), and internal error. Document
  them. An exit code of 0 does **not** mean the agent passed: stage 1 makes no
  decision, and the CLI output must say so.

### 3.11 Tests

- Unit tests for every module.
- End-to-end tests that run `suncly attest` against each mock agent and assert
  the exact verdict counts, the attestation status, the exit code and the
  report contents.
- A test that greps every produced file and captured log for the test
  credential and fails if it is found.
- A test for each non-negotiable rule DR-001, DR-003, DR-005, DR-006 and
  DR-007, named after the rule.

### 3.12 Phase 3 checks

- `make check` passes and CI is green.
- Go through the stage 1 definition of done in `docs/ROADMAP.md` line by line.
  For each line, name the test that proves it.

Commit in small steps as you go, one module at a time.

---

## 4. Phase 4 — Documentation

- Root `README.md`: replace "Setup and usage instructions will be added" with
  real instructions for Windows PowerShell and for macOS/Linux: install, run
  the honest mock agent, run `suncly attest` against it with the example
  contract, and where to find the report. Update the status line to say that
  stage 1 is implemented and stages 2 to 6 are not.
- `docs/ROADMAP.md`: tick the stage 1 items that are done. Do not tick an item
  unless a test proves it. Update the status line.
- `docs/IMPLEMENTATION_NOTES.md`: complete and accurate.
- Do not change the meaning of any other document. If the implementation
  showed that a document is wrong or contradicts another, do not fix it
  silently: list it in the final report.

Commit: `Document stage 1 usage and implementation notes`.

---

## 5. Phase 5 — Final report

When everything above is done, write a summary for the user containing:

1. **Stage 1 definition of done** — each line of the roadmap list, marked done
   or not done, with the test that proves it.
2. **Proposals implemented** — each open question you implemented a proposal
   for, in one line.
3. **Needs decision** — each choice you made without a proposal.
4. **Verified facts** — what you found for A2A-T7 and any other `TODO: verify`.
5. **Document problems** — contradictions or errors you found in the documents.
6. **Not done** — anything in this brief you could not complete, and why.
7. **How to try it** — the exact commands to run a pilot attestation by hand.

---

## 6. Out of scope — do not do these

| Item | Why |
|---|---|
| Stage 2: Contract builder | Needs decisions on OQ-A1, OQ-D5, OQ-D7, OQ-R3 and model keys. |
| Stage 3: persistence, Evidence store, signing | The schema is ready in `db/`, but wiring it in is stage 3. Needs OQ-R4, OQ-D6, OQ-D8, OQ-A8. |
| Stage 4: Layer 2 judge, probes | Needs a pinned model and a rubric. |
| Stage 5: API, Policy engine, CI adapter | Thresholds are customer configuration and not defined (OQ-PO1). |
| Stage 6: Registry adapters | Target registries not chosen (OQ-R5). |
| A frontend or website | Handled separately by the other founder. |
| Creating cloud resources (Supabase, Google Cloud, Cloudflare) | Needs the founders' accounts and credentials. |
| Choosing a license | A founder decision. |

Leave the placeholder modules for later stages (`contract_builder.py`,
`evidence_store.py`, `policy_engine.py`, `api.py`) in place and unchanged,
apart from a one-line docstring naming the stage they belong to.

---

## 7. What only the founders can do

List these in the final report as next steps for the humans:

- Decide the open questions recorded under "Needs decision".
- Confirm or reject each proposal recorded in `IMPLEMENTATION_NOTES.md`.
- Provide a real sandbox agent for the first pilot.
- Create the Postgres database when stage 3 begins, and keep its credentials
  out of the repository.
- Choose a license.
- Turn on branch protection for `main` and require CI to pass.
