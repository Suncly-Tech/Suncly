import type { Metadata } from "next";
import { DocLayout } from "@/components/site/DocLayout";
import { CodeBlock } from "@/components/ui/CodeBlock";

export const metadata: Metadata = {
  title: "Command reference",
  description: "Every suncly command, option, exit code, environment variable and the contract file format.",
  alternates: { canonical: "/docs/cli" },
};

const toc = [
  { id: "commands", title: "Commands" },
  { id: "attest-options", title: "suncly attest options" },
  { id: "exit-codes", title: "Exit codes" },
  { id: "contract-file", title: "Contract file" },
  { id: "settings", title: "Settings and environment" },
  { id: "json", title: "Machine-readable output" },
];

const contractExample = `{
  "suncly_contract_file": 1,
  "card_hash": "sha256:…",
  "agent_name": "Order Status Agent",
  "skills_without_test_case": [],
  "test_cases": [
    {
      "skill_id": "order-status",
      "kind": "skill",
      "input": {"text": "Where is order 1234?"},
      "criteria": {
        "final_state": "TASK_STATE_COMPLETED",
        "latency_limit_ms": 10000,
        "response_present": true,
        "output_modes": ["text/plain"],
        "required_fields": ["/artifacts/0/parts/0/text"],
        "response_schema": {"type": "object", "required": ["artifacts"]},
        "model_checks": [],
        "accept_direct_message": false
      }
    }
  ]
}`;

