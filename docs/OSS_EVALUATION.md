# Evaluation of external tools for import-mode evidence

Suncly may later accept the result files of two external tools as evidence
about an agent: the A2A Technology Compatibility Kit (`a2aproject/a2a-tck`)
and Promptfoo (`promptfoo/promptfoo`). This document records what was
verified about each on 2026-10-06, before any integration exists. Nothing in
this document is implemented; see "Intended architecture" at the end for the
constraints any later implementation must keep.

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md), and "spec §N" to the A2A specification at tag
v1.0.1. Every fact below names its source; where a source could not be
reached, the fact is marked **uncertain**. The GitHub REST API was not
reachable from the environment used for this evaluation, so repository
statistics come from the cloned git history and release metadata from the
package registries.

## Summary

| | a2a-tck | Promptfoo |
|---|---|---|
| Licence | Apache-2.0 (`LICENSE`; `pyproject.toml` references the file) | MIT (`LICENSE`, `package.json`, npm metadata) |
| Licence acceptable (Apache-2.0 or MIT) | yes | yes |
| Latest stable release | none; tags `1.0.0.alpha1` (2026-05-13) and `1.0.0.alpha2` (2026-05-27); `pyproject.toml` says `1.0.0`; not on PyPI | 0.124.0, published 2026-10-06 (npm); 0.x line |
| Latest commit seen | `263b9cf`, 2026-09-01 | `832173001f`, 2026-10-06 |
| Activity, last 90 days | 11 commits, in one burst on 2026-08-31 and 2026-09-01; 15 authors over the project's life | 959 commits on `main`, 76 author identities, about a third from dependency bots |
| A2A protocol version | 1.0 (vendored spec pinned to A2A tag `v1.0.0`; sends `A2A-Version: 1.0`; PascalCase methods) | 1.0 in its A2A provider, HTTP+JSON binding only |
| Result file | `reports/compatibility.json` (plus HTML, pytest-html and JUnit XML) | `promptfoo eval -o results.json` (plus yaml, xml, jsonl, csv, html) |
| Importable without running the tool | yes: plain JSON, no code, no credentials | yes: plain JSON, no code, no credentials |
| Credential needed to import | none | none |
| Tool version inside the file | no | optional `metadata.promptfooVersion` |
| Would running it need the Runner boundary | yes: it calls the agent under test and opens an inbound webhook listener | yes: it calls the agent and a grader model, and needs their keys |
| Suitable for import mode | yes, with strict schema validation and operator-supplied tool version | yes, with strict schema validation and a second redaction pass |

## a2a-tck

Evaluated from a clone of `https://github.com/a2aproject/a2a-tck` at `main`
(`263b9cf`, 2026-09-01) with tags fetched, and from the PyPI index.

### Licence, release, maintenance

