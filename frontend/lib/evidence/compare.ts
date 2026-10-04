/**
 * Comparing two attestations of the same agent. Computed in the workspace from the two
 * signed bundles; Suncly's own store has no comparison operation yet (the Policy
 * engine's "drop" detection is an open question, OQ-PO2). The comparison matches test
 * cases by content, so a changed criterion is reported as a changed test, not as a
 * change in the agent.
 */

import { canonicalize } from "./jcs";
import { inputText, skillName } from "./derive";
import type { ResultDocument, TestCase, TestCaseResult } from "./types";

export type TestCaseChange = "regressed" | "improved" | "unchanged" | "mixed" | "no_runs";

export interface TestCaseComparison {
  key: string;
  skillId: string | null;
  skillName: string;
  input: string;
  before: TestCaseResult | null;
  after: TestCaseResult | null;
  change: TestCaseChange | "added" | "removed";
  /** Criteria differ between the two contracts although skill and input match. */
  criteriaChanged: boolean;
}

export interface Comparison {
  older: ResultDocument;
  newer: ResultDocument;
  sameAgent: boolean;
  cardHashChanged: boolean;
  contractChanged: boolean;
  statusChanged: boolean;
  decisionChanged: boolean;
  testCases: TestCaseComparison[];
  notTestedAdded: string[];
  notTestedRemoved: string[];
  summary: { regressed: number; improved: number; unchanged: number; mixed: number; no_runs: number; added: number; removed: number };
}

function identityKey(tc: TestCase): string {
  return canonicalize({ skill_id: tc.skill_id, kind: tc.kind, input: tc.input });
}

function contentKey(tc: TestCase): string {
  return canonicalize({ skill_id: tc.skill_id, kind: tc.kind, input: tc.input, criteria: tc.criteria });
}

function total(r: TestCaseResult): number {
  return r.pass_count + r.fail_count + r.inconclusive_count;
}

function classify(before: TestCaseResult, after: TestCaseResult): TestCaseChange {
  // A test case with no recorded runs on either side (budget stop, crash) is not a change
  // in the agent; it is missing evidence.
  if (total(after) === 0 || total(before) === 0) return "no_runs";
  const worse = after.fail_count > before.fail_count || after.pass_count < before.pass_count;
  const better = after.fail_count < before.fail_count || after.pass_count > before.pass_count;
  if (worse && better) return "mixed";
  if (worse) return "regressed";
  if (better) return "improved";
  return "unchanged";
}

export function compareEvaluations(older: ResultDocument, newer: ResultDocument): Comparison {
  const olderResults = new Map(older.results.map((r) => [r.test_case_id, r]));
  const newerResults = new Map(newer.results.map((r) => [r.test_case_id, r]));
  const olderByIdentity = new Map(older.test_cases.map((tc) => [identityKey(tc), tc]));
  const newerByIdentity = new Map(newer.test_cases.map((tc) => [identityKey(tc), tc]));

  const rows: TestCaseComparison[] = [];
  for (const [key, oldTc] of olderByIdentity) {
    const newTc = newerByIdentity.get(key);
    const before = olderResults.get(oldTc.id) ?? null;
    if (!newTc) {
      rows.push({
        key,
        skillId: oldTc.skill_id,
        skillName: skillName(older, oldTc.skill_id),
        input: inputText(oldTc),
        before,
        after: null,
        change: "removed",
        criteriaChanged: false,
      });
      continue;
    }
    const after = newerResults.get(newTc.id) ?? null;
    rows.push({
      key,
      skillId: oldTc.skill_id,
      skillName: skillName(newer, newTc.skill_id),
      input: inputText(newTc),
      before,
      after,
      change: before && after ? classify(before, after) : "unchanged",
      criteriaChanged: contentKey(oldTc) !== contentKey(newTc),
    });
  }
  for (const [key, newTc] of newerByIdentity) {
    if (olderByIdentity.has(key)) continue;
    rows.push({
      key,
      skillId: newTc.skill_id,
      skillName: skillName(newer, newTc.skill_id),
      input: inputText(newTc),
      before: null,
      after: newerResults.get(newTc.id) ?? null,
      change: "added",
      criteriaChanged: false,
    });
  }

  const olderNotTested = new Set(older.not_tested.map((i) => `${i.category}: ${i.detail}`));
  const newerNotTested = new Set(newer.not_tested.map((i) => `${i.category}: ${i.detail}`));
  const summary = { regressed: 0, improved: 0, unchanged: 0, mixed: 0, no_runs: 0, added: 0, removed: 0 };
  for (const row of rows) summary[row.change] += 1;

  const olderDecision = older.decisions[0]?.outcome ?? null;
  const newerDecision = newer.decisions[0]?.outcome ?? null;

  return {
    older,
    newer,
    sameAgent: older.agent.id === newer.agent.id,
    cardHashChanged: older.card_version.card_hash !== newer.card_version.card_hash,
    contractChanged: older.contract.id !== newer.contract.id,
    statusChanged: older.attestation.status !== newer.attestation.status,
    decisionChanged: olderDecision !== newerDecision,
    testCases: rows,
    notTestedAdded: [...newerNotTested].filter((x) => !olderNotTested.has(x)),
    notTestedRemoved: [...olderNotTested].filter((x) => !newerNotTested.has(x)),
    summary,
  };
}
