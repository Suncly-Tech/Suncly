import type { Metadata } from "next";
import Link from "next/link";
import { DocLayout } from "@/components/site/DocLayout";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { KEYWORDS, pageMeta } from "@/lib/seo";

export const metadata: Metadata = pageMeta({
  title: "Signed evidence and AI agent evaluation reports",
  description:
    "What a Suncly report folder contains, what the Ed25519 signature covers, how suncly verify checks it offline, and how to load a report into the review workspace.",
  path: "/docs/evidence",
  type: "article",
  keywords: [...KEYWORDS.evidence, "result.json", "suncly verify", "Ed25519 signed attestation"],
});

const toc = [
  { id: "folder", title: "The report folder" },
  { id: "result", title: "result.json" },
  { id: "transcripts", title: "Transcript files" },
  { id: "signature", title: "What the signature covers" },
  { id: "verify", title: "Verifying" },
  { id: "not-tested", title: "What was NOT tested" },
  { id: "workspace", title: "Loading into the workspace" },
];

const payload = `{
  "payload_version": 1,
  "attestation_id": "…",
  "card_hash": "sha256:…",
  "contract": {"id": "…", "version": 1},
  "results": [
    {"test_case_id": "…", "skill_id": "order-status", "kind": "skill",
     "pass": 5, "fail": 0, "inconclusive": 0}
  ],
  "transcript_hashes": {"<run-id>": "sha256:…"},
  "decision": {"outcome": "flag", "policy_version": "unconfigured"}
}`;

