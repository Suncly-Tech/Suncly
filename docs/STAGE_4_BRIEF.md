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
- **Wire shape, a placeholder.** `POST <endpoint>` with
  `{"model": <id>, "input": <prompt>}` and `Authorization: Bearer <key>`;
  the answer is `{"model": <id>, "output": <text>}`. No real provider speaks
  this. A real provider adapter replaces `call_endpoint` in
  `judge/process.py` and nothing else; none was added here, by instruction,
  and no dependency was added.

## Configuration (DR-004)

| Setting | Env var | Meaning |
|---|---|---|
| `judge_model` | `SUNCLY_JUDGE_MODEL` | The one pinned model id. No default. |
| `judge_endpoint` | `SUNCLY_JUDGE_ENDPOINT` | The one URL the subprocess may talk to. No default. |
| `judge_rubric_version` | `SUNCLY_JUDGE_RUBRIC_VERSION` | Must be `1`, the rubric this build carries. |
| `judge_timeout_s` | `SUNCLY_JUDGE_TIMEOUT_S` | Seconds per model question (default 60). |
| (not a setting) | `SUNCLY_JUDGE_MODEL_KEY` | Read only by the judge subprocess. |

The three settings are set together or not at all; a partial configuration,
or a rubric version this build does not carry, is refused before anything
runs. Without them Layer 2 is off: every run with a model check is
`inconclusive`, `judge_layer` stays `deterministic`, and the report's "What
was NOT tested" says so. A new rubric frame ships under a new version and
takes effect only when the configuration names it.

## Proven by tests

`tests/unit/test_judge_layer_2.py` (47 tests) covers pass, fail,
inconclusive on failure, timeout, malformed output, wrong model and no model;
Layer 2 only for what Layer 1 cannot decide; the provenance in the evidence
document and the rationale on the run; DR-004; the criteria format; the
subprocess's environment, endpoint restriction and redaction; and that the
key appears in no evidence, report or log. `tests/unit/test_architecture.py`
adds the judge layer, the single-module rule for the key variable and the
rule that the judge package never imports the Runner. The proofs are listed
under the ticked items in [ROADMAP.md](ROADMAP.md).

## Not done, and known limits

- No real provider adapter and no call to a real model. Item 6 of stage 4
  stays unticked.
- No probes (items 4 and 5).
- Prompt injection: the agent's response is embedded in the prompt as data,
  and the frame says so, but a model can still be misled by it. The rubric
  frame is the one place to harden, under a new version.
- The parent process forwards the key variable to the child without reading
  it into a setting, but the variable is in the parent's environment block
  because the operator put it there. Running the subprocess under a
  different user or in a container would remove even that.
