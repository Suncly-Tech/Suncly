/**
 * Views derived from a result document. Everything here is a re-arrangement of what the
 * CLI wrote; nothing is scored, weighted or combined. Inconclusive is never a pass.
 */

import type {
  AttestationStatus,
  CheckResult,
  Decision,
  DecisionOutcome,
  EvidenceBundle,
  EvidenceDocument,
  ResultDocument,
  RunVerdict,
  TestCase,
  TestCaseResult,
} from "./types";

export const POLICY_DECIDED_BY = "policy";

export interface Totals {
  pass: number;
  fail: number;
  inconclusive: number;
  recorded: number;
  planned: number | null;
  notExecuted: number;
}

export function totals(result: ResultDocument): Totals {
  const sum = (key: keyof Pick<TestCaseResult, "pass_count" | "fail_count" | "inconclusive_count">) =>
    result.results.reduce((acc, row) => acc + row[key], 0);
  return {
    pass: sum("pass_count"),
    fail: sum("fail_count"),
    inconclusive: sum("inconclusive_count"),
    recorded: result.runs.length,
    planned: result.planned_runs,
    notExecuted: result.not_executed.length,
  };
}

/** Evaluation status: what happened to the attestation itself. */
export const STATUS_LABEL: Record<AttestationStatus, string> = {
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  invalidated: "Invalidated",
};

export const STATUS_EXPLANATION: Record<AttestationStatus, string> = {
  queued: "Created and waiting to run.",
  running: "Runs are in progress.",
  completed: "Every planned run was judged, the card was unchanged at the end, a decision was recorded and the attestation was signed.",
  failed: "The budget stopped it or the card could not be re-fetched at the end. No decision is made for a failed attestation.",
  cancelled: "Stopped before it finished. No decision.",
  invalidated: "The Agent Card changed while the attestation ran. The results describe a card that no longer exists; a new contract needs approval. No decision.",
};

export type DecisionState =
  | { kind: "automatic_flag"; decision: Decision; human: Decision[] }
  | { kind: "automatic"; decision: Decision; human: Decision[] }
  | { kind: "none"; reason: string };

/** Approval status: what the Policy engine recorded, separate from evaluation status. */
export function decisionState(result: ResultDocument): DecisionState {
  const policy = result.decisions.find((d) => d.decided_by === POLICY_DECIDED_BY);
  const human = result.decisions.filter((d) => d.decided_by !== POLICY_DECIDED_BY);
  if (!policy) {
    const status = result.attestation.status;
    return {
      kind: "none",
      reason:
        status === "failed"
          ? "No decision: the attestation ended failed."
          : status === "invalidated"
            ? "No decision: the card changed during the attestation."
            : status === "cancelled"
              ? "No decision: the attestation was cancelled."
              : `No decision yet: the attestation is ${status}.`,
    };
  }
  if (policy.outcome === "flag") return { kind: "automatic_flag", decision: policy, human };
  return { kind: "automatic", decision: policy, human };
}

export const OUTCOME_LABEL: Record<DecisionOutcome, string> = {
  approve: "Approve",
  flag: "Flag for human review",
  block: "Block",
};

export interface TestCaseRow {
  testCase: TestCase;
  result: TestCaseResult;
  skillName: string;
  inputText: string;
  /** Both pass and fail recorded for the same test case across repeated runs. */
  inconsistent: boolean;
  /** Every run was inconclusive, so nothing was decided for this test case. */
  undecided: boolean;
}

export function inputText(testCase: TestCase): string {
  if (typeof testCase.input.text === "string") return testCase.input.text;
  return JSON.stringify(testCase.input.parts ?? testCase.input);
}

export function skillName(result: ResultDocument, skillId: string | null): string {
  if (!skillId) return "probe";
  const skill = result.parsed_card.card.skills.find((s) => s.id === skillId);
  return skill?.name ?? skillId;
}

