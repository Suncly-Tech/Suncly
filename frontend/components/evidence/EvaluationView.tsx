"use client";

import { useState, type ReactNode } from "react";
import { Tabs } from "@/components/ui/Tabs";
import { Card, CardHeader } from "@/components/ui/Card";
import { Notice } from "@/components/ui/Notice";
import { Stat } from "@/components/ui/Stat";
import { EvaluationHeader } from "./EvaluationHeader";
import { TestCaseTable } from "./TestCaseTable";
import { NotTestedList, SkillCoverageList } from "./NotTested";
import { RunsTable } from "./Runs";
import { ExecutionPanel, ProposalsList } from "./Execution";
import { SignaturePanel } from "./Signature";
import { CardPanel } from "./CardPanel";
import { pendingActions, testCaseRows, totals } from "@/lib/evidence/derive";
import type { EvidenceBundle } from "@/lib/evidence/types";

export type EvaluationTab =
  | "summary"
  | "tests"
  | "coverage"
  | "card"
  | "execution"
  | "signature"
  | "review";

/**
 * One attestation, in tabs: the same component serves the public sample and the
 * workspace. `review` is a slot so the sample can show a static record and the workspace a
 * form.
 */
export function EvaluationView({
  bundle,
  sample = false,
  initialTab = "summary",
  review,
  actions,
  hasLocalReview = false,
  heading = "h1",
}: {
  bundle: EvidenceBundle;
  sample?: boolean;
  initialTab?: EvaluationTab;
  review?: ReactNode;
  actions?: ReactNode;
  hasLocalReview?: boolean;
  heading?: "h1" | "h2";
}) {
  const { result } = bundle;
  const [tab, setTab] = useState<EvaluationTab>(initialTab);
  const [selectedTestCase, setSelectedTestCase] = useState<string | null>(null);
  const sums = totals(result);
  const rows = testCaseRows(result);
  const actionsPending = pendingActions(result, hasLocalReview);
  const inconsistent = rows.filter((r) => r.inconsistent);
  const undecided = rows.filter((r) => r.undecided);

  const items = [
    { id: "summary", label: "Summary" },
    { id: "tests", label: "Tests and evidence", count: result.runs.length },
    { id: "coverage", label: "Coverage gaps", count: result.not_tested.length },
    { id: "card", label: "Agent Card" },
    { id: "execution", label: "Execution" },
    { id: "signature", label: "Signature" },
    ...(review ? [{ id: "review", label: "Review" }] : []),
  ];

  return (
    <div className="flex flex-col gap-8">
      <EvaluationHeader
        result={result}
        sample={sample}
        actions={actions}
        heading={heading}
      />

      <Tabs
        items={items}
        value={tab}
        onChange={(id) => setTab(id as EvaluationTab)}
        label="Evaluation sections"
      />

      <div
        id={`panel-${tab}`}
        role="tabpanel"
        tabIndex={0}
        className="flex flex-col gap-6 focus:outline-none"
      >
        {tab === "summary" ? (
          <>
            {actionsPending.length ? (
              <div className="flex flex-col gap-3">
                {actionsPending.map((action) => (
                  <Notice
                    key={action.kind}
                    tone={action.kind === "human_review" ? "warn" : "error"}
                    title={action.title}
                    role="status"
                  >
                    {action.detail}
                  </Notice>
                ))}
              </div>
            ) : null}

            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <Stat
                label="Pass"
                value={sums.pass}
                tone="pass"
                hint="runs with every check passed"
              />
              <Stat
                label="Fail"
                value={sums.fail}
                tone="fail"
                hint="runs with a failed check"
              />
              <Stat
                label="Inconclusive"
                value={sums.inconclusive}
                tone="inconclusive"
                hint="never counted as a pass"
              />
              <Stat
                label="Runs recorded"
                value={`${sums.recorded}${sums.planned !== null ? ` / ${sums.planned}` : ""}`}
                tone={sums.notExecuted ? "fail" : "ink"}
                hint={
                  sums.notExecuted
                    ? `${sums.notExecuted} planned run(s) never executed`
                    : "every planned run recorded"
                }
              />
            </div>

            {inconsistent.length || undecided.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {inconsistent.length ? (
                  <Notice
                    tone="error"
                    title={`Inconsistent behaviour on ${inconsistent.length} test case${inconsistent.length === 1 ? "" : "s"}`}
                  >
                    The same input passed on some runs and failed on others:{" "}
                    {inconsistent.map((r) => `“${r.inputText}”`).join(", ")}.
                    One manual prompt would have shown only one of those
                    outcomes.
                  </Notice>
                ) : null}
                {undecided.length ? (
                  <Notice
                    tone="warn"
                    title={`${undecided.length} test case${undecided.length === 1 ? "" : "s"} undecided`}
                  >
                    Every run was inconclusive:{" "}
                    {undecided.map((r) => `“${r.inputText}”`).join(", ")}. Open
                    the run evidence to see which check Layer 1 could not
                    decide.
                  </Notice>
                ) : null}
              </div>
            ) : null}

            <Card padded={false} className="overflow-hidden">
              <div className="p-5 pb-0 md:p-6 md:pb-0">
                <CardHeader
                  title="Results per test case"
                  description="Pass, fail and inconclusive are shown side by side. Suncly never combines them into a score."
                />
              </div>
              <div className="p-5 pt-0 md:p-6 md:pt-0">
                <TestCaseTable
                  result={result}
                  onSelect={(id) => {
                    setSelectedTestCase(id);
                    setTab("tests");
                  }}
                />
              </div>
            </Card>

            <Card>
              <CardHeader
                title="What was not tested"
                description="Straight from the report. An approval on this evidence is an approval with these gaps."
              />
              <NotTestedList result={result} compact />
            </Card>
          </>
        ) : null}

        {tab === "tests" ? (
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader
                title="Test cases"
                description="Select a row to filter the runs below. Each test case is one declared example of a skill, with the criteria the reviewer approved."
                action={
                  selectedTestCase ? (
                    <button
                      type="button"
                      onClick={() => setSelectedTestCase(null)}
                      className="btn-base btn-secondary btn-sm"
                    >
                      Show all runs
                    </button>
                  ) : null
                }
              />
              <TestCaseTable
                result={result}
                selected={selectedTestCase}
                onSelect={(id) =>
                  setSelectedTestCase(id === selectedTestCase ? null : id)
                }
              />
            </Card>
            {selectedTestCase ? (
              <CriteriaCard bundle={bundle} testCaseId={selectedTestCase} />
            ) : null}
            <Card>
              <CardHeader
                title={
                  selectedTestCase
                    ? "Runs for the selected test case"
                    : "All recorded runs"
                }
                description="Open a run to see every check with its expected and observed value, the final response, and the redacted exchange."
              />
              <RunsTable bundle={bundle} testCaseId={selectedTestCase} />
            </Card>
          </div>
        ) : null}

        {tab === "coverage" ? (
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader
                title="Declared skills and their coverage"
                description="Every skill the card declares, whether it has a test case, and why not when it does not."
              />
              <SkillCoverageList result={result} />
            </Card>
            <Card>
              <CardHeader
                title="What was not tested"
                description="The report's own list. Categories and wording are the CLI's."
              />
              <NotTestedList result={result} />
            </Card>
          </div>
        ) : null}

        {tab === "card" ? (
          <Card>
            <CardHeader
              title="Agent Card"
              description="The claims under test, exactly as fetched and hashed at the start of the evaluation."
            />
            <CardPanel result={result} />
          </Card>
        ) : null}

        {tab === "execution" ? (
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader
                title="Execution"
                description="Environment, configuration, budget and timestamps from the attestation record. Nothing here is estimated."
              />
              <ExecutionPanel result={result} />
            </Card>
            <Card>
              <ProposalsList result={result} />
            </Card>
          </div>
        ) : null}

        {tab === "signature" ? (
          <Card>
            <CardHeader
              title="Signature and verification"
              description="What is signed, with which key, and how to check it. A valid signature proves the evidence was not altered; it does not prove the agent is correct."
            />
            <SignaturePanel bundle={bundle} />
          </Card>
        ) : null}

        {tab === "review" && review ? review : null}
      </div>
    </div>
  );
}

