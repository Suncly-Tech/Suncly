# Stage 4 brief: Judge Layer 2

What was built on 2026-10-07 for ROADMAP stage 4, definition of done items 1
to 3 (the Layer 2 judge; no probes), what the founders decided, how the key
is kept apart, and what is still missing. Conventions are as in
[ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers to
[SCHEMA.md](../SCHEMA.md), which this work did not change.

## Decisions (founders, 2026-10-07)

Recorded in [IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md), section 3:

- **OQ-A1:** the customer's model key lives in a separate judge subprocess,
  never in the Runner or the core process.
- **OQ-D4:** model id, rubric version and hash, criterion text, prompt, raw
  response and rationale go into the per-run evidence document.
- **OQ-D7:** each model check is an object in `criteria.model_checks`:
  `name`, `criterion`, `expected`, `pass_rule`. Unknown keys are refused.
- **OQ-PO6:** results are counted per test case.
- **Model:** one pinned model id from the configuration, no default.
- **Rubric:** a versioned global frame plus the criterion text.

## What runs

1. Layer 1 (`core/judge.py::judge_run`) decides every check it can. A model
   check is left undecided.
2. Layer 2 runs only when every other check passed and model checks remain
   (`undecided_model_checks`). It never runs for a failed run, an unreachable
   agent or an unreadable transcript, and never for a criterion Layer 1 can
   decide.
3. For each model check the core builds the prompt from the rubric frame
   (`core/rubric.py`, version `1`) and the criterion, with the agent input and
   the agent response embedded as data, and asks the `ModelJudge` port
   (`ports/model_judge.py`) for the pinned model.
4. The core interprets the raw answer: one JSON object `{"answer", "rationale"}`
   in the expected shape. The pass rule maps the answer to pass or fail. No
   model configured, a model failure, a timeout, an answer attributed to
   another model, or malformed output all give `inconclusive`, never `pass`.
5. The run is stored with `judge_layer` `model` and the rationale; the
   evidence document carries `judgement.layer_2` with the model id, the
   rubric version and hash, and per check the criterion, prompt, raw response,
   answer and rationale. The signed payload format is unchanged: the
   provenance is bound through the document hash it already carries.

## The judge subprocess

`python -m suncly.judge.process`, started by
`adapters/judge_subprocess.py::SubprocessModelJudge`:

- **From-scratch environment.** The child gets `SUNCLY_JUDGE_MODEL_KEY`,
  forwarded by name from the parent's environment, plus `SYSTEMROOT` where
  Python needs it. Nothing else: not the agent credential, not
  `DATABASE_URL`, not proxy settings.
- **One key variable.** Named in `judge/key.py` and nowhere else in the
  source; a test enforces it. The Runner's `SUNCLY_AGENT_AUTHORIZATION` stays
  the Runner's.
- **One endpoint.** A request hook refuses any scheme, host or port other
  than the configured `judge_endpoint`; redirects are not followed; the
  environment's proxies are ignored; https is required except for loopback.
- **Redaction.** The key is removed from the answer text, the model id and
  every error before the response leaves the subprocess; stderr is never
  surfaced. A test runs a real subprocess against a loopback endpoint that
  echoes the key back and checks every file of the report, the transcript
  storage, the file store and the progress events.
- **Wire shape: the Anthropic Messages API.** Added 2026-10-07 and verified
  against the official documentation that day; the facts are in
  [IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md), section 4.
  `POST <endpoint>`, where the endpoint is
  `https://api.anthropic.com/v1/messages`, with the headers
  `Authorization: Bearer <key>`, `anthropic-version: 2023-06-01` and
  `content-type: application/json`. The body carries the pinned `model`, a
  `max_tokens` ceiling of 4096, the prompt as the one `user` message, and
  `output_config.format` with a JSON schema that admits exactly the object the
  rubric asks for (`answer` and `rationale`, no other key). `temperature` `0`
  is sent to the models whose API still accepts sampling parameters, up to the
  4.6 generation (`judge/process.py::accepts_sampling`); from 4.7 on the API
  rejects any non-default value, so later models run with their defaults. No
  thinking or effort setting is sent, because each is rejected by some model.
  The answer is a `message` object: its `model` is what the core compares with
  the pin, its text block holds the JSON. Only `stop_reason` `end_turn` is a
  complete answer; a refusal (`refusal`, with its `stop_details` category), a
  truncated answer (`max_tokens`) or any other stop is an error, and so
  `inconclusive`, never `pass`. An HTTP error is reported with the API's
  `error.type`, `error.message` and `request_id`. The existing HTTP client is
  used; no SDK or other dependency was added. Another provider replaces
  `build_request`, `request_headers` and `read_answer` in `judge/process.py`
  and nothing else.

## Configuration (DR-004)

| Setting | Env var | Meaning |
|---|---|---|
| `judge_model` | `SUNCLY_JUDGE_MODEL` | The one pinned model id. No default. |
| `judge_endpoint` | `SUNCLY_JUDGE_ENDPOINT` | The one URL the subprocess may talk to. No default. For the Anthropic API: `https://api.anthropic.com/v1/messages`. |
| `judge_rubric_version` | `SUNCLY_JUDGE_RUBRIC_VERSION` | Must be `1`, the rubric this build carries. |
| `judge_timeout_s` | `SUNCLY_JUDGE_TIMEOUT_S` | Seconds per model question (default 60). |
| (not a setting) | `SUNCLY_JUDGE_MODEL_KEY` | Read only by the judge subprocess. |

The three settings are set together or not at all; a partial configuration,
or a rubric version this build does not carry, is refused before anything
runs. Without them Layer 2 is off: every run with a model check is
`inconclusive`, `judge_layer` stays `deterministic`, and the report's "What
was NOT tested" says so. A new rubric frame ships under a new version and
takes effect only when the configuration names it.

## Judge model: a recommendation, not a default

The model id stays a configuration value with no default (DR-004). The
recommendation for the judge is **`claude-haiku-4-5-20251001`**, the cheapest
current model that is adequate for the task:

- The task is one criterion per question, answered yes/no or 0 to 10, with the
  agent input and response embedded as data: a classification-grade job, and
  the strict JSON schema fixes the shape of the answer.
- $1 per million input tokens and $5 per million output tokens: half the price
  of Claude Sonnet 5.5 ($2 / $10) and a quarter of Claude Opus 5.5 ($4 / $20).
- It is the one current model that gives the judge the most deterministic
  settings the API offers: `temperature` `0` is accepted, and thinking is off
  unless a request turns it on, so the only output is the JSON object. Every
  later model rejects non-default sampling and thinks by default (adaptive
  thinking, which Claude Opus 5.5 and Claude Fable 5.1 cannot turn off and
  Claude Sonnet 5.5 can only lower to `between_tools`).
- The id is a dated, pinned snapshot; the alias `claude-haiku-4-5` resolves to
  it. Pin the dated id.

Known limit: its retirement commitment runs to 15 October 2026, the earliest
of the current models (status active, no deprecation announced; Anthropic
gives at least 60 days' notice). The next step up is `claude-sonnet-5-5`
(retirement not sooner than 28 September 2027) at twice the price, with
adaptive thinking on and no sampling control. A model change is a
configuration change (DR-004); the live smoke test
(`tests/live/test_messages_api_live.py`) checks a candidate with one real
question.

## Proven by tests

`tests/unit/test_judge_layer_2.py` (68 tests) covers pass, fail,
inconclusive on failure, timeout, malformed output, wrong model and no model;
Layer 2 only for what Layer 1 cannot decide; the provenance in the evidence
document and the rationale on the run; DR-004; the criteria format; the
subprocess's environment, endpoint restriction and redaction; the Messages API
wire shape against a loopback fake that answers in the verified shape,
including HTTP errors, a refusal, a truncated answer, an unexpected stop, an
answer from another model, a thinking block and a message without text; and
that the key appears in no evidence, report or log. No test calls the real
API: `tests/live/test_messages_api_live.py` asks it one question through the
real subprocess and runs only when `SUNCLY_JUDGE_MODEL_KEY` and
`SUNCLY_JUDGE_MODEL` are set, so CI skips it. `tests/unit/test_architecture.py`
adds the judge layer, the single-module rule for the key variable and the
rule that the judge package never imports the Runner. The proofs are listed
under the ticked items in [ROADMAP.md](ROADMAP.md).

## Not done, and known limits

- The adapter for the Anthropic Messages API exists, but no call to the real
  API has been made from this repository: the live smoke test needs a key and
  runs only by hand. Item 6 of stage 4 stays unticked until it has passed.
- Determinism has a ceiling set by the API: `temperature` `0` reaches only
  models up to the 4.6 generation. On later models the API offers no sampling
  control, the judge runs with the model's default thinking, and the thinking
  tokens count against the 4096-token ceiling; reaching it is `inconclusive`.
- No probes (items 4 and 5).
- Prompt injection: the agent's response is embedded in the prompt as data,
  and the frame says so, but a model can still be misled by it. The rubric
  frame is the one place to harden, under a new version.
- The parent process forwards the key variable to the child without reading
  it into a setting, but the variable is in the parent's environment block
  because the operator put it there. Running the subprocess under a
  different user or in a container would remove even that.
