# Real-agent interoperability report

Suncly tested against official A2A reference agents, before any further
infrastructure is built. Date: 2026-10-06. Suncly at `origin/main` afcd48a,
branch `feat/real-agent-interop-and-oss-eval`.

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md), "spec §N" to the A2A specification at tag
v1.0.1, "proto" to `specification/a2a.proto` at the same tag, and `OQ-…` to
open questions. Every protocol claim was checked against the specification,
not against an SDK or a sample. Where something could not be verified it is
marked **uncertain**.

## Method

- Every agent ran locally on `127.0.0.1`, on its own port, in its own
  virtual environment or build, started from the official repository at the
  commit named in its section. No production endpoint was contacted.
- Suncly was run as a user runs it: `python -m suncly.cli.main --home <dir>
  attest <card-url> --sandbox --approve-as interop-tester --runs 3
  --reports-dir <dir> --json`, plus `--export-draft` to see the drafted
  contract, plus a hand-written contract file where the draft could not run.
- Independently of Suncly, every agent was probed with `curl`: the raw Agent
  Card, a 1.0 `SendMessage` with `A2A-Version: 1.0`, a 0.3-shaped
  `message/send`, and `GetTask`, so the wire format is on record.
- Sources of protocol truth: `a2aproject/A2A` at tag v1.0.1 (commit 3303592,
  2026-05-28), compared with `main` (84c1e39, 2026-10-06) and with tag v0.3.0.
  Reference code: `a2aproject/a2a-samples` main 6603ba3 (2026-08-04) and the
  commit before the 1.0 migration, `a2aproject/a2a-tck` main 263b9cf
  (2026-09-01), `a2aproject/a2a-python` at cbb2d84 (2026-10-06).
- Classification of each observation, one of: **protocol conformance issue**
  (one side violates a MUST or SHOULD of the spec), **Suncly interoperability
  bug** (Suncly misbehaves on spec-valid input), **version mismatch** (the
  agent speaks A2A 0.3), **malformed agent behaviour** (the agent's output is
  not what its card or the spec says), **works as intended** (Suncly's
  documented rules produced the predicted verdicts, including correct
  `fail`s), **uncertain**.
- Suncly was not changed to make any agent pass. The three changes made are
  listed under "Suncly bugs fixed", each with the regression test that
  reproduces it.

## Summary

| Agent | Official | A2A version | What happened | Classification |
|---|---|---|---|---|
| a2a-samples `helloworld` on a2a-sdk 1.2.2 | yes | 1.0 | Card parsed, 2 test cases drafted, 6 runs, all `pass`, signed, exit 0 | works as intended |
| a2a-tck reference SUT (Python) | yes | 1.0 | Card parsed; the one skill has no `examples`, so the default run is refused (exit 3, documented); `--export-draft` crashed (exit 1); with a contract file 9 runs: 6 `pass`, 3 correct `fail` | Suncly bug (export crash); otherwise works as intended |
| a2a-samples `helloworld` (0.3-era source) on a2a-sdk 0.3.26 | yes | 0.3 | Card refused at parse time (exit 3); the refusal did not name the cause | version mismatch; Suncly diagnostic bug |
| a2a-sdk 1.2.2 server with 0.3 compatibility mode (helloworld agent) | yes | 1.0 and 0.3 on one endpoint | Hybrid card parsed, 1.0 interface selected, 6 runs, all `pass`, signed, exit 0; the 0.3 path was observed only through raw probes | works as intended |
| a2a-samples `multitenancy` (three tenants on one host) | yes | 1.0 | Three cards at tenant sub-paths parsed; 18 runs over path-bearing interface URLs, all `pass`; `suncly verify` passes | works as intended |
| a2a-samples `sign_and_verify_agent_card` | yes | 1.0 | Signed card parsed; `card_hash` stable although the agent re-signs on every fetch; 3 runs, all `fail` on `output_modes` because the card declares `"text"` instead of a media type | works as intended; agent card conformance issue |
| a2a-samples Go `helloworld` (a2a-go v2.3.1) | yes | 1.0 | Card parsed; 6 runs, all `fail` on `response_present` because the agent returns its answer in `status.message` and no artifact; the Go SDK's JSON was consumed without any structural problem | works as intended; agent deviates from a spec SHOULD |
| JavaScript agent on `@a2a-js/sdk` | partly (official SDK, see section) | pending | pending | pending |

Spec gap found by reading, confirmed by the spec and fixed: the Runner never
sent the `tenant` routing field that spec §8.3.2 requires when the selected
interface declares one (see "Suncly bugs fixed").

## Protocol facts verified

