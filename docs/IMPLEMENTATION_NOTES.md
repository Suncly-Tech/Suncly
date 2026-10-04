# Implementation notes

What the code decided, where, and how to change it. No open question is
resolved here; only the founders resolve them. Every proposal below is behind
one named function, constant or configuration value.

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md) and `OQ-…` to the open questions listed in the
documents. "NEEDS DECISION" marks a choice the documents gave no proposal for.

## 1. Proposals implemented

| Open question | What was implemented | Where | How to change it |
|---|---|---|---|
| OQ-A2 sandbox | Nothing runs unless the caller declares the endpoint a sandbox (`--sandbox`). The Runner refuses undeclared targets a second time. Suncly cannot verify a sandbox. | `core/attestation.py` (`SandboxDeclarationMissingError`), `runner/process.py` | Replace the flag with a real check once one exists. |
| OQ-A3 redaction | The Runner removes its credential (and its token part), sensitive header keys, documented token patterns and `key=value` secrets, over the whole transcript as data. | `runner/redaction.py`: `SENSITIVE_KEYS`, `PATTERNS`, `KEY_VALUE_PATTERN`, `Redactor` | Edit the lists; every rule is named in `transcript.redaction.rules`. |
| OQ-A4 protocol | A2A 1.0 over JSON-RPC only; the first `supportedInterfaces` entry with `JSONRPC` and `1.0` is used. Tasks are followed by polling `GetTask`; no streaming, no push notifications; an interrupted state is recorded, never answered. | `core/cards.py::select_interface`, `runner/protocol.py::execute_run` | Add a transport per binding behind `ports/a2a.py`; extend `select_interface`. |
| OQ-A7 card hash | `card_hash` = `sha256:` + SHA-256 of the RFC 8785 form of the card without `signatures`. The initial fetch is done by `CardService` on behalf of the use case; the end-of-run re-fetch by the Orchestrator. | `domain/card.py::compute_card_hash`, `core/cards.py`, `core/orchestrator.py::_recheck_card` | One function; the scheme is also printed in every report. |
| OQ-A8 signature | Ed25519 over the RFC 8785 payload of schema §11; encoded `ed25519:<base64url>`; `signing_key_id` = `ed25519-` + 16 hex of SHA-256(public key); the public key is embedded in `result.json`. | `core/signing.py`: `build_payload`, `sign_payload`, `key_id_for`, `SIGNATURE_PREFIX` | Change the constants and the two functions. |
| OQ-A9 mappings | Exit code 0 means completed and signed, never approved. CI and registry adapters are out of scope. | `cli/exit_codes.py` | Implement `adapters/ci.py` and `adapters/registry.py` in stages 5 and 6. |
| OQ-A11 fail-safe defaults | Unparsable card → no records, visible error; no skills → not attestable; redaction failure → transcript withheld, run not recorded; `TASK_STATE_UNSPECIFIED` is not final; unreadable transcript → `inconclusive`; evidence write failure → run not recorded; signing failure → not `completed`; the NOT-tested categories. | `domain/card.py`, `core/cards.py`, `runner/process.py`, `domain/a2a.py`, `core/judge.py`, `core/orchestrator.py`, `core/policy_engine.py`, `core/coverage.py` | Each is one branch next to the rule it implements. |
| OQ-D1 types | `uuid` ids, `numeric` (Python `Decimal`) costs, `text` for `raw_json`, as proposed. | `domain/models.py`, `db/migrations/0001_initial_schema.sql` | Model fields and a new migration. |
| OQ-D3 run key | `run.attempt` is the repetition number from 1; (`attestation_id`, `test_case_id`, `attempt`) is unique in both stores; retries reuse the key. | `domain/models.py::RunKey`, `domain/rules.py::check_run_insert`, `adapters/file_store.py`, `adapters/postgres/store.py` | The key is the run file name in the file store and `UNIQUE run_key` in Postgres. |
| OQ-D5 versions | `contract.version` counts per card version. | `core/contract_builder.py::ContractService.create_draft` | One `max()+1` expression. |
| OQ-D6 attestation record | `completed` = all runs judged, card unchanged, decision recorded, signed. Only `status`, `cost_total`, `finished_at`, `signature`, `signing_key_id` change; `cancelled` gets no decision; `attestation.card_version_id` equals the contract's. | `domain/rules.py`, `domain/models.py` | The rule functions in `domain/rules.py`; the database mirrors them. |
| OQ-D7 formats | `input` is `{"text": …}` or `{"parts": […]}`; `criteria` holds the Layer 1 checks; unknown keys are refused. `skill_id` is nullable for probes. | `domain/criteria.py`: `TestInput`, `Criteria` | Add fields to `Criteria`; the Judge reads them in `core/judge.py::judge_run`. |
| OQ-D9 hash seen before | A card hash seen before reuses its `card_version`, and so its approved contract. `card_version` records never change. | `core/cards.py::ensure_card_version` | Create a new record instead of reusing. |
| OQ-D10 latency | `latency_ms` runs from sending the message to the final task state (or the direct Message); null when nothing answered. | `runner/protocol.py` (`elapsed_ms`) | One helper. |
| OQ-F3 unreachable | No connection → `unreachable` → `inconclusive`. A timeout after the connection → `timeout` → `fail` on the latency check. The latency limit is judged; the run timeout stops the Runner. | `runner/http_transport.py`, `core/judge.py::judge_run` | Change the classification in `_rpc_result` and the first branches of `judge_run`. |
| OQ-F5 re-fetch fails | The attestation ends `failed` with no decision. | `core/orchestrator.py::execute` (`recheck.outcome == "unavailable"`) | One branch. |
| OQ-F7 signing without a decision | `failed` and `invalidated` attestations are signed with `"decision": null` in the payload. | `core/attestation.py::_sign_without_decision` | Remove the call to leave them unsigned. |
| OQ-PO5 policy_version | `decision.policy_version` is the placeholder `unconfigured`; without a policy the only outcome is `flag`. | `core/policy_engine.py::POLICY_VERSION_UNCONFIGURED`, `decide` | Replace `decide` with the configured engine in stage 5. |
| OQ-R1 Orchestrator | A minimal Orchestrator inside the process: expansion, run keys, concurrency, retries, timeouts, budget, re-fetch. | `core/orchestrator.py` | Replace the thread pool with the job table when it arrives. |
| OQ-R2 test cases | A deterministic drafter (one test case per declared example, up to a cap) and a hand-written contract file. No model. | `core/contract_builder.py::DeterministicDrafter`, `domain/contract_file.py` | Implement `ports/drafter.py::ContractDrafter` with a model (stage 2). |
| OQ-R4 signing before the Policy engine | Both exist in this version: the Policy engine signs completed attestations after deciding; the use case signs failed and invalidated ones without a decision. | `core/policy_engine.py`, `core/attestation.py` | See OQ-F7 above. |
| OQ-R6 report | The file report is the first Report adapter: `result.json`, redacted transcripts, Markdown and offline HTML. | `adapters/report/` | Add renderers next to `markdown.py` and `html.py`. |
| OQ-P5 CLI | `--runs` is repetitions per test case, default 5; budget defaults to 2 x planned runs; a CLI attestation has trigger `manual`; exit codes are documented in [API.md](API.md). | `core/config.py` (`DEFAULT_RUNS`, `DEFAULT_BUDGET_FACTOR`), `cli/exit_codes.py` | Constants. |

