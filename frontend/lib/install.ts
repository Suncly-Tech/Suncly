/**
 * The Install section's commands and captured output.
 *
 * Commands are word for word from docs/QUICKSTART.md §1 and §2 (QUICKSTART). The
 * macOS/Linux variant was run in the build session on 2026-10-05 in a clean Python 3.12
 * virtual environment (RUN; see VERIFICATION.md). The Windows variant comes from
 * QUICKSTART.md and was not run here. The demo output is the captured output of that
 * run, trimmed to the honest agent's run and the lying agent's results, not retyped.
 */

export const installCommands = {
  unix: `git clone https://github.com/Suncly-Tech/Suncly.git
cd Suncly
python -m venv .venv
source .venv/bin/activate
pip install -e .
suncly demo`,
  windows: `git clone https://github.com/Suncly-Tech/Suncly.git
cd Suncly
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -e .
suncly demo`,
  attest: "suncly attest <card-url> --sandbox",
  verify: "suncly verify <report-folder>",
  mock: "python -m suncly.mock_agents honest --port 8701",
  attestLocal: "suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox",
} as const;

/** Captured from `suncly demo` on 2026-10-05 (3.6 s). Ports, ids, hashes and times vary per run. */
export const demoOutput = `=== honest mock agent at http://127.0.0.1:42277/.well-known/agent-card.json ===
Bundled mock agents run on this machine and are sandboxes by construction.
Created a deployment signing key (ed25519-6c8beef28aa330d3). The private key stays in your Suncly home folder.
Fetched the Agent Card of 'honest mock agent': 2 skill(s), card_hash sha256:7300c3a0e9fa23dca76e66843f6c3b5a9c1a4d0829932ade84955c8fa8b82fe0
Contract version 1 approved by suncly-demo.
Attestation a0dc8bab-5f36-4f16-a967-8aa353317a81: 3 test case(s) x 3 run(s) = 9 planned run(s); budget 18 attempt(s).

  uppercase      hello world               run   2  pass                         5 ms  pass: every Layer 1 check passed
  uppercase      suncly attests agents     run   1  pass                         6 ms  pass: every Layer 1 check passed
  count-words    one two three             run   1  pass                         3 ms  pass: every Layer 1 check passed
  …
Card re-check: unchanged

Results for honest mock agent
Skill        Input                  pass  fail  inconclusive
-----------  ---------------------  ----  ----  ------------
uppercase    hello world               3     0             0
uppercase    suncly attests agents     3     0             0
count-words  one two three             3     0             0

Decision: flag. No policy is configured, so a human must review this result.
Signed with key ed25519-6c8beef28aa330d3. Verify with: suncly verify "suncly-reports/a0dc8bab-5f36-4f16-a967-8aa353317a81"

What was NOT tested
  - probes: no probe_undeclared, probe_injection or probe_failure test cases exist yet (stage 4)
  - semantic correctness: Layer 1 checks structure, state, output modes and latency; whether the content of each answer is correct needs Layer 2 (stage 4)
  - production endpoint: tests ran against the declared sandbox or dry-run endpoint http://127.0.0.1:42277/rpc; the production endpoint itself was not tested (DR-006)

=== lying mock agent at http://127.0.0.1:45229/.well-known/agent-card.json ===
  uppercase      hello world               run   1  fail                         5 ms  fail: output_modes
  …
Results for lying mock agent
Skill        Input                  pass  fail  inconclusive
-----------  ---------------------  ----  ----  ------------
uppercase    hello world               0     3             0
uppercase    suncly attests agents     0     3             0
count-words  one two three             0     3             0

Decision: flag. No policy is configured, so a human must review this result.

Demo finished
The honest agent's runs pass Layer 1; the lying agent's runs fail the declared output modes.
Both decisions are 'flag': without a configured policy, a human reviews every result.`;