| Topic | Fact | Source (v1.0.1) |
|---|---|---|
| Release status | v1.0.1 is the latest release (tag commit 3303592, 2026-05-28). `main` adds §7.6.4 (in-task authorization scope), renames the §4.3.1 heading, corrects the §8.5 sample card to `securityRequirements`, and allows `hostname:port` for gRPC URLs in a proto comment. No method name, task state, Part key, header rule or discovery path changed. | `git tag`; `git diff v1.0.1 main` |
| Protocol version | `Major.Minor` only, `"1.0"`; patch numbers SHOULD NOT appear in cards or requests. | §3.6 |
| Discovery | Well-known URI `https://{server_domain}/.well-known/agent-card.json`. `/.well-known/agent.json` appears nowhere in the spec at v1.0.1, main or v0.3.0; it belongs to v0.2.x. | §8.2, §14.3 |
| Card REQUIRED fields | `name`, `description`, `supportedInterfaces`, `version`, `capabilities`, `defaultInputModes`, `defaultOutputModes`, `skills`. | proto `AgentCard` |
| Interfaces | `url`, `protocolBinding`, `protocolVersion` REQUIRED; `tenant` optional. Clients MUST pick the first supported entry and MUST set `tenant` in every request when the entry declares one, omitting it otherwise. | §8.3.1, §8.3.2; proto `SendMessageRequest.tenant`, `GetTaskRequest.tenant` |
| Skills | `id`, `name`, `description`, `tags` REQUIRED; `examples`, `inputModes`, `outputModes`, `securityRequirements` optional. | proto `AgentSkill` |
| Methods | PascalCase: `SendMessage`, `GetTask`, … Unknown method: JSON-RPC -32601. | §5.3, §9.1, §9.5 |
| SendMessage result | `SendMessageResponse`, a oneof: JSON `{"task": {...}}` or `{"message": {...}}`. `GetTask` returns the Task directly. | proto; §9.4.1 |
| Message reply | An agent MAY answer with a direct Message "for simple interactions"; the spec does not say how a client must judge it. Messages SHOULD NOT carry task outputs; outputs SHOULD be artifacts. | §3.1.1, §3.7 |
| Blocking | Blocking by default: without `returnImmediately` the server MUST wait for a terminal or interrupted state. | §3.2.2 |
| Task states | `TASK_STATE_*` strings; terminal: COMPLETED, FAILED, CANCELED, REJECTED; interrupted: INPUT_REQUIRED, AUTH_REQUIRED. | proto `TaskState`; §3.1.1 |
| Version header | Clients MUST send `A2A-Version`; servers MUST treat an empty value as 0.3 and MUST answer an unsupported version with `VersionNotSupportedError` (-32009). | §3.6.1, §3.6.2, §5.4, §9.2 |
| Parts | exactly one of `text`, `raw`, `url`, `data`; `mediaType` optional on every part; `Message.parts` and `Artifact.parts` must not be empty; `Task.artifacts` is not REQUIRED. | proto `Part`, `Artifact`, `Task`; §5.7 |

Suncly's constants in `domain/a2a.py` and the card model in `domain/card.py`
match every row. Two mismatches were found: the missing `tenant` (fixed) and
a docstring in `domain/card.py` citing §4.4.2 for `AgentInterface`, which is
§4.4.6 in v1.0.1 (fixed).

### A2A 0.3 versus 1.0 on the wire

Only the differences Suncly's JSON-RPC path meets. Sources: spec v0.3.0
(`docs/specification.md`, `specification/json/a2a.json`) and v1.0.1.

| Aspect | 0.3 | 1.0 |
|---|---|---|
| Card endpoint fields | top-level `url` and `preferredTransport` (REQUIRED), optional `additionalInterfaces[{url, transport}]` | `supportedInterfaces[{url, protocolBinding, protocolVersion, tenant?}]` (REQUIRED) |
| Card protocol version | top-level `protocolVersion`, full string (default `"0.3.0"`) | per interface, `Major.Minor` |
| Extended card flag | top-level `supportsAuthenticatedExtendedCard` | `capabilities.extendedAgentCard` |
| Method names | `message/send`, `tasks/get`, … | `SendMessage`, `GetTask`, … |
| Message | `{kind: "message", messageId, role: "user", parts: [{kind: "text", text}]}` | `{messageId, role: "ROLE_USER", parts: [{text}]}` |
| Result | the Task or Message object itself, discriminated by `kind` | wrapper `{"task": …}` or `{"message": …}` |
| Task states | `submitted`, `working`, `input-required`, `completed`, `canceled`, `failed`, `rejected`, `auth-required`, `unknown` | `TASK_STATE_SUBMITTED`, … |
| Version header | none defined | `A2A-Version` required |
| Blocking | `configuration.blocking`, non-blocking implied | `returnImmediately`, blocking by default |

## Agents tested

### 1. a2a-samples `helloworld` (Python) on a2a-sdk 1.2.2

- **Repository:** `a2aproject/a2a-samples`, `samples/python/agents/helloworld`,
  main 6603ba3 (2026-08-04). Official. Its `requirements.txt` pins
  `a2a-sdk==1.1.0`; it was run on 1.2.2 (PyPI, 2026-10-05) without any code
  change. Only the port was changed in a copy (9999 to 9901).
- **Protocol version:** 1.0. `supportedInterfaces[0]` is
  `{"url": "http://127.0.0.1:9901", "protocolBinding": "JSONRPC", "protocolVersion": "1.0"}`.
- **Started:** `uv venv`, install `requirements.txt` then `a2a-sdk==1.2.2`,
  `python __main__.py`. Card answered after about 4 s.