export default function CliPage() {
  return (
    <DocLayout
      eyebrow="Command reference"
      headline="One command does the work. Five keep it honest."
      intro="The CLI parses, prompts and prints; every decision lives in the core library the future HTTP API will call too. Options marked Proposed implement proposals for open questions and may change when the founders decide them."
      current="/docs/cli"
      toc={toc}
    >
      <h2 id="commands">Commands</h2>
      <table>
        <thead>
          <tr>
            <th>Command</th>
            <th>What it does</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>suncly attest &lt;card-url&gt; --sandbox</code></td>
            <td>Evaluate the agent at the card URL: fetch and hash the card, draft or reuse a contract, record the approval, run, judge, decide (flag), sign, write the report folder.</td>
          </tr>
          <tr>
            <td><code>suncly demo</code></td>
            <td>Start the bundled honest and lying mock agents and evaluate both. <code>--runs</code> (default 3), <code>--reports-dir</code>, <code>--json</code>.</td>
          </tr>
          <tr>
            <td><code>suncly verify &lt;report-folder&gt;</code></td>
            <td>Check the signature, card hash, decision, transcript hashes and counts of a report folder. <code>--public-key</code> overrides the embedded key.</td>
          </tr>
          <tr>
            <td><code>suncly keys init [--new]</code></td>
            <td>Create the local Ed25519 deployment key. <code>attest</code> and <code>demo</code> create one on first use if none exists.</td>
          </tr>
          <tr>
            <td><code>suncly db migrate</code>, <code>suncly db check</code></td>
            <td>Apply and check the Postgres schema (seven tables, eight enums, triggers) when <code>DATABASE_URL</code> is set.</td>
          </tr>
          <tr>
            <td><code>suncly doctor [card-url]</code></td>
            <td>Check Python, the deployment key, the store configuration and, optionally, that a card is reachable and parsable.</td>
          </tr>
        </tbody>
      </table>
      <p>
        <code>--home DIR</code> before any command moves the whole state folder (store, transcripts, keys). <code>-h</code> prints help; <code>--version</code> the version.
      </p>

      <h2 id="attest-options">suncly attest options (Proposed)</h2>
      <table>
        <thead>
          <tr>
            <th>Option</th>
            <th>Meaning</th>
          </tr>
        </thead>
        <tbody>
          <tr><td><code>--sandbox</code></td><td>Declares the endpoint a sandbox or dry-run endpoint. Required: without it nothing runs (DR-006). Suncly cannot verify a sandbox.</td></tr>
          <tr><td><code>--runs N</code></td><td>Repetitions per test case. Default 5 (<code>SUNCLY_RUNS</code>).</td></tr>
          <tr><td><code>--budget N</code></td><td>Budget in attempts. Default 2 × planned runs. One attempt costs 1, retries included; the attestation ends <code>failed</code> when reached.</td></tr>
          <tr><td><code>--approve-as ID</code></td><td>Approves the drafted contract as <code>ID</code> without a prompt; <code>ID</code> becomes <code>approved_by</code>. Without it the CLI shows the draft and asks; with no terminal, it refuses.</td></tr>
          <tr><td><code>--contract FILE</code></td><td>Uses a contract file instead of the drafter. The imported contract becomes a new version and still needs approval.</td></tr>
          <tr><td><code>--export-draft FILE</code></td><td>Writes the draft contract to <code>FILE</code> and stops. Nothing runs.</td></tr>
          <tr><td><code>--owner</code>, <code>--risk-level</code></td><td><code>agent.owner</code> and <code>agent.risk_level</code> (low, medium, high), recorded on first sight of the card URL. Defaults: <code>unspecified</code> and <code>high</code>. The risk level does not change the outcome yet.</td></tr>
          <tr><td><code>--reports-dir DIR</code></td><td>Where the report folder goes. Default <code>./suncly-reports</code>.</td></tr>
          <tr><td><code>--json</code></td><td>Prints a machine-readable result (see below). Progress goes to stderr.</td></tr>
          <tr><td><code>--debug</code></td><td>Shows tracebacks.</td></tr>
        </tbody>
      </table>
      <p>An attestation started from the CLI has <code>trigger</code> <code>manual</code>, also when CI calls the CLI.</p>

      <h2 id="exit-codes">Exit codes</h2>
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Meaning</th>
          </tr>
        </thead>
        <tbody>
          <tr><td><code>0</code></td><td>The attestation completed: decided (<code>flag</code>) and signed. <strong>Not an approval.</strong></td></tr>
          <tr><td><code>1</code></td><td>Suncly itself failed.</td></tr>
          <tr><td><code>2</code></td><td>Wrong arguments.</td></tr>
          <tr><td><code>3</code></td><td>Refused to start: no <code>--sandbox</code>, no approval, unusable card or contract.</td></tr>
          <tr><td><code>4</code></td><td>The attestation ended <code>failed</code>: the budget stopped it, or the card could not be re-fetched.</td></tr>
          <tr><td><code>5</code></td><td>The attestation ended <code>invalidated</code>: the card changed while it ran.</td></tr>
          <tr><td><code>6</code></td><td><code>suncly verify</code> or <code>suncly doctor</code> found a problem.</td></tr>
        </tbody>
      </table>
      <p>Because every decision is <code>flag</code> in this version, no pipeline should gate a release on the exit code alone. Archive the report folder and route it to a reviewer.</p>

      <h2 id="contract-file">Contract file (Proposed)</h2>
      <p>A hand-written or exported contract: one JSON document with the test cases of one contract for one card. Field names are the data model's. The file carries no approval fields: approval is recorded by <code>--approve-as</code> or the prompt.</p>
      <CodeBlock label="contract file example" code={contractExample} />
      <ul>
        <li><code>card_hash</code> must equal the hash of the fetched card, or the file is refused.</li>
        <li>Every declared skill needs a test case, or must be listed under <code>skills_without_test_case</code> to acknowledge that it stays untested.</li>
        <li><code>input</code> is <code>{"{"}&quot;text&quot;: …{"}"}</code> or <code>{"{"}&quot;parts&quot;: […]{"}"}</code> with A2A Part objects.</li>
        <li>
          <code>criteria</code> keys: <code>final_state</code> (a terminal task state, default <code>TASK_STATE_COMPLETED</code>); <code>latency_limit_ms</code> (required); <code>response_present</code>; <code>output_modes</code> (media types every output part must use; <code>null</code> disables the check); <code>required_fields</code> (JSON pointers that must exist and be non-empty in the final response); <code>response_schema</code> (a JSON Schema the final response must satisfy); <code>model_checks</code> (criteria for Layer 2, which does not exist yet, so any entry makes the run <code>inconclusive</code>); <code>accept_direct_message</code> (a direct Message reply counts as a completed task). Unknown keys are refused, so a typo can never silently weaken a check.
        </li>
      </ul>

      <h2 id="settings">Settings and environment</h2>
      <p>Resolved in this order: built-in defaults, then <code>SUNCLY_HOME/config.toml</code>, then environment variables. A blank value is the same as an unset one.</p>
      <table>
        <thead>
          <tr>
            <th>Variable</th>
            <th>Default</th>
            <th>Meaning</th>
          </tr>
        </thead>
        <tbody>
          <tr><td><code>SUNCLY_HOME</code></td><td><code>~/.suncly</code></td><td>State folder: file store, transcripts, deployment keys.</td></tr>
          <tr><td><code>DATABASE_URL</code></td><td>unset</td><td>When set, the Postgres store is used instead of the file store.</td></tr>
          <tr><td><code>SUNCLY_REPORTS_DIR</code></td><td><code>./suncly-reports</code></td><td>One report folder per attestation.</td></tr>
          <tr><td><code>SUNCLY_RUNS</code></td><td>5</td><td>Repetitions per test case.</td></tr>
          <tr><td><code>SUNCLY_BUDGET_LIMIT</code></td><td>2 × planned runs</td><td>Budget in attempts.</td></tr>
          <tr><td><code>SUNCLY_RUN_TIMEOUT_S</code></td><td>30</td><td>Per-run timeout; the Runner process is killed 10 s after it.</td></tr>
          <tr><td><code>SUNCLY_LATENCY_LIMIT_MS</code></td><td>10000</td><td>Latency limit written into drafted criteria.</td></tr>
          <tr><td><code>SUNCLY_MAX_RETRIES</code></td><td>2</td><td>Retries per run, under the same run key.</td></tr>
          <tr><td><code>SUNCLY_CONCURRENCY</code></td><td>4</td><td>Concurrent runs.</td></tr>
          <tr><td><code>SUNCLY_POLL_INTERVAL_S</code></td><td>0.5</td><td>Seconds between GetTask polls.</td></tr>
          <tr><td><code>SUNCLY_CARD_TIMEOUT_S</code>, <code>SUNCLY_CARD_MAX_BYTES</code></td><td>10, 1000000</td><td>Card fetch limits.</td></tr>
          <tr><td><code>SUNCLY_MAX_TEST_CASES_PER_SKILL</code></td><td>3</td><td>Drafted test cases per skill, one per declared example up to this cap.</td></tr>
          <tr><td><code>SUNCLY_AGENT_AUTHORIZATION</code></td><td>unset</td><td>The agent credential. Read only by the Runner process; redacted from every transcript.</td></tr>
        </tbody>
      </table>

      <h2 id="json">Machine-readable output</h2>
      <p>
        <code>suncly attest … --json</code> prints one JSON object with <code>exit_code</code>, <code>exit_code_meaning</code> (“0 means completed and signed, not approved”), <code>kind</code> (completed, failed, invalidated or draft_exported), <code>attestation</code>, <code>decision</code>, <code>results</code>, <code>not_tested</code> and <code>report_dir</code>. <code>suncly verify … --json</code> prints <code>ok</code> and the list of checks.
      </p>
    </DocLayout>
  );
}