export default function EvidencePage() {
  return (
    <DocLayout
      eyebrow="Evidence and reports"
      headline="Files you can hand to an auditor."
      intro="One folder per attestation, self-contained, verifiable offline, and honest about its gaps. This page describes the format the workspace reads."
      current="/docs/evidence"
      toc={toc}
    >
      <h2 id="folder">The report folder</h2>
      <p><code>suncly-reports/&lt;attestation-id&gt;/</code> holds four kinds of file:</p>
      <ul>
        <li><code>result.json</code>: the evidence bundle, format <code>suncly-result/1</code>.</li>
        <li><code>transcripts/&lt;run-id&gt;.json</code>: one evidence document per recorded run, byte for byte as stored.</li>
        <li><code>report.md</code>: the human-readable report as Markdown.</li>
        <li><code>report.html</code>: the same report, self-contained, no network needed.</li>
      </ul>

      <h2 id="result">result.json</h2>
      <p>The bundle without the inline transcripts (they are the files next to it). Top-level fields, with the data model's names:</p>
      <table>
        <thead>
          <tr>
            <th>Field</th>
            <th>Contents</th>
          </tr>
        </thead>
        <tbody>
          <tr><td><code>agent</code></td><td><code>id</code> (derived from the card URL), <code>name</code>, <code>owner</code>, <code>risk_level</code>.</td></tr>
          <tr><td><code>card_version</code></td><td><code>card_hash</code>, <code>raw_json</code> exactly as fetched, <code>fetched_at</code>.</td></tr>
          <tr><td><code>parsed_card</code></td><td>The card as JSON and as the parsed model: skills, interfaces, capabilities, modes.</td></tr>
          <tr><td><code>card_url</code></td><td>The URL that was fetched.</td></tr>
          <tr><td><code>contract</code>, <code>test_cases</code></td><td>The approved contract (version, status, <code>approved_by</code>, <code>approved_at</code>) and its test cases with <code>input</code> and <code>criteria</code>.</td></tr>
          <tr><td><code>attestation</code></td><td>Status, trigger, timestamps, <code>budget_limit</code>, <code>cost_total</code>, <code>signature</code>, <code>signing_key_id</code>.</td></tr>
          <tr><td><code>runs</code></td><td>Every recorded run (<code>verdict</code>, <code>judge_layer</code>, <code>latency_ms</code>, <code>attempt</code>, <code>transcript_ref</code>) with the <code>document_hash</code> of its transcript file.</td></tr>
          <tr><td><code>decisions</code></td><td>Every decision record, oldest first. The first is the Policy engine's.</td></tr>
          <tr><td><code>results</code></td><td>Per test case: <code>pass_count</code>, <code>fail_count</code>, <code>inconclusive_count</code>. Never combined.</td></tr>
          <tr><td><code>planned_runs</code>, <code>not_executed</code></td><td>How many runs were planned and which never ran, with the reason: <code>budget</code>, <code>runner_crashed</code> or <code>withheld</code>.</td></tr>
          <tr><td><code>card_recheck</code></td><td>What the final re-fetch found: unchanged, changed, unavailable or not performed.</td></tr>
          <tr><td><code>not_tested</code></td><td>The “What was NOT tested” list, category and detail.</td></tr>
          <tr><td><code>sandbox_declared</code>, <code>drafter_name</code></td><td>The sandbox declaration and the source of the test plan.</td></tr>
          <tr><td><code>signer_public_key</code>, <code>signature_payload</code></td><td>The public key (base64url) and the exact payload that was signed.</td></tr>
          <tr><td><code>proposals</code></td><td>The open-question proposals in effect for this run.</td></tr>
        </tbody>
      </table>

      <h2 id="transcripts">Transcript files</h2>
      <p>Each file is one evidence document with two parts:</p>
      <ul>
        <li>
          <code>transcript</code>: the target URL and binding, timestamps, <code>latency_ms</code>, the <code>outcome</code> (responded_task, responded_message, unreachable, timeout, protocol_error), the final task state and final response, every request and response exchanged with headers and bodies after redaction, and a redaction summary naming the rules that fired.
        </li>
        <li>
          <code>judgement</code>: the verdict, the judge layer, a summary, and every check with its name, its <code>passed</code> value (true, false, or null when Layer 1 cannot decide) and a detail such as “expected TASK_STATE_COMPLETED, observed TASK_STATE_INPUT_REQUIRED”.
        </li>
      </ul>
      <p>The file is written once in canonical JSON (RFC 8785). Its SHA-256 is what the signature covers.</p>

      <h2 id="signature">What the signature covers</h2>
      <CodeBlock label="signature payload" code={payload} />
      <p>
        The payload is canonicalized with RFC 8785 and signed with the deployment's Ed25519 key; the signature is stored as <code>ed25519:&lt;base64url&gt;</code> and <code>signing_key_id</code> is a SHA-256 fingerprint of the public key. Failed and invalidated attestations are signed with <code>"decision": null</code>. The signature does not cover a later human decision, the report prose, or anything about the agent's future behaviour.
      </p>

      <h2 id="verify">Verifying</h2>
      <CodeBlock label="verify command" lines code="suncly verify suncly-reports/<attestation-id> [--public-key <base64url>]" />
      <p>Checks, in order: signature present; public key matches <code>signing_key_id</code>; signature valid over the payload; <code>card_hash</code> recomputed from <code>raw_json</code> equals the payload and the record; attestation and contract ids match; every transcript file hashes to its signed value; the recorded decision equals the signed one; the signed per-test-case counts match the recorded runs. The <Link href="/app">workspace</Link> runs the same checks in the browser, with the CLI as the reference.</p>

      <h2 id="not-tested">What was NOT tested</h2>
      <p>Every report carries this section. The categories the current version can emit:</p>
      <ul>
        <li><strong>skill without test case</strong>: a declared skill has no test case (no examples, or left out by the contract file).</li>
        <li><strong>runs never executed</strong>: how many planned runs did not run, and why.</li>
        <li><strong>inconclusive runs</strong>: how many runs ended inconclusive; they count neither as pass nor as fail.</li>
        <li><strong>declared capability not exercised</strong>: streaming, push notifications, extended card, extensions.</li>
        <li><strong>interface not used</strong>: other bindings or URLs the card lists.</li>
        <li><strong>probes</strong>: no probe test cases of the data model's probe kinds exist; a behavioural suite's negative security cases are the current form.</li>
        <li><strong>semantic correctness</strong>: Layer 1 checks structure, state, output modes and latency; meaning is judged by Layer 2 (a pinned model) only where a rubric exists and a provider is configured, otherwise it is inconclusive.</li>
        <li><strong>production endpoint</strong>: tests ran against the declared sandbox only.</li>
        <li><strong>card observation</strong>: fields the A2A specification marks REQUIRED that the card omits.</li>
      </ul>

      <h2 id="workspace">Loading into the workspace</h2>
      <p>
        Open <Link href="/app/import">Import</Link>, then drop <code>result.json</code> together with the files from <code>transcripts/</code> (or select the whole report folder). The workspace validates the format, keeps the transcript text byte for byte so hashes can be re-checked, and stores the bundle in this browser only. Nothing is uploaded anywhere. Remove a bundle from the workspace settings at any time.
      </p>
    </DocLayout>
  );
}