- **Card discovery:** `GET /.well-known/agent-card.json` 200 (602 bytes; the
  server's weak `ETag` equals the SHA-256 Suncly computes as `card_hash`).
  `/.well-known/agent.json` 404, which is consistent with spec §8.2.
- **Card parsing:** parsed; `card_hash`
  `sha256:0794a39a…87db`; no spec-required field missing; interface selected:
  JSONRPC 1.0. Draft: 2 test cases, one per example of skill `echo_bot`
  (`"hi"`, `"how are you"`), criteria `final_state TASK_STATE_COMPLETED`,
  `latency_limit_ms 10000`, `response_present`, `output_modes ["text/plain"]`.
- **Declared skills:** `echo_bot` ("Echo Bot", examples `hi`, `how are you`,
  input and output modes `text/plain`).
- **Invocation:** each run sent one `SendMessage` with `A2A-Version: 1.0`;
  each answer was `{"result": {"task": {... "status": {"state": "TASK_STATE_COMPLETED"} ... "artifacts": [{"parts": [{"text": "Hello, World! I have received your request (hi)", "mediaType": "text/plain"}]}]}}}`.
  The task was terminal in the first response, so `GetTask` was never needed.
  Raw probes: 0.3 `message/send` gives -32601 "Method not found"; a request
  without `A2A-Version` gives -32009 "A2A version '0.3' is not supported by
  this handler. Expected version '1.0'." (spec §3.6.2 behaviour); `GetTask`
  returns the Task object directly, as the proto says.
- **Interpretation:** 6 runs, every Layer 1 check true (`valid_schema`,
  `final_task_state`, `latency_limit` 7 to 16 ms, `response_present`,
  `output_modes`). Verdicts 6 `pass`, 0 `fail`, 0 `inconclusive`; card
  unchanged at the re-check; decision `flag` (no policy configured); signed;
  exit 0. A second attestation with `accept_direct_message: true` in a
  contract file gave the same counts: the agent answers with a Task, so that
  branch was never exercised.
- **Pass or failure point:** none; end to end.
- **Classification:** works as intended. Note for the record: the task brief
  assumed this sample answers with a direct Message. At this commit it
  completes a Task with one artifact (`agent_executor.py` uses `TaskUpdater`).
  Whether an older revision answered with a Message: **uncertain**.
- **Evidence:** `scratchpad/runs/py-helloworld-1x/` (card, probes, two
  report folders with `result.json`, transcripts, `report.md`).

### 2. a2a-tck reference System Under Test (Python)

- **Repository:** `a2aproject/a2a-tck`, `sut/a2a-python/sut_agent.py`, main
  263b9cf (2026-09-01). Official; generated from the TCK's Gherkin scenarios.
  Its `pyproject.toml` wants `a2a-sdk[http-server,grpc,sqlite]>=0.3.0` from a
  local sibling clone that does not exist here, so a2a-sdk 1.2.2 from PyPI was
  used; all its imports resolve against 1.2.2.
- **Protocol version:** 1.0 on all three declared interfaces (JSONRPC at
  `http://127.0.0.1:9902`, HTTP+JSON at `/a2a/rest`, GRPC on 9903).
- **Started:** `SUT_HOST=127.0.0.1:9902 GRPC_PORT=9903`, through a 40-line
  launcher that only rebinds the SUT's hard-coded `0.0.0.0` and `[::]`
  listeners to loopback and then runs `sut_agent.py` unchanged.
- **Card discovery:** 200, 734 bytes, all eight spec-required fields present.
  `capabilities.streaming` true, `pushNotifications` false.
  `defaultInputModes` and `defaultOutputModes` are `["text"]`, which is not a
  media type (proto defines these fields as media types).
- **Card parsing:** parsed; `card_hash` `sha256:8ede6cd1…2541`; interface
  selected: JSONRPC 1.0. Drafting then found no usable example: the single
  skill `tck` declares none, and Suncly never invents input.
  - Default run: exit 3 (refused) with the documented message "The draft has
    no test cases, so there is nothing to approve or run. No declared skill
    has a usable example: tck. Add examples to the card's skills, or write a
    contract file (see docs/API.md)." Nothing was sent to the agent.
  - `--export-draft`: exit 1 (internal error) with a raw pydantic
    `ValidationError` ("List should have at least 1 item"). **Suncly bug**,
    fixed below.
  - Contract file with 3 hand-written test cases, `--runs 3`: 9 runs, exit 0.
- **Declared skills:** `tck` ("TCK Conformance", no examples, no modes).
- **Invocation:** every run sent one `SendMessage`; every answer was a Task in
  `TASK_STATE_COMPLETED` with **no artifacts**, the text only in
  `status.message.parts` ("Unhandled messageId prefix: <uuid>"), and the user
  message in `history`. Latencies 6 to 15 ms. Raw probes: no header gives
  -32009; `A2A-Version: 0.5` gives -32009; `message/send` gives -32601;
  `GetTask` with `historyLength: 0` omits history (spec §3.2.4); unknown task
  id gives -32001. The SUT selects its scenario by `messageId` prefix
  (`tck-complete-task`, `tck-input-required`, `tck-artifact-text`, …);
  Suncly's `messageId` is always a fresh UUID, so only the default branch is
  reachable from Suncly.
- **Interpretation:** test case 1 (`"hi"`, drafter-equivalent criteria):
  0 `pass`, 3 `fail`; the failing check is `response_present` ("0 output
  part(s) with content"), because the SUT returns no artifact and the Judge
  counts artifact parts of a Task as the output (criteria.py, a2a.py
  `output_parts`), consistent with spec §3.7. Test cases 2 and 3 (criteria
  without `response_present`, with `required_fields` on
  `/status/message/parts/0/text` and `/history`, and a `response_schema`):
  3 `pass` each. Totals 6 `pass`, 3 `fail`, 0 `inconclusive`; decision
  `flag`; signed; card unchanged.
- **Pass or failure point:** drafting (documented refusal), the export helper
  (Suncly bug), otherwise end to end.
- **Classification:** Suncly bug for the export crash. The nine verdicts are
  works as intended. Agent-side observations: the card's `["text"]` modes are
  a **conformance issue of the SUT's card**; two scenario branches drift from
  a2a-sdk 1.2.2 (`tck-message-response` is rejected by the SDK with -32006,
  `tck-reject-task` surfaces as -32603 instead of a `TASK_STATE_REJECTED`
  task), which is **malformed agent behaviour relative to the current SDK**,
  unreachable from Suncly and classified **uncertain** as to which SDK commit
  the SUT was generated against.
- **Evidence:** `scratchpad/runs/tck-sut-python/` (card, `contract.json`,
  probes, report folder, launcher).

### 3. a2a-samples `helloworld` (0.3-era source) on a2a-sdk 0.3.26

- **Repository:** `a2aproject/a2a-samples` at c2f26a4 (2026-03-23), the last
  commit of `samples/python/agents/helloworld` before its migration to the
  1.0 API (b5af0df, 2026-03-26). Official. Run on a2a-sdk 0.3.26 (PyPI,
  2026-04-09), the last 0.3 release, with the `[http-server]` extra. Three
  edits to the copy: port 9999 to 9903, the card's self URL to
  `http://127.0.0.1:9903/`, and the bind host from `0.0.0.0` to `127.0.0.1`
  (the environment refuses non-loopback binds).
- **Protocol version:** 0.3. The card has top-level `"protocolVersion":
  "0.3.0"`, `"url"`, `"preferredTransport": "JSONRPC"`,
  `"supportsAuthenticatedExtendedCard": true`, and no `supportedInterfaces`.
- **Card discovery:** the 0.3.26 SDK serves the identical card at both
  `/.well-known/agent-card.json` and `/.well-known/agent.json` (200,
  466 bytes). The second path is the SDK's deprecated alias, not the spec's.
- **Card parsing:** refused on both paths, exit 3: "The Agent Card does not
  have the structure Suncly needs. Validation reported: supportedInterfaces:
  Field required. …". Correct outcome; the message named the missing 1.0
  field but not the cause, although the card declares it. **Suncly diagnostic
  bug**, fixed below. No records were created.
- **Declared skills:** `hello_world` (examples `hi`, `hello world`); an
  extended card at `/agent/authenticatedExtendedCard` adds
  `super_hello_world`.
- **Invocation:** Suncly sent nothing. Raw probes: 1.0 `SendMessage` with
  `A2A-Version: 1.0` gives -32601 "Method not found" (the 0.3 SDK has no
  `A2A-Version` handling, so -32009 cannot occur); 0.3 `message/send` gives
  `{"result": {"kind": "message", "messageId": "…", "parts": [{"kind": "text", "text": "Hello World"}], "role": "agent"}}`,
  a direct Message object without the 1.0 wrapper; `message/send` with a 1.0
  body gives -32602 ("Input should be 'agent' or 'user'" for
  `role: ROLE_USER`); 1.0 `GetTask` gives -32601; 0.3 `tasks/get` gives
  -32001.
- **Interpretation:** no runs. Had the Runner reached the agent, the observed
  answers predict `PROTOCOL_ERROR` on the method name and, even past that, on
  the result envelope, so every run would be `fail` on `valid_schema`.
- **Pass or failure point:** card parsing.
- **Classification:** version mismatch (the agent is a correct 0.3 agent;
  Suncly is a 1.0 client by documented design). Older-version compatibility
  would be required to attest it. The exact incompatibilities are the rows of
  the table "A2A 0.3 versus 1.0 on the wire", all observed here except the
  task-state strings (this agent answers with a Message).
- **Evidence:** `scratchpad/runs/py-helloworld-03/` (both cards, six probes,
  refusals).

### 4. a2a-sdk 1.2.2 server in 0.3 compatibility mode

- **Repository:** the `helloworld` sample of a2a-samples main 6603ba3 on
  a2a-sdk 1.2.2, with the SDK's documented server-side compatibility switch
  (`docs/migrations/v1_0/README.md`, "Supporting v0.3 Clients", in
  `a2aproject/a2a-python` at cbb2d84): a second `AgentInterface` with
  `protocol_version='0.3'` at the same URL, and
  `create_jsonrpc_routes(..., enable_v0_3_compat=True)`. Official SDK and
  sample; the three-line change follows the SDK's own
  `samples/hello_world_agent.py`. Port 9904.
- **Protocol version:** 1.0 and 0.3 on one JSON-RPC endpoint. The SDK
  dispatches by method name (0.3 names such as `message/send` go to its 0.3
  adapter, PascalCase names to the 1.0 handlers) and then validates
  `A2A-Version` per path: the 1.0 path requires major version 1, the 0.3 path
  requires 0.3, with an empty header read as 0.3 (spec §3.6.2).
- **Card discovery:** 200, 812 bytes. Because a 0.3 interface is declared,
  the SDK also injects the legacy top-level fields `url`,
  `preferredTransport`, `protocolVersion: "0.3"` and
  `supportsAuthenticatedExtendedCard` into the served card (a hybrid card).
  `/.well-known/agent.json` 404.
- **Card parsing:** parsed; `card_hash` `sha256:e454f0dc…525d`. The four
  legacy fields are kept as unknown fields (spec §5.7) and are part of the
  hash. `select_interface` chose the first entry, JSONRPC 1.0. Draft: the
  same two test cases as in section 1.
- **Declared skills:** `echo_bot`, as in section 1.
- **Invocation:** identical to section 1 on Suncly's side (one `SendMessage`
  per run with `A2A-Version: 1.0`, a completed Task with a `text/plain`
  artifact, 7 to 17 ms). Raw probes of the 0.3 path: `message/send` with a
  0.3 body and no header, or with `A2A-Version: 0.3`, answers a 0.3-shaped
  Task (`"kind": "task"`, `"state": "completed"`, parts with `kind`, no
  `mediaType`); `message/send` with `A2A-Version: 1.0` answers -32603 with
  the text of a `VersionNotSupportedError`, where spec §9.5 assigns -32009
  (the 1.0 path of the same server does answer -32009 for a header-less
  request). A 1.0 `SendMessage` without the header is refused with -32009
  although a 0.3 interface exists at the URL, because the empty header means
  0.3 and `SendMessage` is not a 0.3 method.
- **Interpretation:** 6 `pass`, 0 `fail`, 0 `inconclusive`; card unchanged;
  decision `flag`; signed; exit 0.
- **Pass or failure point:** none.
- **Classification:** works as intended. Two SDK-side observations, neither
  affecting Suncly, which always sends the header: the -32603 instead of
  -32009 on the compatibility path is a **conformance issue of the SDK**
  against spec §9.5 (**uncertain** whether its maintainers would count a
  0.3-format response as exempt); the hybrid card's top-level
  `protocolVersion: "0.3"` would mislead a client that reads that field
  instead of `supportedInterfaces`. Suncly reads `supportedInterfaces`, so
  the fix for section 3 was written to fire only when that field is absent.
- **Evidence:** `scratchpad/runs/py-sdk-compat-mode/` (card, `src-diff.patch`,
  nine probes, report folder).

### 5. a2a-samples `multitenancy` (Python)

- **Repository:** `a2aproject/a2a-samples`, `samples/python/agents/multitenancy`,
  main 6603ba3 (added in #634, 2026-07-14). Official. `requirements.txt` pins
  `a2a-sdk==1.1.0`; the sample does not start until the SDK's `http-server`
  extra is installed too (its JSON-RPC routes import `sse_starlette`), a
  packaging gap of the sample. Started with
  `A2A_BIND_HOST=127.0.0.1 A2A_PORT=9905 A2A_PUBLIC_URL=http://127.0.0.1:9905`,
  no other change. No model key needed.
- **Protocol version:** 1.0 on every card.
- **Card discovery:** the sample routes tenants by URL sub-path, not by the
  `tenant` field: `/.well-known/agent-card.json` at the root is 404; the cards
  are at `/hello/…`, `/palindrome/…` and `/reverse/…`, each with an interface
  URL ending in the tenant path (for example `http://127.0.0.1:9905/hello`).
  Spec §8.2 allows pre-configured card URLs. No card sets
  `AgentInterface.tenant`.
- **Card parsing:** all three parsed (`hello`
  `sha256:8201022f…7a10`); interface JSONRPC 1.0 selected; `tenant` parsed as
  null. Because `agent.id` derives from the card URL, the three tenants became
  three agents.
- **Declared skills:** `hello` (examples `hi`, `hello there`), `palindrome`
  (`racecar`, `hello`), `reverse` (`hello world`, `agents talking to agents`).
- **Invocation:** one `SendMessage` per run to the full interface URL
  including its path; the origin check compares scheme, host and port only,
  so a path-bearing URL is preserved (server log: `POST /hello 200`). Every
  answer a completed Task with a `text/plain` artifact, 7 to 16 ms. Probes:
  `GetTask` returns the Task directly; `message/send` gives -32601; a 1.0
  request to the root path gives HTTP 404 (routing is purely by path).
- **Interpretation:** 18 runs, every check true; 18 `pass`; all three
  attestations completed, decision `flag`, signed, card unchanged;
  `suncly verify` on the `hello` report passes all eight checks.
- **Pass or failure point:** none.
- **Classification:** works as intended. The sample does not exercise the
  `tenant` field, so the Runner's omission of it (fixed in this task) did not
  affect these runs; the agent confirmed the gap by inspection and it was
  fixed from the spec.
- **Evidence:** `scratchpad/runs/py-multitenancy/` (three cards, probes,
  three report folders, `verify.stdout`).

### 6. a2a-samples `sign_and_verify_agent_card` (Python)

- **Repository:** `a2aproject/a2a-samples`,
  `samples/python/agents/sign_and_verify_agent_card`, main 6603ba3. Official.
  `a2a-sdk==1.1.0`. Only the port changed in a copy (9999 to 9906). The sample
  generates an ephemeral P-256 key at start and signs its card (JWS, `ES256`,
  `jku` pointing at its own `/public_keys.json`); no external key or model.
- **Protocol version:** 1.0.
- **Card discovery:** 200. The card carries a `signatures` array that **grows
  by one entry on every fetch** (2, 3, 4, … 8 observed): the SDK's signer
  appends to the shared card object it serves. All other fields are
  byte-identical between fetches. The JWS header has `typ: "JWT"` where spec
  §8.4.2 says it SHOULD be `JOSE`. `GetExtendedAgentCard` answers without
  authentication, which spec §13.3 says MUST be required (not exercised by
  Suncly; from a raw probe).
- **Card parsing:** parsed; `card_hash` `sha256:bb2016b4…0e98`, identical for
  fetches with 2, 3 and 4 signatures, because the hash excludes `signatures`
  as spec §8.4.1 excludes them from the signed content. The end-of-run
  re-check reported "unchanged", so the attestation ended `completed`, not
  `invalidated`. All three served signatures verify (with the served public
  key) against exactly Suncly's RFC 8785 canonical form of the card, so for
  this card Suncly's canonicalization equals what the official SDK signs.
- **Declared skills:** `reminder` (example `Verify me!`); the extended card
  adds `reminder-please`, which Suncly does not fetch.
- **Invocation:** one `SendMessage` per run, completed Task with a
  `text/plain` artifact ("Verify me! (Verify me!)"), 12 to 16 ms. Probes as in
  section 1 (-32601 for `message/send`, -32009 without the header).
- **Interpretation:** 3 runs, checks `valid_schema`, `final_task_state`,
  `latency_limit`, `response_present` true; `output_modes` **false**:
  "declared ['text']; offending media types: ['text/plain']". 0 `pass`,
  3 `fail`; completed, `flag`, signed, exit 0.
- **Pass or failure point:** the `output_modes` check, on the agent's side.
- **Classification:** works as intended; the fails are correct. The card's
  `defaultOutputModes` is `["text"]`, which is not a media type (the proto
  defines these fields as media types), while the agent emits `text/plain`.
  That is a **conformance issue of the sample's card**. Observation on
  Suncly's hash: it applies §8.4.1 rules 2 and 3 (RFC 8785, drop
  `signatures`) but not rule 1 (default-value removal); for this card the two
  forms coincide. `card_hash` is a change detector, not a signature verifier,
  so this matters only if Suncly ever verifies card signatures (recorded
  under open questions).
- **Evidence:** `scratchpad/runs/py-signed-card/` (three fetches,
  `verify_sig.out`, probes, report folder).

### 7. a2a-samples `helloworld` (Go, a2a-go v2.3.1)

- **Repository:** `a2aproject/a2a-samples`, `samples/go/agents/helloworld`,
  main 6603ba3 (sample commit 1f03e5d, 2026-07-06). Official. `go.mod` pins
  `github.com/a2aproject/a2a-go/v2 v2.3.1` (the module proxy has v2.6.0;
  the declared version was built). The port 9999 is hard-coded; a copy was
  changed to 9907 (six lines). Built with `go build`; the binary also runs an
  interactive stdin client, so stdin was held open. No model key needed.
- **Protocol version:** 1.0 over JSONRPC (`a2a.Version` is `"1.0"` in a2a-go).
- **Card discovery:** 200, 602 bytes, all eight spec-required fields,
  lowerCamelCase names, skill `echo_bot` with examples `hi`, `how are you`,
  modes `text/plain`.
- **Card parsing:** parsed; `card_hash` `sha256:61504c4c…582c`; JSONRPC 1.0
  selected; two test cases drafted; card unchanged at the re-check.
- **Declared skills:** `echo_bot`.
- **Invocation:** one `SendMessage` per run; every answer HTTP 200 with
  `{"result": {"task": {"id": …, "contextId": …, "history": […], "status": {"message": {"parts": [{"text": "Hello, World! I have received your request (hi)"}], "role": "ROLE_AGENT"}, "state": "TASK_STATE_COMPLETED", "timestamp": "…Z"}}}}`
  and **no `artifacts` key**. Latencies 5 to 10 ms. Cross-language
  serialization observed: enums as strings (`TASK_STATE_COMPLETED`,
  `ROLE_USER`), the `{"task": …}` wrapper on `SendMessage`, the bare Task on
  `GetTask`, camelCase field names, no `mediaType` on text parts (omitted when
  empty), `artifacts` omitted when empty, nanosecond timestamps, JSON-RPC
  errors carrying `google.rpc.ErrorInfo` details. Suncly's Judge found every
  Task well-formed. Raw probes: `message/send` gives -32601; **a request
  without `A2A-Version`, and one with `A2A-Version: 0.3`, are both answered
  as 1.0** (the server does not read the header).
- **Interpretation:** every run `valid_schema`, `final_task_state`,
  `latency_limit`, `output_modes` true (the last vacuously) and
  `response_present` **false** ("0 output part(s) with content"). 0 `pass`,
  6 `fail`; completed, `flag`, signed, exit 0.
- **Pass or failure point:** the `response_present` check, on the agent's
  side: the sample's executor yields a status update with the text and never
  an artifact, although the sample's README shows an artifact in its expected
  output (**uncertain** which SDK version that output was captured with).
- **Classification:** works as intended. The fails are a correct application
  of Suncly's documented rule, which follows spec §3.7 (outputs SHOULD be
  artifacts); the agent deviates from that SHOULD. Agent-side conformance
  issue: the server ignores `A2A-Version`, where spec §3.6.2 says an empty
  value MUST be read as 0.3 and an unsupported version MUST get
  `VersionNotSupportedError`; no non-test code in a2a-go v2.3.1 reads the
  header. Suncly always sends the header, so it is unaffected. The
  `status.timestamp` uses nanoseconds where §5.6.1 says millisecond precision
  SHOULD be used; Suncly does not parse timestamps.