function CriteriaCard({
  bundle,
  testCaseId,
}: {
  bundle: EvidenceBundle;
  testCaseId: string;
}) {
  const tc = bundle.result.test_cases.find((t) => t.id === testCaseId);
  if (!tc) return null;
  const c = tc.criteria;
  return (
    <Card>
      <CardHeader
        title="Approved criteria for this test case"
        description={`Contract version ${bundle.result.contract.version}, approved by ${bundle.result.contract.approved_by ?? "–"}.`}
        as="h3"
      />
      <dl className="kv">
        <dt>Input sent</dt>
        <dd>“{tc.input.text ?? JSON.stringify(tc.input.parts)}”</dd>
        <dt>Expected final state</dt>
        <dd className="font-mono text-[13px]">{c.final_state}</dd>
        <dt>Latency limit</dt>
        <dd className="font-mono text-[13px]">{c.latency_limit_ms} ms</dd>
        <dt>Response present</dt>
        <dd>{c.response_present ? "required" : "not required"}</dd>
        <dt>Output modes</dt>
        <dd className="font-mono text-[13px]">
          {c.output_modes ? c.output_modes.join(", ") : "not checked"}
        </dd>
        <dt>Required fields</dt>
        <dd className="font-mono text-[13px]">
          {c.required_fields.length ? c.required_fields.join(", ") : "none"}
        </dd>
        <dt>Response schema</dt>
        <dd className="font-mono text-[13px]">
          {c.response_schema ? JSON.stringify(c.response_schema) : "none"}
        </dd>
        <dt>Model checks</dt>
        <dd>
          {c.model_checks.length ? (
            <>
              {c.model_checks.join("; ")}{" "}
              <span className="text-partial">
                (needs Judge Layer 2, stage 4; every run is inconclusive until
                then)
              </span>
            </>
          ) : (
            "none"
          )}
        </dd>
        <dt>Direct Message accepted</dt>
        <dd>{c.accept_direct_message ? "yes" : "no"}</dd>
      </dl>
    </Card>
  );
}
