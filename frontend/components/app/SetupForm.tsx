"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Card, CardHeader } from "@/components/ui/Card";
import { Field, Input, Select, Checkbox, describedBy } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { CodeBlock } from "@/components/ui/CodeBlock";
import { Badge, AvailabilityBadge } from "@/components/ui/Badge";
import { PageTitle } from "./PageTitle";
import {
  buildAttestCommand,
  buildExportDraftCommand,
  credentialLines,
  DEFAULTS,
  validateAttest,
  type AttestOptions,
} from "@/lib/cli";

const initial: AttestOptions = {
  cardUrl: "",
  sandboxDeclared: false,
  runs: null,
  budget: null,
  approveAs: "",
  owner: "",
  riskLevel: "",
  contractPath: "",
  reportsDir: DEFAULTS.reportsDir,
  needsCredential: false,
  json: false,
};

/**
 * Evaluation setup. The browser cannot start a run (no HTTP API yet; the Runner must hold
 * the credential in its own process), so this form validates the configuration and
 * produces the exact commands. Every option maps to a real CLI option.
 */
export function SetupForm() {
  const [o, setO] = useState<AttestOptions>(initial);
  const [shell, setShell] = useState<"posix" | "powershell">("posix");
  const [exportDraft, setExportDraft] = useState(false);
  const [touched, setTouched] = useState(false);
  const issues = useMemo(() => validateAttest(o), [o]);
  const issueFor = (field: keyof AttestOptions) => (touched ? issues.find((i) => i.field === field)?.message ?? null : null);
  const set = <K extends keyof AttestOptions>(key: K, value: AttestOptions[K]) => setO((prev) => ({ ...prev, [key]: value }));
  const ready = issues.length === 0 && o.cardUrl.trim();

  const commands = useMemo(() => {
    const lines: string[] = [];
    if (o.needsCredential) lines.push(...credentialLines(shell));
    lines.push(`suncly doctor ${o.cardUrl.trim() || "<card-url>"}`);
    if (exportDraft) {
      lines.push(buildExportDraftCommand(o, o.contractPath.trim() || "contract.json"));
      lines.push("# edit the file: required_fields, response_schema, latency_limit_ms, output_modes");
    }
    lines.push(buildAttestCommand({ ...o, contractPath: exportDraft ? o.contractPath.trim() || "contract.json" : o.contractPath }));
    return lines.join("\n");
  }, [o, shell, exportDraft]);

  return (
    <>
      <PageTitle
        title="New evaluation"
        intro="Configure the evaluation, then run it with the CLI. The workspace cannot start runs in this version: there is no HTTP API, and the Runner must hold the agent credential in its own process on your machine."
      />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)]">
        <form className="flex flex-col gap-6" onSubmit={(e) => { e.preventDefault(); setTouched(true); }} noValidate>
          <Card>
            <CardHeader title="1. Agent" description="The agent is identified by its Agent Card URL. Suncly derives a stable agent id from it and records owner and risk level on first sight." as="h2" />
            <div className="flex flex-col gap-4">
              <Field id="card-url" label="Agent Card URL" required error={issueFor("cardUrl")} help="Usually https://<host>/.well-known/agent-card.json. Plain http is accepted for 127.0.0.1 and localhost only.">
                <Input
                  id="card-url"
                  type="url"
                  inputMode="url"
                  placeholder="https://sandbox.example.com/.well-known/agent-card.json"
                  value={o.cardUrl}
                  onChange={(e) => set("cardUrl", e.target.value)}
                  onBlur={() => setTouched(true)}
                  aria-invalid={issueFor("cardUrl") ? true : undefined}
                  aria-describedby={describedBy("card-url", true, Boolean(issueFor("cardUrl")))}
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field id="owner" label="Owner (agent.owner)" help="Recorded on first sight of this card URL. Default: unspecified.">
                  <Input id="owner" value={o.owner} onChange={(e) => set("owner", e.target.value)} placeholder="payments-platform" aria-describedby="owner-help" />
                </Field>
                <Field id="risk" label="Risk level (agent.risk_level)" help="Default high, the most restrictive. Recorded; it does not change the outcome yet.">
                  <Select id="risk" value={o.riskLevel} onChange={(e) => set("riskLevel", e.target.value as AttestOptions["riskLevel"])} aria-describedby="risk-help">
                    <option value="">high (default)</option>
                    <option value="low">low</option>
                    <option value="medium">medium</option>
                    <option value="high">high</option>
                  </Select>
                </Field>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="2. Access and environment" description="Suncly tests sandboxes only, and the credential never passes through this page." as="h2" />
            <div className="flex flex-col gap-4">
              <Checkbox
                id="sandbox"
                label="This endpoint is a sandbox or dry-run endpoint"
                description="Required (DR-006). Without the declaration nothing runs. Suncly cannot verify a sandbox; this is your declaration, and the report records it."
                checked={o.sandboxDeclared}
                onChange={(e) => set("sandboxDeclared", e.target.checked)}
                aria-invalid={issueFor("sandboxDeclared") ? true : undefined}
              />
              {issueFor("sandboxDeclared") ? (
                <p role="alert" className="text-[13px] font-medium text-fail">{issueFor("sandboxDeclared")}</p>
              ) : null}
              <Checkbox
                id="credential"
                label="The sandbox requires an Authorization header"
                description="The value goes into the environment variable SUNCLY_AGENT_AUTHORIZATION on the machine that runs the CLI. Only the Runner process reads it, and it is redacted from every transcript. Do not enter the token here or anywhere in a browser."
                checked={o.needsCredential}
                onChange={(e) => set("needsCredential", e.target.checked)}
              />
              <Field id="shell" label="Shell for the commands">
                <Select id="shell" value={shell} onChange={(e) => setShell(e.target.value as "posix" | "powershell")}>
                  <option value="posix">bash / zsh (macOS, Linux)</option>
                  <option value="powershell">PowerShell (Windows)</option>
                </Select>
              </Field>
              <Notice tone="info" title="Prerequisites on the machine that runs the CLI">
                Python 3.12 or newer, the suncly package installed, network access to the card URL and the agent endpoint only, and a deployment signing key (created on first run). <code className="code-inline">suncly doctor</code> checks all of it.
              </Notice>
            </div>
          </Card>

          <Card>
            <CardHeader title="3. Test scope and success criteria" description="One test case per declared example of each skill, with structural criteria. A person approves the plan before anything runs." as="h2" />
            <div className="flex flex-col gap-4">
              <ul className="flex flex-col gap-2 text-small text-ink-soft">
                <li className="cuts-bullet text-sun"><span className="text-ink">Drafted:</span> the task reaches TASK_STATE_COMPLETED, answers with content, uses the skill's declared output modes, within {DEFAULTS.latencyLimitMs} ms (configurable).</li>
                <li className="cuts-bullet text-sun"><span className="text-ink">Yours to add in the contract file:</span> required fields (JSON pointers), a JSON Schema for the response, a tighter latency limit, a different expected final state.</li>
                <li className="cuts-bullet text-sun"><span className="text-ink">Not available yet:</span> model-based checks about the meaning of an answer (any model_checks entry makes the run inconclusive), probes for injection, undeclared behaviour and failure handling.</li>
                <li className="cuts-bullet text-sun"><span className="text-ink">Skills without examples</span> get no test case and are reported as not tested. Add examples to the card or a test case to the file.</li>
              </ul>
              <Checkbox
                id="export-draft"
                label="Review and edit the test plan as a file before running"
                description="Exports the draft contract to a file, which you edit and pass back with --contract. Approval is still recorded as a separate step."
                checked={exportDraft}
                onChange={(e) => setExportDraft(e.target.checked)}
              />
              {exportDraft ? (
                <Field id="contract-path" label="Contract file path" help="Where the draft is written and read from.">
                  <Input id="contract-path" value={o.contractPath} onChange={(e) => set("contractPath", e.target.value)} placeholder="contract.json" />
                </Field>
              ) : null}
              <Field id="approve-as" label="Approver identifier (recorded as approved_by)" required error={issueFor("approveAs")} help="Use the identifier your review process recognises, for example a work email. Leave empty only if you will approve at the interactive prompt.">
                <Input id="approve-as" value={o.approveAs} onChange={(e) => set("approveAs", e.target.value)} placeholder="reviewer@company.com" autoComplete="email" aria-invalid={issueFor("approveAs") ? true : undefined} aria-describedby={describedBy("approve-as", true, Boolean(issueFor("approveAs")))} />
              </Field>
            </div>
          </Card>

          <Card>
            <CardHeader title="4. Run limits" description="Repetitions expose inconsistent behaviour; the budget caps the cost. Both are shown by the CLI before anything runs." as="h2" />
            <div className="grid gap-4 sm:grid-cols-2">
              <Field id="runs" label="Runs per test case" error={issueFor("runs")} help={`Default ${DEFAULTS.runs}. Each run is a separate Runner process.`}>
                <Input id="runs" type="number" min={1} step={1} inputMode="numeric" value={o.runs ?? ""} onChange={(e) => set("runs", e.target.value === "" ? null : Number(e.target.value))} placeholder={String(DEFAULTS.runs)} aria-invalid={issueFor("runs") ? true : undefined} />
              </Field>
              <Field id="budget" label="Budget (attempts)" error={issueFor("budget")} help={`Default ${DEFAULTS.budgetFactor} × planned runs. Retries count. When reached, the attestation ends failed and lists the runs never executed.`}>
                <Input id="budget" type="number" min={0} step={1} inputMode="numeric" value={o.budget ?? ""} onChange={(e) => set("budget", e.target.value === "" ? null : Number(e.target.value))} placeholder="2 × planned" aria-invalid={issueFor("budget") ? true : undefined} />
              </Field>
              <Field id="reports-dir" label="Reports folder" help="One folder per attestation is written here; import it afterwards.">
                <Input id="reports-dir" value={o.reportsDir} onChange={(e) => set("reportsDir", e.target.value)} />
              </Field>
              <div className="flex flex-col gap-3 pt-7">
                <Checkbox id="json" label="Machine-readable output (--json)" description="For pipelines. Progress goes to stderr." checked={o.json} onChange={(e) => set("json", e.target.checked)} />
              </div>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Badge tone="neutral">Per-run timeout {DEFAULTS.runTimeoutS} s</Badge>
              <Badge tone="neutral">Retries {DEFAULTS.maxRetries}, same run key</Badge>
              <Badge tone="neutral">Concurrency {DEFAULTS.concurrency}</Badge>
              <span className="self-center text-[12px] text-ink-soft">Change these with SUNCLY_* environment variables or config.toml.</span>
            </div>
          </Card>

          <button type="submit" className="sr-only">Validate</button>
        </form>

        <div className="flex flex-col gap-6 lg:sticky lg:top-24 lg:self-start">
          <Card>
            <CardHeader title="5. Run it" description="Copy and run on the machine that can reach the sandbox. Shown exactly as the CLI accepts it." as="h2" />
            {touched && issues.length ? (
              <Notice tone="error" title={`${issues.length} thing${issues.length === 1 ? "" : "s"} to fix first`} role="alert" className="mb-4">
                <ul className="list-disc pl-4">
                  {issues.map((i) => (
                    <li key={i.field}>{i.message}</li>
                  ))}
                </ul>
              </Notice>
            ) : null}
            <CodeBlock code={commands} label="evaluation commands" lines />
            {!ready ? <p className="mt-3 text-[13px] text-ink-soft">Fill in the card URL, confirm the sandbox declaration and name the approver to complete the command.</p> : null}
          </Card>

          <Card>
            <CardHeader title="While it runs" description="What the CLI shows, live, in the terminal. This page does not mirror it: there is no channel from the CLI to the browser." as="h3" />
            <ul className="flex flex-col gap-2 text-small text-ink-soft">
              <li className="cuts-bullet text-sun">The card fetched and hashed, and the target endpoint.</li>
              <li className="cuts-bullet text-sun">The contract version and who approved it, or the draft waiting for your approval.</li>
              <li className="cuts-bullet text-sun">The plan: test cases × runs = planned runs, and the budget.</li>
              <li className="cuts-bullet text-sun">One line per recorded run with its verdict, latency and summary; retries and withheld transcripts are announced.</li>
              <li className="cuts-bullet text-sun">A budget stop, the card re-check, the decision line, the signature, what was not tested, and the report folder.</li>
            </ul>
          </Card>

          <Card>
            <CardHeader title="6. Afterwards" as="h3" />
            <p className="text-small text-ink-soft">
              <Link href="/app/import" className="font-semibold text-ink underline underline-offset-4">Import the report folder</Link> to inspect results and evidence, verify the signature, record a review note and compare with the previous evaluation.
            </p>
            <div className="mt-4 flex flex-col gap-2 text-[13px]">
              <div className="flex items-center justify-between gap-3"><span className="text-ink-soft">Start runs from this page</span><AvailabilityBadge status="planned" /></div>
              <div className="flex items-center justify-between gap-3"><span className="text-ink-soft">Schedules and card-change triggers</span><AvailabilityBadge status="planned" /></div>
              <div className="flex items-center justify-between gap-3"><span className="text-ink-soft">Run from CI with the CLI</span><AvailabilityBadge status="available" /></div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}
