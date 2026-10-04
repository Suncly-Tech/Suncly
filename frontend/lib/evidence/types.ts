/**
 * The shape of `result.json` as written by `suncly attest` (adapters/report/writer.py,
 * format "suncly-result/1"), and of the transcript files next to it. Field names are
 * the data model's (docs/DATA_MODEL.md). Nothing here is invented: every field maps to
 * a Python model in src/suncly/domain or src/suncly/core.
 */

export type RiskLevel = "low" | "medium" | "high";
export type ContractStatus = "draft" | "approved" | "rejected" | "superseded";
export type TestCaseKind = "skill" | "probe_undeclared" | "probe_injection" | "probe_failure";
export type AttestationTrigger = "ci" | "schedule" | "card_change" | "manual";
export type AttestationStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "invalidated";
export type RunVerdict = "pass" | "fail" | "inconclusive";
export type JudgeLayer = "deterministic" | "model";
export type DecisionOutcome = "approve" | "flag" | "block";
export type RunOutcome =
  | "responded_task"
  | "responded_message"
  | "unreachable"
  | "timeout"
  | "protocol_error";
export type NotExecutedReason = "budget" | "runner_crashed" | "withheld";
export type CardRecheckOutcome = "unchanged" | "changed" | "unavailable" | "not_performed";

export interface Agent {
  id: string;
  name: string;
  owner: string;
  risk_level: RiskLevel;
}

export interface CardVersion {
  id: string;
  agent_id: string;
  card_hash: string;
  raw_json: string;
  fetched_at: string;
}

export interface AgentInterface {
  url: string;
  protocol_binding: string;
  protocol_version: string;
  tenant: string | null;
}

export interface AgentCapabilities {
  streaming: boolean | null;
  push_notifications: boolean | null;
  extended_agent_card: boolean | null;
  extensions: unknown[] | null;
}

export interface AgentSkill {
  id: string;
  name: string;
  description: string;
  tags: string[];
  examples: string[] | null;
  input_modes: string[] | null;
  output_modes: string[] | null;
  security_requirements: unknown[] | null;
}

export interface AgentCard {
  name: string;
  description: string;
  version: string;
  supported_interfaces: AgentInterface[];
  capabilities: AgentCapabilities;
  default_input_modes: string[];
  default_output_modes: string[];
  skills: AgentSkill[];
}

export interface ParsedCard {
  raw_json: string;
  json_object: Record<string, unknown>;
  card: AgentCard;
  card_hash: string;
}

export interface Contract {
  id: string;
  card_version_id: string;
  version: number;
  status: ContractStatus;
  created_at: string;
  approved_by: string | null;
  approved_at: string | null;
}

/** `test_case.criteria` as proposed for OQ-D7 (domain/criteria.py). */
export interface Criteria {
  final_state: string;
  latency_limit_ms: number;
  response_present: boolean;
  output_modes: string[] | null;
  required_fields: string[];
  response_schema?: Record<string, unknown> | null;
  model_checks: string[];
  accept_direct_message: boolean;
}

export interface TestCase {
  id: string;
  contract_id: string;
  skill_id: string | null;
  input: { text?: string; parts?: unknown[] };
  criteria: Criteria;
  kind: TestCaseKind;
}

export interface Attestation {
  id: string;
  contract_id: string;
  card_version_id: string;
  trigger: AttestationTrigger;
  status: AttestationStatus;
  started_at: string;
  finished_at: string | null;
  budget_limit: string;
  cost_total: string;
  signature: string | null;
  signing_key_id: string | null;
}

export interface Run {
  id: string;
  attestation_id: string;
  test_case_id: string;
  attempt: number;
  verdict: RunVerdict;
  judge_layer: JudgeLayer;
  rationale: string | null;
  latency_ms: number | null;
  cost: string;
  transcript_ref: string;
  started_at: string;
  finished_at: string;
}

export interface RunEvidenceRef {
  run: Run;
  /** SHA-256 hex of the evidence document file, as the signature payload carries it. */
  document_hash: string;
}

export interface Decision {
  id: string;
  attestation_id: string;
  outcome: DecisionOutcome;
  policy_version: string;
  decided_by: string;
  decided_at: string;
}

export interface TestCaseResult {
  test_case_id: string;
  skill_id: string | null;
  kind: TestCaseKind;
  pass_count: number;
  fail_count: number;
  inconclusive_count: number;
}

export interface NotExecutedRun {
  test_case_id: string;
  attempt: number;
  reason: NotExecutedReason;
  detail: string;
}

export interface CardRecheck {
  outcome: CardRecheckOutcome;
  card_hash: string | null;
  detail: string;
}

export interface NotTestedItem {
  category: string;
  detail: string;
}

export interface SignaturePayload {
  attestation_id: string;
  card_hash: string;
  contract: { id: string; version: number };
  results: Array<{
    test_case_id: string;
    skill_id: string | null;
    kind: TestCaseKind;
    pass: number;
    fail: number;
    inconclusive: number;
  }>;
  transcript_hashes: Record<string, string>;
  decision: { outcome: DecisionOutcome; policy_version: string } | null;
  [key: string]: unknown;
}

/** `result.json`. */
export interface ResultDocument {
  format: "suncly-result/1";
  generated_at: string;
  agent: Agent;
  card_version: CardVersion;
  parsed_card: ParsedCard;
  card_url: string | null;
  contract: Contract;
  test_cases: TestCase[];
  attestation: Attestation;
  runs: RunEvidenceRef[];
  decisions: Decision[];
  results: TestCaseResult[];
  planned_runs: number | null;
  not_executed: NotExecutedRun[];
  card_recheck: CardRecheck;
  not_tested: NotTestedItem[];
  sandbox_declared: boolean;
  drafter_name: string | null;
  signer_public_key: string | null;
  signature_payload: SignaturePayload | null;
  proposals: string[];
}

/** One Layer 1 check inside an evidence document (core/judge.py: CheckResult). */
export interface CheckResult {
  name: string;
  /** `null` means Layer 1 could not decide it. */
  passed: boolean | null;
  detail: string;
}

export interface Judgement {
  verdict: RunVerdict;
  judge_layer: JudgeLayer;
  summary: string;
  checks: CheckResult[];
}

export interface Exchange {
  direction: "request" | "response";
  at: string;
  method: string | null;
  url: string;
  http_status: number | null;
  headers: Record<string, string>;
  body: unknown;
}

export interface Transcript {
  attestation_id: string;
  test_case_id: string;
  attempt: number;
  target_url: string;
  protocol_binding: string;
  protocol_version: string;
  started_at: string;
  finished_at: string;
  latency_ms: number | null;
  cost: string;
  outcome: RunOutcome;
  task_id: string | null;
  final_task_state: string | null;
  final_response: Record<string, unknown> | null;
  exchanges: Exchange[];
  failure: string | null;
  redaction: { replacements: number; rules: string[] };
}

/** `transcripts/<run-id>.json`: the stored evidence document (transcript plus judgement). */
export interface EvidenceDocument {
  transcript: Transcript;
  judgement: Judgement;
}

/**
 * What the workspace stores for one attestation: result.json plus the transcript
 * files' exact text, keyed by run id. Text is kept byte for byte so hashes can be
 * recomputed the way `suncly verify` does.
 */
export interface EvidenceBundle {
  result: ResultDocument;
  transcripts: Record<string, string>;
}