export function testCaseRows(result: ResultDocument): TestCaseRow[] {
  const byId = new Map(result.test_cases.map((tc) => [tc.id, tc]));
  return result.results
    .map((row) => {
      const testCase = byId.get(row.test_case_id);
      if (!testCase) return null;
      const total = row.pass_count + row.fail_count + row.inconclusive_count;
      return {
        testCase,
        result: row,
        skillName: skillName(result, row.skill_id),
        inputText: inputText(testCase),
        inconsistent: row.pass_count > 0 && row.fail_count > 0,
        undecided: total > 0 && row.inconclusive_count === total,
      };
    })
    .filter((row): row is TestCaseRow => row !== null);
}

export interface RunView {
  run: ResultDocument["runs"][number]["run"];
  documentHash: string;
  testCase: TestCase | undefined;
  skillName: string;
  document: EvidenceDocument | null;
  parseError: string | null;
}

export function parseDocument(text: string | undefined): { document: EvidenceDocument | null; error: string | null } {
  if (text === undefined) return { document: null, error: "transcript file not in this bundle" };
  try {
    const parsed = JSON.parse(text) as EvidenceDocument;
    if (!parsed || typeof parsed !== "object" || !("transcript" in parsed) || !("judgement" in parsed)) {
      return { document: null, error: "the transcript file is not an evidence document" };
    }
    return { document: parsed, error: null };
  } catch (error) {
    return { document: null, error: `the transcript file is not valid JSON: ${String(error)}` };
  }
}

export function runViews(bundle: EvidenceBundle): RunView[] {
  const { result, transcripts } = bundle;
  const byId = new Map(result.test_cases.map((tc) => [tc.id, tc]));
  return result.runs
    .map((entry) => {
      const { document, error } = parseDocument(transcripts[entry.run.id]);
      const testCase = byId.get(entry.run.test_case_id);
      return {
        run: entry.run,
        documentHash: entry.document_hash,
        testCase,
        skillName: skillName(result, testCase?.skill_id ?? null),
        document,
        parseError: error,
      };
    })
    .sort((a, b) =>
      a.run.test_case_id === b.run.test_case_id
        ? a.run.attempt - b.run.attempt
        : a.run.test_case_id < b.run.test_case_id
          ? -1
          : 1,
    );
}

/** Human labels for the Layer 1 check names in core/judge.py. */
export function checkLabel(name: string): string {
  if (name === "valid_schema") return "Valid A2A response";
  if (name === "final_task_state") return "Final task state";
  if (name === "latency_limit") return "Latency limit";
  if (name === "response_present") return "Response present";
  if (name === "output_modes") return "Declared output modes";
  if (name === "response_schema") return "Response schema";
  if (name === "response_received") return "Response received";
  if (name === "transcript_readable") return "Transcript readable";
  if (name.startsWith("required_field ")) return `Required field ${name.slice("required_field ".length)}`;
  if (name.startsWith("model_check ")) return `Model check: ${name.slice("model_check ".length)}`;
  return name;
}