- **Evidence:** `scratchpad/runs/go-helloworld/` (card, six probes,
  `src-diff.txt`, `build.log`, report folder).

### 8. JavaScript agent on `@a2a-js/sdk`

Pending.

## Findings by class

### Protocol conformance issues

1. **Suncly, fixed:** the Runner omitted `tenant` from `SendMessage` and
   `GetTask` when the selected `AgentInterface` declares one. Spec §8.3.2
   rule 4 and proto `SendMessageRequest.tenant`, `GetTaskRequest.tenant`
   make this a MUST. It affected no run here, because none of the tested
   cards declares a tenant on its JSONRPC interface, but it is a MUST and the
   fix is a pass-through.
2. **Agent cards (a2a-tck SUT and `sign_and_verify_agent_card`):**
   `defaultInputModes` and `defaultOutputModes` are `["text"]`, not media
   types; the proto defines these fields as media types and every example in
   the spec uses forms such as `text/plain`. On the signed-card sample this
   made all three runs fail the `output_modes` check, correctly: the agent
   emits `text/plain`. On the SUT it was not triggered (no artifacts).
3. **SDK (a2a-sdk 1.2.2, 0.3 compatibility path):** a 0.3-shaped request with
   `A2A-Version: 1.0` is answered with -32603 where spec §9.5 assigns -32009
   to `VersionNotSupportedError`. **Uncertain** whether the maintainers count
   a 0.3-format response as exempt. Does not affect Suncly.