- **Licence:** Apache License 2.0. `LICENSE` is the Apache 2.0 text;
  `pyproject.toml` line 14 declares `license = {file = "LICENSE"}` (a file
  reference, not an SPDX string); the README says "Apache License 2.0". The
  metadata was aligned in commit `cd34e1f` (2026-08-31, "fix: align package
  license metadata (#199)").
- **Releases:** no stable release. Tags: `v0.2.3` (2025-07-09), `v0.2.5`
  (2025-07-18), `0.3.0.alpha` to `0.3.0.beta5` (2025-08 to 2026-05-14),
  `1.0.0.alpha1` (2026-05-13), `1.0.0.alpha2` (2026-05-27). `pyproject.toml`
  has `version = "1.0.0"` at every tag of the 1.0 line and on `main`, with the
  classifier "Development Status :: 4 - Beta", so the package version does
  not identify a build. The package is not on PyPI
  (`https://pypi.org/pypi/a2a-tck/json` answers 404). GitHub release entries:
  **uncertain** (API not reachable).
- **Maintenance:** 350 commits since 2025-05-21; 11 commits between
  2026-07-08 and 2026-10-06, all on 2026-08-31 and 2026-09-01 (pull requests
  #199 to #230). 15 distinct authors; the three most active account for about
  nine out of ten commits. CI runs lint and unit tests only. Open-issue count:
  **uncertain**.
- **Spec tracking:** the TCK targets protocol 1.0. `specification/version.json`
  pins A2A commit `173695755607e884aa9acf8ce4feed90e32727a1`, which is tag
  `v1.0.0` (downloaded 2026-03-13), one patch release behind the current
  v1.0.1. The harness sends `A2A-Version: 1.0` on every request
  (`tck/transport/_helpers.py`), uses the PascalCase method names of spec §5.3
  and §9.1, fetches the card from `/.well-known/agent-card.json` (spec §8.2)
  and derives the transports to test from `supportedInterfaces` (spec §8.3).
  The documents under `docs/` (`A2A_V030_FEATURES.md`,
  `AUTHENTICATION_SETUP.md`, `SUT_REQUIREMENTS.md`) describe the pre-rewrite
  0.3-era TCK and name command-line flags and test paths that no longer
  exist; the code, not the documents, is the reference.

### Result files

`run_tck.py` always writes, relative to the working directory:

| File | Produced by | Format |
|---|---|---|
| `reports/compatibility.json` | `tests/compatibility/conftest.py::pytest_sessionfinish` via `tck/reporting/json_formatter.py` | JSON, see below |
| `reports/compatibility.html` | the same hook via the HTML formatter | self-contained HTML |
| `reports/tck_report.html` | pytest-html | HTML |
| `reports/junitreport.xml` | pytest `--junitxml` | JUnit XML (pytest default family) |

The two `compatibility.*` files are written only when at least one result
was collected; if the Agent Card cannot be fetched, no `compatibility.json`
exists.

`compatibility.json` is built directly in code (`_build_dict` in
`tck/reporting/json_formatter.py`) and written with `json.dumps(indent=2)`:

```jsonc
{
  "summary": {
    "timestamp": "<ISO-8601 UTC>",
    "sut_url": "<the --sut-host value>",
    "spec_version": "",            // always empty: conftest constructs the formatter without it
    "overall_compatibility": "NN.N%",
    "must_compatibility": "NN.N%",
    "should_compatibility": "NN.N%",
    "may_compatibility": "NN.N%"
  },
  "per_requirement": {
    "<REQUIREMENT-ID>": {
      "level": "MUST" | "SHOULD" | "MAY",
      "status": "PASS" | "FAIL" | "SKIPPED" | "NOT TESTED",
      "transports": { "grpc" | "jsonrpc" | "http_json": "PASS" | "FAIL" | "SKIPPED" },
      "errors": ["<free text>"],
      "test_ids": ["<pytest node id>"]
    }
  },
  "per_transport": {
    "<transport>": { "total": 0, "passed": 0, "failed": 0, "skipped": 0 }
  },
  "agent_card": { /* the fetched Agent Card, verbatim; present only when one was fetched */ }
}
```

Semantics (`tck/reporting/aggregator.py`): a transport cell is `SKIPPED` if
the test skipped, `PASS` if it passed, otherwise `FAIL`; a requirement is
`FAIL` if any transport failed, `SKIPPED` if all skipped, otherwise `PASS`;
requirements in the registry with no recorded result are `NOT TESTED`.
Percentages exclude `SKIPPED` requirements and count `NOT TESTED` as not
passed. The registry holds 127 requirement ids (114 MUST, 11 SHOULD, 4 MAY),
matching `^[A-Z][A-Z0-9_]+-[A-Z]+-\d+$`. Transport keys are the TCK's own
names `grpc`, `jsonrpc` and `http_json`, mapped from the card's
`protocolBinding` values `GRPC`, `JSONRPC` and `HTTP+JSON`.

The file carries **no tool name, tool version, TCK commit or spec commit**,
and `summary.spec_version` is always the empty string. The only reliable
identifier of the TCK build is the git commit or tag of the checkout that
produced the file, which the operator must supply.

### Import safety

- Pure JSON; no embedded code, includes or references to resolve.
- Embeds about the agent under test: the base URL given as `--sut-host`, the
  Agent Card verbatim (names, interface URLs, declared security schemes,
  signatures if any), free-text error strings that may quote the agent's
  error messages, and, for tests that crashed, a short pytest traceback with
  file paths of the machine that ran the TCK. These are display text and must
  be treated as untrusted data.
- The current harness sends no `Authorization` or custom authentication
  header at all (the environment variables described in
  `docs/AUTHENTICATION_SETUP.md` are not implemented in the code), so no
  credential of the agent under test can reach the file. The only way a
  credential enters the file is an operator typing it into the URL.
- Size: roughly 50 to 150 KB for a full run with three transports.
- **Credentials needed to import: none.**

### If the TCK were executed inside Suncly

Not planned. It would have to run inside the Runner's credential boundary:
the TCK is the party that contacts the agent (outbound HTTP for JSON-RPC and
HTTP+JSON, outbound gRPC), and it opens an inbound webhook HTTP server bound
to all interfaces for the push-notification tests. It must run from a source
checkout (the wheel does not package the test suite) and shells out to
pytest. It would bring `pytest`, `pytest-asyncio`, `httpx`, `grpcio`,
`protobuf`, `googleapis-common-protos`, `jsonschema`, `pytest-html`,
`gherkin-official` and `Jinja2` into the Runner. This is excluded by the
rules of this project: the Runner takes no third-party execution tools.

### Reference agent shipped with the TCK

`sut/a2a-python/sut_agent.py` is a generated reference System Under Test
(Python, a2a-sdk) that declares three interfaces, all `protocolVersion`
`1.0`. It was run against Suncly as part of this work; see
[REAL_AGENT_REPORT.md](REAL_AGENT_REPORT.md).

## Promptfoo

Evaluated from the npm registry (`promptfoo`, `dist-tags.latest`), a sparse
clone of `https://github.com/promptfoo/promptfoo` at `main` (`832173001f`,
2026-10-06, `package.json` version 0.124.0), and the project documentation
in that clone.

### Licence, release, maintenance

- **Licence:** MIT. `LICENSE` is the MIT text ("Copyright (c) Promptfoo
  2025"); `package.json` has `"license": "MIT"`; npm reports MIT. No second
  licence applies to the open-source package. The "Enterprise" offering
  documented under `site/docs/enterprise/` is a hosted product, not a
  differently licensed code component. The README states that the project is
  now part of OpenAI and remains MIT licensed. One vendored third-party
  `LICENSE` file under `plugins/` was not inspected.
- **Releases:** 0.124.0, published 2026-10-06 on npm, tag `0.124.0`,
  CHANGELOG entry dated 2026-10-06. Still a 0.x line, so the output types
  may move between minors. 424 published versions since 2023-05-03; in 2026
  about 30 releases, roughly a minor release per month since 0.122.0
  (2026-08-04). Requires Node 22.22.0 or newer.
- **Maintenance:** 959 commits on `main` between 2026-07-08 and 2026-10-06
  from 76 author identities, 73 of them not bots. Open issues, stars and the
  total contributor count: **uncertain** (API not reachable).

### Result file format

`promptfoo eval -o results.json` writes `JSON.stringify(outputData, null, 2)`
of the TypeScript interface `OutputFile` (`src/types/index.ts`, around line
1551 at the commit above):

```text
OutputFile
├─ evalId: string | null
├─ results: EvaluateSummaryV3 | EvaluateSummaryV2
│   ├─ version: 3                 (literal; legacy records export version 2 with "table" instead of "prompts")
│   ├─ timestamp: string          (ISO-8601)
│   ├─ prompts: CompletedPrompt[]
│   ├─ results: EvaluateResult[]
│   └─ stats: { successes, failures, errors, tokenUsage, durationMs? }
├─ config: Partial<UnifiedConfig>  (a redacted copy of the configuration)
├─ shareableUrl: string | null     (null unless the evaluation was shared)
├─ metadata?: OutputMetadata       { promptfooVersion, nodeVersion, platform, arch, exportedAt, evaluationCreatedAt?, author? }
├─ vars?: string[]
├─ runtimeOptions?
├─ traces?: TraceData[]
└─ blobAssets?: { hash, mimeType, sizeBytes, data (base64) }[]   (only when media is included)
```

Per result (`EvaluateResult`):

| Field | Type | Meaning |
|---|---|---|
| `promptIdx`, `testIdx`, `promptId`, `id?` | number, string | row identity |
| `testCase` | object | the test, including its `assert` list and `vars` |
| `provider` | `{ id, label }` | for example `a2a:https://...` |
| `prompt`, `vars` | object | what was sent |
| `response?` | `ProviderResponse` | `output?`, `raw?`, `error?`, `latencyMs?`, `metadata?` (including HTTP status and headers), and more |
| `error?` | string or null | provider or runtime error text |
| `failureReason` | `0` none, `1` assertion, `2` error | absent in files written by older versions |
| `success` | boolean | the row passed |
| `score` | number | aggregate score |
| `gradingResult?` | `GradingResult` or null | `pass`, `score`, `reason`, `componentResults?` (one per assertion), `assertion?` (type, value, provider), `metadata?` |
| `latencyMs`, `cost?`, `tokenUsage?`, `namedScores`, `metadata?` | | measurements |

Aggregation (`src/assertions/assertionsResult.ts`): `gradingResult.pass` is
true only when no assertion failed, or, with a numeric test `threshold`,
when the weighted score reaches it; `reason` is the first failing assertion's
reason or "All assertions passed"; `componentResults` lists one
`GradingResult` per assertion. Rows without assertions or with a provider
error may have no `gradingResult`.

**Schema version:** `results.version` (3 today). **Tool version:**
`metadata.promptfooVersion` only; `metadata` is optional and absent from
files written by older versions, from the XML writer and from JSONL rows.
The example in the documentation page `site/docs/configuration/outputs.md`
does not match the real type; the TypeScript types are authoritative.

Other `-o` formats are lossy or lack the envelope (`xml` drops `metadata`
and stringifies values; `jsonl` has no envelope; `csv` is a table). An
importer should accept `.json` only.

### Model-graded assertions and A2A support

- Promptfoo has model-graded assertions (`llm-rubric`, `g-eval`,
  `factuality`, `model-graded-closedqa`, `agent-rubric` and others). The
  judge model's `{reason, score, pass}` lands in one `componentResults`
  entry with `assertion.type` naming the assertion. A grader transport or
  parse failure is written as `pass: false` **with
  `metadata.graderError: true`**, and Promptfoo's own code comments that this
  "is not evidence that the criterion was or was not met"
  (`src/matchers/shared.ts`, `src/types/index.ts` around line 557). Suncly
  must map such entries to `inconclusive`, never to `fail` and never to
  `pass`.
- Promptfoo has a built-in A2A provider (`a2a:<url>`), added 2026-06-01. It
  speaks **only the HTTP+JSON binding** (`POST /message:send`,
  `GET /tasks/{id}`, SSE for streaming); its documentation states that
  JSON-RPC and gRPC are not supported. It sends `A2A-Version` (default
  `1.0`), selects the first `supportedInterfaces` entry with
  `protocolBinding` `HTTP+JSON`, treats the four terminal states of spec
  §3.1.1 as terminal, and also accepts the non-spec spelling
  `TASK_STATE_CANCELLED`. Failed, cancelled, rejected and interrupted tasks
  become provider errors. Consequence: Promptfoo result files can exist only
  for agents that expose an HTTP+JSON interface, while Suncly's Runner uses
  JSON-RPC.

### Import safety

- Pure JSON written locally; no code to run; no credential needed to parse
  it. `shareableUrl` is null unless the operator shared the evaluation to
  Promptfoo's hosted service.
- The file embeds full prompts, test variables, the agent's full output, the
  rendered grading prompts, the whole redacted configuration (including
  provider configuration blocks), optional traces and optional base64 media.
  Promptfoo redacts the configuration by field name (`apiKey`, `token`,
  `password`, `authorization` and similar), by value pattern (UUIDs, long
  hex strings, JWTs, prefixed tokens) and strips URL user information and
  secret query parameters; credential-bearing HTTP headers in result rows
  are redacted too. A secret inlined under an unusual field name whose value
  matches none of the patterns is written in clear, and Promptfoo's
  `SECURITY.md` guarantees redaction only for documented fields. Suncly must
  therefore treat the file as untrusted data and run its own redaction pass
  before storing or displaying any of it.
- Size: about 1.7 KB per result in the shipped example; it grows with output
  length, grading prompts and traces. An importer should cap the accepted
  size.
- **Credentials needed to import: none.** Running Promptfoo needs model
  provider keys for targets and graders and, for A2A agents, whatever the
  agent requires; sharing needs a Promptfoo account; telemetry is on by
  default.

### If Promptfoo were executed inside Suncly

Not planned. It would have to run inside the Runner, because it calls the
agent and a grader model, which places the target credential and the grader
keys inside the credential boundary and breaks the Runner rule "call
anything other than the target" ([ARCHITECTURE.md](ARCHITECTURE.md), Runner).
Footprint: Node 22 or newer, an unpacked package of about 32 MB and 698
files, a lock file resolving to about 730 runtime packages (a web server, a
local SQLite database that every evaluation writes to, telemetry, OpenAI and
Anthropic client libraries, among others). Import mode avoids all of it.

### Mapping Promptfoo results to Suncly verdicts

The rule matches `run.verdict` (schema §3) and the Judge: anything unknown,
unrecognized or undecidable is `inconclusive`, and `inconclusive` is never
counted as a pass. Rows are evaluated top to bottom; the first match decides.

| # | Condition in the file | Verdict |
|---|---|---|
| 1 | Not valid JSON, no `results.results`, or `results.version` is not `3` | `inconclusive` for the whole file |
| 2 | `metadata.promptfooVersion` missing | import continues; tool version recorded as unknown |
| 3 | Row `error` set, or `failureReason` is `2`, or `response.error` set | `inconclusive` |
| 4 | `gradingResult` null or absent, or the test has no assertions | `inconclusive` |
| 5 | Any component has `metadata.graderError` true | `inconclusive` |
| 6 | Any component's `assertion.type` is not on Suncly's allow-list (code-executing assertions such as `javascript`, `python`, `webhook`, `human`, unknown types) | `inconclusive` |
| 7 | `success` false, `failureReason` `1`, `gradingResult.pass` false, all component types recognized | `fail` |
| 8 | `success` false, no `failureReason` (older file), `gradingResult.pass` false, no `error` | `fail` |
| 9 | `success` true, `gradingResult.pass` true, every component `pass` true with a recognized type and no grader error | `pass` |
| 10 | `success` and `gradingResult.pass` disagree, or a test `threshold` made `pass` true while a component failed | `inconclusive` |
| 11 | `provider.id` does not identify an A2A provider when the evidence is about an A2A agent | `inconclusive` |
| 12 | `response.metadata` reports a task state other than `TASK_STATE_COMPLETED` | `inconclusive` |

## Intended architecture for the next task: import mode only

These constraints are binding for any later implementation:

- The user runs the TCK or Promptfoo. Suncly reads the result file. Suncly
  never installs or executes either tool, and neither becomes a dependency of
  the Runner or of the package.
- No customer credential is read outside the Runner. Importing a file needs
  none.
- Every imported record is validated against the field sets above. Any file,
  row or component Suncly does not recognize maps to `inconclusive`, never to
  `pass`.
- The raw file is kept with: tool name, tool version (for the TCK, the
  operator-supplied git commit or tag, because the file carries none; for
  Promptfoo, `metadata.promptfooVersion` or "unknown"), the SHA-256 of the raw
  bytes, and the normalized Suncly verdict.
- Imported content is untrusted data: it is redacted with Suncly's own rules
  and displayed as text, never interpreted.
- Imported evidence does not fit the current signed payload; see
  [REAL_AGENT_REPORT.md](REAL_AGENT_REPORT.md), "Signed payload", for what a
  change would involve. That change needs the founders' approval first.

## Open questions

- **OQ-OSS1** The TCK's result file carries no tool or spec version. Should
  Suncly require the operator to supply the TCK commit, or refuse files
  without it? An upstream change (populating `summary.spec_version` and
  adding a commit field) would remove the problem.
- **OQ-OSS2** The TCK pins A2A `v1.0.0` while Suncly follows `v1.0.1`. Is a
  requirement set written against a one-patch-older text acceptable as
  evidence about a 1.0 agent?
- **OQ-OSS3** Promptfoo's A2A provider speaks HTTP+JSON only and Suncly's
  Runner speaks JSON-RPC. Should Suncly accept Promptfoo evidence about an
  interface it did not exercise itself, and how should the report state
  that?
- **OQ-OSS4** Which Promptfoo assertion types belong on the allow-list of
  the mapping table, and whether model-graded assertions count as Layer 2
  evidence or as a separate class, is a policy decision
  ([POLICY.md](POLICY.md)).
- **OQ-OSS5** Where imported evidence lives in the data model. The seven
  entities have no place for a third-party result (schema §3), so import mode
  needs a founders' decision on the model before any code.