/** Split a check's detail into expected and observed where the detail has that form. */
export function expectedObserved(check: CheckResult): { expected: string; observed: string } | null {
  const m = /^expected (.+), observed (.+)$/.exec(check.detail);
  if (m) return { expected: m[1], observed: m[2] };
  const latency = /^(\S+) ms against a limit of (\d+) ms$/.exec(check.detail);
  if (latency) return { expected: `≤ ${latency[2]} ms`, observed: `${latency[1]} ms` };
  const modes = /^declared (\[.*\]); (.+)$/.exec(check.detail);
  if (modes) return { expected: modes[1].replace(/'/g, ""), observed: modes[2] };
  return null;
}

export function checkState(check: CheckResult): "passed" | "failed" | "undecided" {
  return check.passed === true ? "passed" : check.passed === false ? "failed" : "undecided";
}

export interface SkillCoverage {
  id: string;
  name: string;
  description: string;
  tags: string[];
  examples: string[];
  testCases: TestCase[];
  tested: boolean;
  reason: string | null;
  verdicts: { pass: number; fail: number; inconclusive: number };
}

export function skillCoverage(result: ResultDocument): SkillCoverage[] {
  return result.parsed_card.card.skills.map((skill) => {
    const testCases = result.test_cases.filter((tc) => tc.skill_id === skill.id && tc.kind === "skill");
    const rows = result.results.filter((r) => r.skill_id === skill.id);
    const notTested = result.not_tested.find(
      (item) => item.category === "skill without test case" && item.detail.includes(`'${skill.id}'`),
    );
    return {
      id: skill.id,
      name: skill.name || skill.id,
      description: skill.description,
      tags: skill.tags,
      examples: skill.examples ?? [],
      testCases,
      tested: testCases.length > 0,
      reason: notTested
        ? (skill.examples ?? []).length === 0
          ? "The card declares no examples for this skill, and Suncly never invents input."
          : "Left out of the approved contract."
        : null,
      verdicts: {
        pass: rows.reduce((a, r) => a + r.pass_count, 0),
        fail: rows.reduce((a, r) => a + r.fail_count, 0),
        inconclusive: rows.reduce((a, r) => a + r.inconclusive_count, 0),
      },
    };
  });
}

export interface PendingAction {
  kind: "human_review" | "rerun" | "approve_contract" | "none";
  title: string;
  detail: string;
}

export function pendingActions(result: ResultDocument, hasLocalReview: boolean): PendingAction[] {
  const actions: PendingAction[] = [];
  const status = result.attestation.status;
  const decision = decisionState(result);
  if (decision.kind === "automatic_flag" && decision.human.length === 0 && !hasLocalReview) {
    actions.push({
      kind: "human_review",
      title: "Needs a human decision",
      detail: "The Policy engine recorded flag. A reviewer has to decide on this evidence.",
    });
  }
  if (status === "failed") {
    actions.push({
      kind: "rerun",
      title: "Re-run with a sufficient budget",
      detail: `${result.not_executed.length} planned run(s) were never executed. The attestation carries no decision.`,
    });
  }
  if (status === "invalidated") {
    actions.push({
      kind: "approve_contract",
      title: "Approve a contract for the changed card",
      detail: "The card changed mid-run. The next attestation drafts a new contract that needs approval.",
    });
  }
  return actions;
}

export function budgetUsage(result: ResultDocument): { cost: number; limit: number; fraction: number } {
  const cost = Number(result.attestation.cost_total);
  const limit = Number(result.attestation.budget_limit);
  return { cost, limit, fraction: limit > 0 ? Math.min(cost / limit, 1) : 0 };
}

export function notExecutedByReason(result: ResultDocument): Record<string, number> {
  const out: Record<string, number> = {};
  for (const item of result.not_executed) out[item.reason] = (out[item.reason] ?? 0) + 1;
  return out;
}

export function verdictLabel(verdict: RunVerdict): string {
  return verdict === "pass" ? "Pass" : verdict === "fail" ? "Fail" : "Inconclusive";
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "–";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("en-GB", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    timeZoneName: "short",
  });
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "–";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "2-digit", timeZone: "UTC" });
}

export function durationSeconds(start: string, end: string | null): string {
  if (!end) return "–";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (!Number.isFinite(ms)) return "–";
  return ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`;
}

/** Interface actually used by the Runner: the first JSON-RPC 1.0 interface (core/cards.py). */
export function targetInterface(result: ResultDocument) {
  const interfaces = result.parsed_card.card.supported_interfaces;
  return (
    interfaces.find((i) => i.protocol_binding === "JSONRPC" && i.protocol_version === "1.0") ??
    interfaces[0]
  );
}

/** Group a transcript's redaction statistics across runs. */
export function redactionSummary(bundle: EvidenceBundle): { replacements: number; rules: string[] } {
  let replacements = 0;
  const rules = new Set<string>();
  for (const view of runViews(bundle)) {
    const redaction = view.document?.transcript.redaction;
    if (!redaction) continue;
    replacements += redaction.replacements;
    for (const rule of redaction.rules) rules.add(rule);
  }
  return { replacements, rules: [...rules].sort() };
}

export function isResultDocument(value: unknown): value is ResultDocument {
  if (!value || typeof value !== "object") return false;
  const doc = value as Partial<ResultDocument>;
  return (
    doc.format === "suncly-result/1" &&
    typeof doc.attestation === "object" &&
    doc.attestation !== null &&
    Array.isArray(doc.runs) &&
    Array.isArray(doc.results) &&
    typeof doc.agent === "object"
  );
}
