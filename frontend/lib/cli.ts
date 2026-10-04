/**
 * Builds the exact `suncly` commands for an evaluation. The web workspace cannot start a
 * run: there is no HTTP API in this version (api.py is a stage 5 placeholder), and the
 * Runner must hold the credential in its own process. Options and defaults are those of
 * src/suncly/cli/main.py and docs/API.md.
 */

import type { RiskLevel } from "@/lib/evidence/types";

export interface AttestOptions {
  cardUrl: string;
  sandboxDeclared: boolean;
  runs: number | null;
  budget: number | null;
  approveAs: string;
  owner: string;
  riskLevel: RiskLevel | "";
  contractPath: string;
  reportsDir: string;
  needsCredential: boolean;
  json: boolean;
}

export const DEFAULTS = {
  runs: 5,
  budgetFactor: 2,
  latencyLimitMs: 10_000,
  runTimeoutS: 30,
  maxRetries: 2,
  concurrency: 4,
  maxTestCasesPerSkill: 3,
  reportsDir: "./suncly-reports",
} as const;

function quote(value: string): string {
  if (/^[A-Za-z0-9._:/@=+-]+$/.test(value)) return value;
  return `"${value.replace(/(["\\$`])/g, "\\$1")}"`;
}

export interface ValidationIssue {
  field: keyof AttestOptions;
  message: string;
}

export function validateAttest(options: AttestOptions): ValidationIssue[] {
  const issues: ValidationIssue[] = [];
  const url = options.cardUrl.trim();
  if (!url) {
    issues.push({ field: "cardUrl", message: "Enter the URL of the agent's Agent Card." });
  } else {
    try {
      const parsed = new URL(url);
      const loopback = ["127.0.0.1", "localhost", "[::1]", "::1"].includes(parsed.hostname);
      if (parsed.protocol !== "https:" && !(parsed.protocol === "http:" && loopback)) {
        issues.push({
          field: "cardUrl",
          message: "Suncly fetches cards over https only. Plain http is accepted for loopback addresses, where local sandboxes run.",
        });
      }
    } catch {
      issues.push({ field: "cardUrl", message: "This is not a valid URL." });
    }
  }
  if (!options.sandboxDeclared) {
    issues.push({
      field: "sandboxDeclared",
      message: "Nothing runs without the sandbox declaration (DR-006). Confirm that this endpoint is a sandbox or dry-run endpoint.",
    });
  }
  if (options.runs !== null && (!Number.isInteger(options.runs) || options.runs < 1)) {
    issues.push({ field: "runs", message: "Runs per test case must be a whole number of at least 1." });
  }
  if (options.budget !== null && (!Number.isFinite(options.budget) || options.budget < 0)) {
    issues.push({ field: "budget", message: "The budget is a number of attempts and cannot be negative." });
  }
  if (!options.approveAs.trim()) {
    issues.push({
      field: "approveAs",
      message: "Enter the identifier recorded as approved_by, or leave this blank to approve at the interactive prompt instead.",
    });
  }
  return issues;
}

export function plannedRuns(testCases: number, runs: number | null): number {
  return testCases * (runs ?? DEFAULTS.runs);
}

export function buildAttestCommand(options: AttestOptions): string {
  const parts = ["suncly", "attest", quote(options.cardUrl.trim() || "<card-url>")];
  if (options.sandboxDeclared) parts.push("--sandbox");
  if (options.runs !== null && options.runs !== DEFAULTS.runs) parts.push("--runs", String(options.runs));
  if (options.budget !== null) parts.push("--budget", String(options.budget));
  if (options.approveAs.trim()) parts.push("--approve-as", quote(options.approveAs.trim()));
  if (options.owner.trim()) parts.push("--owner", quote(options.owner.trim()));
  if (options.riskLevel) parts.push("--risk-level", options.riskLevel);
  if (options.contractPath.trim()) parts.push("--contract", quote(options.contractPath.trim()));
  if (options.reportsDir.trim() && options.reportsDir.trim() !== DEFAULTS.reportsDir) {
    parts.push("--reports-dir", quote(options.reportsDir.trim()));
  }
  if (options.json) parts.push("--json");
  return parts.join(" ");
}

export function buildExportDraftCommand(options: AttestOptions, file = "contract.json"): string {
  return `suncly attest ${quote(options.cardUrl.trim() || "<card-url>")} --sandbox --export-draft ${file}`;
}

export function credentialLines(shell: "posix" | "powershell"): string[] {
  return shell === "powershell"
    ? ['$env:SUNCLY_AGENT_AUTHORIZATION = "Bearer <token>"']
    : ['export SUNCLY_AGENT_AUTHORIZATION="Bearer <token>"'];
}

export function verifyCommand(reportDir: string): string {
  return `suncly verify ${quote(reportDir)}`;
}