## 2. Needs decision

Choices the documents gave no proposal for. Each is behind the named place.

| Topic | What the code does | Where | Why this way |
|---|---|---|---|
| A2A client (A2A-T7) | A minimal JSON-RPC client of Suncly's own, behind the `A2ATransport` port, instead of `a2a-sdk`. | `runner/protocol.py`, `runner/http_transport.py`, `ports/a2a.py` | The SDK does support 1.0 (see section 3), but it brings protobuf, google-api-core and json-rpc into the one process that holds credentials. The Runner's job in this version is `SendMessage` plus `GetTask` polling. Switching means one new adapter for the port. CLAUDE_CODE_BRIEF.md 3.1 would have preferred the SDK. |
| Cost unit (OQ-D1) | Every attempt costs 1; `budget_limit` and `cost_total` count attempts, retries included; `cost_total` can exceed the sum of `run.cost`. | `domain/transcript.py::COST_PER_ATTEMPT`, `core/orchestrator.py::_Budget` | A2A has no price signal; counting calls is the one unit that is always true. |
| Agent identity (OQ-P2, OQ-P5) | `agent.id` = UUID v5 of the card URL under a fixed namespace; `owner` defaults to `unspecified`; `risk_level` defaults to `high`. | `core/cards.py::AGENT_ID_NAMESPACE`, `agent_id_for_url`; `core/attestation.py::DEFAULT_OWNER`, `DEFAULT_RISK_LEVEL` | Nothing outside the seven entities is stored; `high` is the most restrictive level. |
| When the attestation record is created (OQ-F1) | Only after the contract is approved. There is no `queued` attestation waiting for approval. | `core/attestation.py::attest` | This is the alternative OQ-F1 itself raises; it avoids an attestation pointing at a draft. |
| Superseding (OQ-D5) | Approving version N moves older approved versions of the same card version to `superseded`. | `core/contract_builder.py::ContractService.approve` | Otherwise "the approved contract" of a card version is ambiguous. |
| Uncovered skills in contract files (OQ-R2, invariant 1) | A drafted contract may leave a skill without examples untested; it is listed as not testable and reported. A hand-written file must list such skills under `skills_without_test_case`, or it is refused. | `core/contract_builder.py::draft_from_contract_file`, `DeterministicDrafter` | Reconciles the brief's refusal rule with the prompt's "never invent input". |
| Who signs failed and invalidated attestations (OQ-F7) | The attestation use case, not the Policy engine, which signs only after deciding. | `core/attestation.py::_sign_without_decision` | The Policy engine makes no decision for them (schema §11). |
| In-flight attempts at the budget stop (OQ-F4) | Attempts already started finish and are charged; nothing new starts once `cost_total` reaches `budget_limit`, checked before every attempt. | `core/orchestrator.py::_Budget.charge` | Charging before starting keeps `cost_total` from exceeding the limit. |
| Judging rule for media types | A `text` part without `mediaType` is treated as `text/plain`. | `domain/a2a.py::TEXT_PART_DEFAULT_MEDIA_TYPE`, `part_media_type` | The spec gives no default; this is Suncly's rule, not the spec's. |
| Deployment key on first use | `suncly attest` and `suncly demo` create the Ed25519 key if none exists, and say so. `suncly keys init` creates it explicitly. | `core/attestation.py::_signer`, `adapters/file_keys.py` | A first run should not fail for lack of a key. |
| Plain http for loopback | Card URLs and agent endpoints must be https, except loopback addresses, where local sandboxes run. | `runner/http_transport.py::require_https_or_loopback` | A2A §7.1 requires TLS in production; the demo runs on 127.0.0.1. |
| Minimum Python | 3.12 minimum; CI tests 3.12, 3.13 and 3.14. | `pyproject.toml`, `.github/workflows/ci.yml` | 3.14 is the newest every dependency ships wheels for; 3.12 is what the founders' machines run. |
| Migration state | No bookkeeping table; `suncly db migrate` reads `information_schema` and applies the file only to an empty database. | `adapters/postgres/migrate.py` | An eighth table would break "seven entities are the complete list". |
| Evidence document | The stored transcript file holds the transcript and the judgement; its hash is what the signature covers. | `core/judge.py::JudgeService.evidence_document` | The checks are evidence too. |

