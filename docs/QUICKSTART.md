# Quickstart

Five minutes from nothing to a signed attestation and a report. Everything
below runs on Windows PowerShell, macOS and Linux; where a command differs, both
forms are given.

## 1. Install

You need Python 3.12 or newer and git.

```powershell
git clone https://github.com/Kristjanh2/Suncly.git
cd Suncly
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -e .
suncly --version
```

## 2. See it work: `suncly demo`

```powershell
suncly demo
```

The demo starts two bundled mock A2A agents on this machine, an honest one and
a lying one, and attests both. Mock agents are sandboxes by construction, so
the demo declares them as such. You will see, for each agent:

1. the Agent Card being fetched and hashed;
2. a drafted contract approved as `suncly-demo` (the demo approves on your
   behalf; `suncly attest` never does);
3. live progress per run, with the Layer 1 verdict for each;
4. a table of `pass`, `fail` and `inconclusive` counts per test case;
5. the decision line:

   > Decision: flag. No policy is configured, so a human must review this result.

6. the signature, the "What was NOT tested" list and the report folder.

The honest agent passes every run. The lying agent's card declares `text/plain`
output but it answers with JSON, so every run fails the `output_modes` check.
Both end with the decision `flag`: without a configured policy, Suncly never
approves or blocks anything.

Reports are written to `./suncly-reports/<attestation-id>/`. Open
`report.html` in a browser (it needs no network), or read `report.md`.

## 3. Attest an agent from its card URL

Start a sandbox to attest. Any A2A 1.0 agent over JSON-RPC works; to try the
flow with a bundled one, start it in a second terminal:

```powershell
python -m suncly.mock_agents honest --port 8701
```

Then, in the first terminal:

```powershell
suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox
```

What happens:

- `--sandbox` is required. Without it Suncly refuses to run anything
  (DR-006): Suncly only tests sandbox or dry-run endpoints, so nothing real is
  booked, paid or deleted. Suncly cannot verify that an endpoint is a sandbox;
  the flag is your declaration.
- Suncly fetches the card, drafts one test case per declared example of each
  skill, and shows you the draft. Nothing runs until you approve it and enter
  your identifier, which is recorded as `approved_by`. In a script, pass
  `--approve-as <identifier>` instead.
- A skill that declares no examples gets no test case: Suncly never invents
  input. The draft says so, and the report lists the skill under "What was
  NOT tested".
- Each test case runs `--runs` times (default 5) against the agent, from a
  separate Runner process, within a budget of attempts (default twice the
  planned runs). Both numbers are shown before anything runs.
- Every run gets a deterministic verdict; the Policy engine records the
  decision `flag`; the attestation is signed with your deployment key; the
  report folder is written.
- The same card gets the same approved contract next time. A changed card gets
  a new draft that needs a new approval.

Exit code 0 means the attestation completed and was signed. It does not mean
the agent was approved; the output says so.

### Using a credential

If the sandbox needs an `Authorization` header, put its full value in the
environment before running. Only the Runner process reads it, and it is
redacted from every transcript before anything leaves the Runner (DR-003):

```powershell
$env:SUNCLY_AGENT_AUTHORIZATION = "Bearer <token>"     # macOS/Linux: export SUNCLY_AGENT_AUTHORIZATION="Bearer <token>"
```

## 4. Read the report

`suncly-reports/<attestation-id>/` holds:

| File | Contents |
|---|---|
| `report.html` | The report for a reviewer. Self-contained; opens offline. |
| `report.md` | The same content as Markdown. |
| `result.json` | The evidence bundle: attestation, runs, decisions, card version, contract, results, the signed payload and the public key. |
| `transcripts/<run-id>.json` | One redacted transcript per run, with its Layer 1 checks. |

The report always states what was NOT tested: skills without a test case, runs
never executed, inconclusive runs, declared capabilities no test exercised,
interfaces not used, probes and semantic checks that need later stages, and the
production endpoint itself.

## 5. Verify an attestation

```powershell
suncly verify suncly-reports/<attestation-id>
```

The verifier checks the signature over the signed payload, that the card hash
matches the stored card, that every transcript file matches its signed hash,
that the recorded decision is the signed one, and that the per-test-case
counts match the recorded runs. Change one byte of a transcript or of
`result.json` and it tells you which check failed and why. The public key
travels in `result.json`; pass `--public-key` to verify against a key you
obtained out of band.

## 6. Edit the test cases

Export the draft, edit it, and run with the file:

```powershell
suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox --export-draft contract.json
# edit contract.json
suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox --contract contract.json --approve-as <you>
```

The file format is documented in [API.md](API.md), section "Contract file".
The imported contract becomes a new version; its approval is recorded like any
other.

## 7. Use Postgres instead of the file store

By default evidence lives in files under `~/.suncly/store`. To use Postgres,
set `DATABASE_URL` and apply the migration:

```powershell
$env:DATABASE_URL = "postgresql://user:password@host:5432/suncly"    # never commit this value
suncly db migrate
suncly db check
```

That is the only change. Transcripts stay on local disk under
`~/.suncly/transcripts` until an object storage adapter exists. When the
Supabase database is ready, set `DATABASE_URL` to its connection string.

## 8. When something goes wrong

```powershell
suncly doctor http://127.0.0.1:8701/.well-known/agent-card.json
```

checks the Python version, the deployment key, the store configuration and
whether the card is reachable. Every error Suncly prints says what happened,
why, and what to do next; add `--debug` for a traceback.

| Exit code | Meaning |
|---|---|
| 0 | The attestation completed: decided (`flag`) and signed. Not an approval. |
| 1 | Suncly itself failed. |
| 2 | Wrong arguments. |
| 3 | Refused to start: no `--sandbox`, no approval, unusable card or contract. |
| 4 | The attestation ended `failed`: the budget stopped it, or the card could not be re-fetched. |
| 5 | The attestation ended `invalidated`: the card changed while it ran. |
| 6 | `suncly verify` or `suncly doctor` found a problem. |

## Settings

Every setting has a default, can be set in `~/.suncly/config.toml`, and can be
overridden by an environment variable (see `.env.example`). `--home` moves the
whole state folder, which is useful for isolated runs:

```powershell
suncly --home .\tmp-home demo --reports-dir .\tmp-reports
```