4. **SDK (a2a-sdk 1.1.0 card signer):** the served card's `signatures` array
   grows by one entry per fetch, and the JWS header uses `typ: "JWT"` where
   §8.4.2 says SHOULD `JOSE`. Suncly's hash is unaffected.
5. **Agent (`sign_and_verify_agent_card`):** `GetExtendedAgentCard` answers
   without authentication; spec §13.3 says the extended card MUST require it.
   Observed by raw probe only; Suncly does not fetch extended cards.
6. **SDK (a2a-go v2.3.1 server):** does not read `A2A-Version`; a header-less
   request and `A2A-Version: 0.3` are both served as 1.0, where spec §3.6.2
   requires 0.3 semantics or `VersionNotSupportedError`. Does not affect
   Suncly.
7. **Agents (a2a-tck SUT default branch, Go `helloworld`):** the task's only
   output is in `status.message`, with no artifact; spec §3.7 says outputs
   SHOULD be artifacts. Suncly's `response_present` fails such runs
   (OQ-RA1).

### Suncly interoperability bugs

1. `attest --export-draft` crashed with an internal error (exit 1) on a
   spec-valid card whose skills declare no `examples` (`examples` is optional
   in the proto). Fixed: the export path now gives the same documented
   refusal (exit 3) as the run path.