## 3. Verified facts

| Fact | Checked | Source |
|---|---|---|
| A2A-T7: the Python SDK `a2a-sdk` 1.2.1 (released 2026-09-30) implements A2A protocol 1.0, with a compatibility mode for 0.3. Its 1.0.0 release (2026-04-20) carries the v0.3 → v1.0 migration guide. Python 3.10+. | 2026-10-04 | [README](https://github.com/a2aproject/a2a-python), [CHANGELOG](https://github.com/a2aproject/a2a-python/blob/main/CHANGELOG.md), [PyPI](https://pypi.org/pypi/a2a-sdk/json) |
| The current A2A specification release is v1.0.1 (2026-05-28); the protocol version is `1.0` (Major.Minor, A2A §3.6). | 2026-10-04 | [github.com/a2aproject/A2A releases](https://github.com/a2aproject/A2A/releases) |
| JSON-RPC binding: method names `SendMessage`, `GetTask` (PascalCase, A2A §5.3, §9.1); `Content-Type: application/json`; `A2A-Version` as an HTTP header (§9.2); the result of `SendMessage` holds `task` or `message` (§9.4.1). | 2026-10-04 | [specification.md at v1.0.1](https://github.com/a2aproject/A2A/blob/v1.0.1/docs/specification.md) |
| Blocking by default: without `returnImmediately` the operation waits for a terminal or interrupted state (§3.2.2); a client polls with `GetTask` otherwise (§3.1.3). | 2026-10-04 | same |
| Task states, terminal and interrupted sets, `Role`, `Part` (one of `text`, `raw`, `url`, `data`), REQUIRED fields of `Task`, `Message`, `Artifact`, `SendMessageRequest`, `GetTaskRequest`. | 2026-10-04 | [a2a.proto at v1.0.1](https://github.com/a2aproject/A2A/blob/v1.0.1/specification/a2a.proto) |
| Agent Card discovery at `/.well-known/agent-card.json` (§8.2); card signing canonicalizes with RFC 8785 and excludes `signatures` (§8.4.1). | 2026-10-04 | specification.md v1.0.1 |
| Dependency versions at the time of writing: httpx 0.28.1, pydantic 2.13.5, click 8.5.0, rfc8785 0.1.4, cryptography 50.0.2, psycopg 3.3.6, jsonschema 4.26.0, pytest 9.1.1, pytest-cov 7.1.0, ruff 0.16.10, mypy 2.4.0. All ship wheels or pure-Python packages for Python 3.12 to 3.14. | 2026-10-04 | PyPI JSON API |
| Python 3.14.8 is the newest release; `actions/checkout` v5 and `actions/setup-python` v6 are current major lines; `postgres:17` is the current Supabase-compatible image line. | 2026-10-04 | endoflife.date, GitHub releases, Docker Hub |

Protocol details the documents mark `TODO: verify against spec` and that this
version handles without taking a side:

- **A2A-T1** (no skill identifier on requests): a test case targets a skill
  through its declared example; the result is attributed to `test_case.skill_id`
  by the test case, not by the protocol.
- **A2A-T2 / A2A-T3** (stream closing; blocking): the Runner uses no streams,
  sends a plain `SendMessage`, and polls `GetTask` whenever the returned task
  is neither terminal nor interrupted, so both readings of the spec work.
- **A2A-T4** (`security` vs `securityRequirements`): the card parser keeps
  both as opaque fields and reads neither.
- **A2A-T5** (empty `skills`): a card with no skills is reported as not
  attestable and runs nothing.
- **A2A-T6** (`SubscribeToTask` HTTP verb): not used; JSON-RPC only.

## 4. Document problems found

Contradictions or errors noticed while implementing. None was fixed silently.

1. **Definition of done, item 9.** `git grep -n -i -E "D1|Cloudflare|wrangler"`
   can never be empty while the documents contain the open-question ids
   `OQ-D1`, `OQ-D10` and `OQ-D11`. The check that passes is the word-boundary
   form: `git grep -n -i -E "(^|[^-])D1\b|Cloudflare|wrangler" -- . ':!CLAUDE_CODE_BRIEF.md'`.
2. **CLAUDE_CODE_BRIEF.md 3.1 vs the MVP prompt** on the A2A SDK: the brief
   says to use the SDK if it supports 1.0; the prompt leaves the choice open.
   See "A2A client" above.
3. **CLAUDE_CODE_BRIEF.md 3.4 vs the MVP prompt** on skills without a test
   case: the brief refuses such a contract; the prompt wants the drafter to list
   the skill as not testable. See "Uncovered skills" above.
4. **FLOW.md OQ-F1** proposes an attestation that waits in `queued` for
   approval; the implementation creates the attestation only after approval,
   which OQ-F1 lists as the alternative.
5. **ROADMAP.md and ARCHITECTURE.md** say stage 1 results are not signed and
   carry no decision; this MVP signs every attestation and records a `flag`
   decision, as the prompt requires. ROADMAP.md's status says so.
6. **ARCHITECTURE.md (Orchestrator)** proposes that the Orchestrator performs
   the initial card fetch; the code performs it in `core/cards.py`, called by
   the attestation use case before the Orchestrator exists for that run. The
   end-of-run re-fetch is the Orchestrator's.
7. **The A2A specification v1.0.1 contradicts itself** on whether `SendMessage`
   blocks (§3.1.1, §3.3.3 vs §3.2.2), on stream closing at interrupted states
   (§3.1.2 vs §11.7), on the field name `security` vs `securityRequirements`,
   and on the HTTP verb of `SubscribeToTask`. These stay as A2A-T2, T3, T4 and
   T6 in ARCHITECTURE.md.
8. **CLAUDE_CODE_BRIEF.md 2.1** asks for "a pinned minimum Python version" and
   to "pick the newest Python version that all dependencies support"; the two
   cannot both be the minimum. The minimum is 3.12 and the newest tested is 3.14.
