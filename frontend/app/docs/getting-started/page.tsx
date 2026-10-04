import type { Metadata } from "next";
import Link from "next/link";
import { DocLayout } from "@/components/site/DocLayout";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Notice } from "@/components/ui/Notice";

export const metadata: Metadata = {
  title: "Getting started",
  description: "Install Suncly, run the bundled demo, evaluate your own sandbox agent, read the report and verify it. Five minutes.",
  alternates: { canonical: "/docs/getting-started" },
};

const toc = [
  { id: "install", title: "1. Install" },
  { id: "demo", title: "2. See it work" },
  { id: "attest", title: "3. Evaluate your sandbox agent" },
  { id: "credential", title: "4. Use a credential" },
  { id: "report", title: "5. Read the report" },
  { id: "verify", title: "6. Verify the attestation" },
  { id: "edit", title: "7. Edit the test cases" },
  { id: "workspace", title: "8. Load it into the workspace" },
  { id: "postgres", title: "9. Use Postgres" },
  { id: "trouble", title: "10. When something goes wrong" },
];

export default function GettingStartedPage() {
  return (
    <DocLayout
      eyebrow="Getting started"
      headline="From nothing to a signed evaluation in five minutes."
      intro="The same commands work on Windows PowerShell, macOS and Linux; where a command differs, both forms are given. Repository access comes with the pilot."
      current="/docs/getting-started"
      toc={toc}
    >
      <h2 id="install">1. Install</h2>
      <p>You need Python 3.12 or newer and git.</p>
      <CodeBlock
        label="install commands"
        lines
        code={`git clone https://github.com/Kristjanh2/Suncly.git
cd Suncly
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1   # macOS/Linux: source .venv/bin/activate
pip install -e .
suncly --version`}
      />

      <h2 id="demo">2. See it work</h2>
      <CodeBlock label="demo command" lines code="suncly demo" />
      <p>
        The demo starts two bundled mock A2A agents on your machine, an honest one and a lying one, and evaluates both. Mock agents are sandboxes by construction, so the demo declares them as such and approves the drafted contract on your behalf as <code>suncly-demo</code>; <code>suncly attest</code> never does either. For each agent you see the card fetched and hashed, the contract approved, live progress per run with its verdict, the per-test-case counts, the decision line, the signature, the “What was NOT tested” list and the report folder.
      </p>
      <blockquote>Decision: flag. No policy is configured, so a human must review this result.</blockquote>
      <p>
        The honest agent passes every run. The lying agent's card declares <code>text/plain</code> output but it answers with JSON, so every run fails the <code>output_modes</code> check. Both end with the decision <code>flag</code>: without a configured policy, Suncly never approves or blocks anything. Reports land in <code>./suncly-reports/&lt;attestation-id&gt;/</code>.
      </p>

      <h2 id="attest">3. Evaluate your sandbox agent</h2>
      <p>Any A2A 1.0 agent over JSON-RPC works. To try the flow with a bundled agent first, start one in a second terminal:</p>
      <CodeBlock label="start a mock agent" lines code="python -m suncly.mock_agents honest --port 8701" />
      <p>Then, in the first terminal:</p>
      <CodeBlock label="attest command" lines code="suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox" />
      <ul>
        <li>
          <strong><code>--sandbox</code> is required.</strong> Without it Suncly refuses to run anything. Suncly cannot verify that an endpoint is a sandbox; the flag is your declaration.
        </li>
        <li>Suncly fetches the card, drafts one test case per declared example of each skill, and shows you the draft. Nothing runs until you approve it and enter your identifier, which is recorded as <code>approved_by</code>. In a script, pass <code>--approve-as &lt;identifier&gt;</code> instead.</li>
        <li>A skill that declares no examples gets no test case: Suncly never invents input. The draft says so, and the report lists the skill under “What was NOT tested”.</li>
        <li>Each test case runs <code>--runs</code> times (default 5), each from a separate Runner process, within a budget of attempts (default twice the planned runs). Both numbers are shown before anything runs.</li>
        <li>Every run gets a deterministic verdict; the Policy engine records <code>flag</code>; the attestation is signed with your deployment key; the report folder is written.</li>
        <li>The same card gets the same approved contract next time. A changed card gets a new draft that needs a new approval.</li>
      </ul>
      <Notice tone="info" title="Exit code 0 is not an approval">
        It means the attestation completed and was signed. The output says so. All codes are in the <Link href="/docs/cli#exit-codes">command reference</Link>.
      </Notice>

      <h2 id="credential">4. Use a credential</h2>
      <p>If the sandbox needs an Authorization header, put its full value in the environment before running. Only the Runner process reads it, and it is redacted from every transcript before anything leaves the Runner.</p>
      <CodeBlock
        label="credential environment variable"
        lines
        code={`$env:SUNCLY_AGENT_AUTHORIZATION = "Bearer <token>"
# macOS/Linux: export SUNCLY_AGENT_AUTHORIZATION="Bearer <token>"`}
      />

      <h2 id="report">5. Read the report</h2>
      <table>
        <thead>
          <tr>
            <th>File</th>
            <th>Contents</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code>report.html</code></td>
            <td>The report for a reviewer. Self-contained; opens offline.</td>
          </tr>
          <tr>
            <td><code>report.md</code></td>
            <td>The same content as Markdown.</td>
          </tr>
          <tr>
            <td><code>result.json</code></td>
            <td>The evidence bundle: attestation, runs, decisions, card version, contract, results, the signed payload and the public key.</td>
          </tr>
          <tr>
            <td><code>transcripts/&lt;run-id&gt;.json</code></td>
            <td>One redacted transcript per run, with its Layer 1 checks.</td>
          </tr>
        </tbody>
      </table>
      <p>The report always states what was NOT tested: skills without a test case, runs never executed, inconclusive runs, declared capabilities no test exercised, interfaces not used, probes and semantic checks that need later stages, and the production endpoint itself.</p>

      <h2 id="verify">6. Verify the attestation</h2>
      <CodeBlock label="verify command" lines code="suncly verify suncly-reports/<attestation-id>" />
      <p>
        The verifier checks the signature over the signed payload, that the card hash matches the stored card, that every transcript file matches its signed hash, that the recorded decision is the signed one, and that the per-test-case counts match the recorded runs. Change one byte of a transcript or of <code>result.json</code> and it tells you which check failed and why. The public key travels in <code>result.json</code>; pass <code>--public-key</code> to verify against a key you obtained out of band.
      </p>

      <h2 id="edit">7. Edit the test cases</h2>
      <p>Export the draft, edit it, and run with the file:</p>
      <CodeBlock
        label="export and import a contract file"
        lines
        code={`suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox --export-draft contract.json
# edit contract.json: add required_fields, a response_schema, a tighter latency_limit_ms
suncly attest http://127.0.0.1:8701/.well-known/agent-card.json --sandbox --contract contract.json --approve-as <you>`}
      />
      <p>
        The file format is in the <Link href="/docs/cli#contract-file">command reference</Link>. The imported contract becomes a new version; its approval is recorded like any other.
      </p>

      <h2 id="workspace">8. Load it into the workspace</h2>
      <p>
        The <Link href="/app">review workspace</Link> reads report folders in this browser: drop <code>result.json</code> and the <code>transcripts</code> folder, and you get the overview, the agent's history, the evidence per run, in-browser verification and a comparison with the previous evaluation. Nothing is uploaded; the workspace stores bundles in this browser only.
      </p>

      <h2 id="postgres">9. Use Postgres instead of the file store</h2>
      <p>By default evidence lives in files under <code>~/.suncly/store</code>. To use Postgres, set <code>DATABASE_URL</code> and apply the migration:</p>
      <CodeBlock
        label="postgres setup"
        lines
        code={`$env:DATABASE_URL = "postgresql://user:password@host:5432/suncly"   # never commit this value
suncly db migrate
suncly db check`}
      />
      <p>That is the only change. Transcripts stay on local disk under <code>~/.suncly/transcripts</code> until an object storage adapter exists.</p>

      <h2 id="trouble">10. When something goes wrong</h2>
      <CodeBlock label="doctor command" lines code="suncly doctor http://127.0.0.1:8701/.well-known/agent-card.json" />
      <p>
        <code>suncly doctor</code> checks the Python version, the deployment key, the store configuration and whether the card is reachable. Every error Suncly prints says what happened, why, and what to do next; add <code>--debug</code> for a traceback.
      </p>
      <p>
        Every setting has a default, can be set in <code>~/.suncly/config.toml</code>, and can be overridden by an environment variable. <code>--home</code> moves the whole state folder, which is useful for isolated runs:
      </p>
      <CodeBlock label="isolated run" lines code="suncly --home ./tmp-home demo --reports-dir ./tmp-reports" />
    </DocLayout>
  );
}