2. A 0.3 Agent Card was refused with a message about a missing field instead
   of its cause. Fixed: the refusal now names the card's `protocolVersion`
   and the 1.0 field it lacks, and says that Suncly attests 1.0 interfaces
   only. No 0.3 support was added.
3. The `tenant` omission above.

### Version mismatch

- a2a-samples `helloworld` on a2a-sdk 0.3.26 (section 3). See "A2A 0.3
  decision".

### Malformed agent behaviour

- a2a-tck SUT: two scenario branches no longer work on a2a-sdk 1.2.2
  (section 2). Unreachable from Suncly; recorded for completeness.
- Sample packaging: `multitenancy` does not start from its own
  `requirements.txt` (missing `sse-starlette`); `helloworld` pins
  `a2a-sdk==1.1.0` but runs unchanged on 1.2.2. Neither affects Suncly.

### Uncertain

- Which a2a-python commit the TCK SUT was generated against (its dependency
  points at a local clone).
- Whether an earlier revision of the Python `helloworld` sample answered with
  a direct Message, as the task brief assumed.
- The GitHub release date of A2A v1.0.1 (the tag commit is 2026-05-28, the
  CHANGELOG says 2026-05-26).

### Observations recorded, not changed

These are judgement calls of Suncly's documented rules, listed so the
founders can decide; none was changed in this task.

- A direct Message reply (spec §3.1.1) fails the drafted default criteria
  (`accept_direct_message` is false). A contract file can accept it. The spec
  does not prescribe a client policy; §3.7 says outputs SHOULD be artifacts.
- The Judge counts only artifact parts as a Task's output
  (`response_present`). An agent that puts its answer in
  `status.message` only (the TCK SUT's default branch) fails that check.
- Suncly's `messageId` is always a fresh UUID and no test case can set it;
  agents that route on `messageId` cannot be exercised (TCK SUT).
- `part_has_content` treats `{"data": null}` as empty, although the proto
  allows a null `data` value.
- `ROLES` excludes `ROLE_UNSPECIFIED` (proto value 0); since `role` is
  REQUIRED this is defensible.
- `select_interface` requires `protocolVersion == "1.0"` exactly. A card
  declaring `"1.0.1"` is itself non-conformant (§3.6 SHOULD NOT), but would be
  refused rather than normalized. a2a-python ignores the patch version when
  choosing an interface (commit cbb2d84).
- `TASK_STATE_UNSPECIFIED` is polled until the timeout, as the documented
  proposal says (OQ-A11).

## Suncly bugs fixed

| Bug | Fix | Regression test |
|---|---|---|
| `tenant` not sent (spec §8.3.2) | `RunJob.tenant` carries the selected interface's value; the Orchestrator fills it; the Runner adds `tenant` to the `SendMessage` and `GetTask` params when set and omits it otherwise | `tests/unit/test_runner.py::test_the_tenant_of_the_selected_interface_is_sent_in_every_request`, `tests/unit/test_orchestrator_and_service.py::test_the_tenant_of_the_selected_interface_reaches_the_runner` |
| `--export-draft` internal error on a card without usable examples | the export path raises the same `ContractError` as `create_draft` before building the file | `tests/unit/test_orchestrator_and_service.py::test_export_draft_of_a_card_without_usable_examples_is_refused_not_an_internal_error` |
| 0.3 card refused with a generic structure message | `parse_agent_card` recognizes the pre-1.0 card markers (top-level `url`, `preferredTransport`, `protocolVersion`, no `supportedInterfaces`) and names the declared protocol version in the refusal | `tests/unit/test_card.py::test_a_0_3_card_is_refused_with_its_protocol_version_named` |

Also corrected: the `domain/card.py` docstring citation for `AgentInterface`
(§4.4.6, not §4.4.2). No Runner dependency changed, no credential path moved,
no secret handling or host restriction weakened.

## A2A 0.3 decision

**Which tested agents require older-version compatibility:** the Python
`helloworld` sample on a2a-sdk 0.3.26 (section 3). Every other agent tested is
1.0. Among the official repositories: all four SDK main lines (a2a-python
1.2.2, a2a-js 1.3.0, a2a-go v2.6.0, a2a-java 1.4.0.Final) are protocol 1.0
with opt-in 0.3 compatibility layers; the TCK and a2a-inspector are 1.0 tools;
but the sample corpus is still mostly 0.3-written: 28 of 39 Python sample
directories pin `a2a-sdk>=0.3.x` and use the 0.3 API, 3 of 5 JavaScript
agents pin `@a2a-js/sdk ^0.3.3`, all Java sample agents use the 0.3 groupId.
No public directory of live A2A endpoints with fetchable cards was found, so
the share of public agents still on 0.3 **cannot be measured** from here, and
probing live endpoints is out of bounds.

**Exactly what is incompatible:** every row of the table "A2A 0.3 versus 1.0
on the wire". For Suncly's path: the card shape (parse fails on
`supportedInterfaces`), the method names (`SendMessage` gets -32601), the
request body (`ROLE_USER` and part shape rejected with -32602), the result
envelope (no `task`/`message` wrapper), the task-state strings, and the
absence of `A2A-Version` handling on the 0.3 side.

**How much code:** a card normalizer in `domain/card.py` that maps `url`,
`preferredTransport`, `additionalInterfaces` and `protocolVersion` to
`supportedInterfaces` entries (about 40 lines; a2a-python's `card_resolver.py`
does the same); a protocol-dialect value in the pure Runner logic
(`runner/protocol.py`) selected from `job.protocol_version`, supplying method
names, request builders, result unwrapping (`kind` discriminator, with the
fallback for servers that omit it) and a normalizer of states and parts to the
1.0 vocabulary before the transcript is written (about 60 lines); constants
per version in `domain/a2a.py`; `select_interface` accepting `0.3` as a second
choice; a 0.3 mock agent for the end-to-end tests (about 100 lines); and the
card, runner, judge and end-to-end test matrix doubled. The `A2ATransport`
port, `http_transport.py`, redaction and the credential boundary need no
change: `RunJob.protocol_version` already flows to the `A2A-Version` header.

**Isolation:** yes. If the Runner normalizes `final_task_state` and
`final_response` to the 1.0 vocabulary (keeping the raw exchanges verbatim in
`exchanges`), the Judge, the criteria format, the drafter, the reports and the
signed payload are untouched. The seam is a dialect object inside the pure
`runner/protocol.py`, not the transport port.

**Security and maintenance implications:** two wire dialects inside the one
process that holds credentials. The added code is data mapping, with no new
network path, so the attack surface grows by parser complexity only;
redaction is version-agnostic. The test matrix doubles, and the 0.3 long tail
(`kind` sometimes missing, patch versions in `protocolVersion`, hybrid cards
from a2a-js and a2a-java that carry both shapes) must be tracked while the
SDKs themselves are still fixing their compatibility layers. Reports must say
which dialect was exercised (`protocol_version` is already in the transcript).

**Recommendation: later.** Do not implement 0.3 now. Reasons: every
official SDK ships 1.0 and the conformance tooling Suncly will import from
(TCK, Promptfoo's A2A provider) is 1.0-only; the 0.3 corpus found is samples,
not agents a customer would submit for approval; the one measurement that
would justify the cost (how many agents customers actually submit with 0.3
cards) cannot be made yet; and a second dialect inside the credential-holding
Runner is a permanent audit cost. What this task did instead: the version
mismatch is now reported precisely (fix 2), so the first customer agent that
is 0.3-only will show up as such in Suncly's output. Revisit when a pilot
customer presents a 0.3-only agent, or when the 0.3 share can be measured.

## Minimal Layer 2 check

Not added. The task allowed one Layer 2 behavioural check only if all Slice 5
prerequisites exist. None does:

- behavioural test format v2: absent (`domain/criteria.py` is the Layer 1
  format; unknown keys are refused);
- behavioural categories: absent (`test_case.kind` has the schema's four
  values and nothing else groups behaviours);
- model drafter: absent (`DeterministicDrafter` only; `ports/drafter.py` is
  the port it would implement);
- model judge: absent (no model call anywhere in `src/`; `judge_layer =
  model` is never produced; `model_checks` always yield `inconclusive`).

Where it would go is documented in [CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)
("Judge Layer 2"), and the rule it must follow is in
[ARCHITECTURE.md](ARCHITECTURE.md) (Judge, "Fails safely").

## Slice status found

| Slice | Plan item | Found on `origin/main` (afcd48a) | Status |
|---|---|---|---|
| 1 | tenancy, identity, migration 0002, store scoping | No tenant or organisation concept in models, stores or CLI. `db/migrations/0002_rls_and_search_path.sql` enables row level security without policies and fixes the guards' `search_path`; it is not a tenancy migration. The only `tenant` in the code is the A2A `AgentInterface.tenant` card field. | not started |
| 2 | HTTP API (FastAPI), OpenAPI, workflow endpoints | `src/suncly/api.py` is a one-line placeholder; no web framework dependency. | not started |
| 3 | Postgres job system, outbox, worker, recovery | `core/orchestrator.py` is an in-process thread pool; no job table. | not started |
| 4 | Runner security, scoped secrets, SSRF hardening | Present: own process, one target origin enforced in one request hook with redirects disabled, https required except loopback, one credential reader, redaction before the transcript leaves. Absent: per-agent or per-tenant scoped secrets (one environment variable), SSRF rules beyond the origin check (a declared sandbox at an `https://` private address is accepted). | partial |
| 5 | behavioural format v2, categories, model drafter, model judge | see "Minimal Layer 2 check" | not started |

## Signed payload

The payload (`core/signing.py`, `payload_version` 1) holds `attestation_id`,
`card_hash`, `contract {id, version}`, `results` per test case (`pass`,
`fail`, `inconclusive` counts), `transcript_hashes` per run (SHA-256 of the
stored evidence document) and `decision {outcome, policy_version}` or null.

- **The fixes in this task need no payload change.** The `tenant` fix changes
  the content of future transcripts (and so their hashes), not the payload
  format; the other two fixes happen before any attestation record exists.
  `suncly verify` on the reports produced in this task passes.
- **Import-mode external evidence would need a payload change.** A TCK or
  Promptfoo result is neither a Suncly `run` (which requires a `test_case_id`,
  an `attempt` and `judge_layer` in `deterministic | model`) nor a per-test-case
  count of the contract. Carrying tool name, tool version, SHA-256 of the raw
  file and the normalized verdict under the signature requires:
  - *required change:* a `payload_version` 2 with an `external_evidence`
    array (tool name, version, file hash, normalized verdict, and the id of
    whatever record holds it), and a place for that record in the data model;
  - *why the current payload is insufficient:* its only evidence slots are
    per-test-case counts and per-run document hashes, both tied to the seven
    entities, which have no entity, `kind` or `judge_layer` for third-party
    results (schema §3: "These seven entities are the complete list");
  - *backward compatibility:* every existing `result.json` carries
    `payload_version: 1` and must keep verifying; `core/verify.py` currently
    does not read `payload_version`, so a version switch has to be added
    before a second format exists;
  - *verification impact:* `suncly verify` must check the imported file's
    hash against the signed hash and must not count imported verdicts into
    the per-test-case totals it recomputes from runs;
  - *migration and re-evaluation:* a new entity or enum value means migration
    0003 and a change to schema §3 or §11, which only the founders can make;
    existing attestations need no re-signing, because version 1 stays valid
    for them.

  Nothing of this was changed. It is listed for approval.

## Database

No migration was added. Nothing in this task needed a database change;
0001 and 0002 are untouched, and 0003 stays free.

## Open questions

- **OQ-RA1** Should the default drafted criteria accept a direct Message reply
  (spec §3.1.1) for skills whose card promises no artifacts, or stay strict as
  today? The spec gives no client rule.
- **OQ-RA2** Should a test case be allowed to set `messageId` (or a prefix),
  so agents that route on it, such as the TCK SUT, can be exercised? Today
  the Runner always generates a fresh UUID.
- **OQ-RA3** Should `select_interface` ignore a patch component in
  `protocolVersion` (as a2a-python now does), or keep refusing cards that
  violate §3.6's SHOULD NOT?
- **OQ-RA4** When to revisit 0.3 support: at the first pilot agent with a
  0.3-only card, or at a measured share of such cards.
- **OQ-RA5** Where imported third-party evidence lives in the data model and
  in the signed payload (see "Signed payload").
- **OQ-RA6** `card_hash` applies spec §8.4.1 rules 2 and 3 but not rule 1
  (default-value and empty-field removal before canonicalization). As a change
  detector that is fine; if Suncly ever verifies card signatures it must apply
  rule 1 too (OQ-A7).
- **OQ-RA7** Should the drafter reject, or merely flag, a card whose
  `defaultOutputModes` are not media types (two official samples declare
  `["text"]`)? Today such a card yields deterministic `fail`s that are
  correct but tell the reviewer little.
