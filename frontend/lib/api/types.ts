/**
 * Shapes of the hosted API (src/suncly/adapters/api/app.py, docs/API.md). Field names are the
 * backend's. Where a shape is open-ended on the server (progress, policy evaluation) it is an
 * index signature here; the pages read only the keys the backend documents.
 */

import type { Attestation, Contract, DecisionOutcome, ResultDocument, RiskLevel, TestCase } from "@/lib/evidence/types";

export type Role = "administrator" | "reviewer" | "viewer";

export interface ApiErrorBody {
  code: string;
  message: string;
  detail: string;
  next_step: string;
  request_id: string | null;
}

export interface Principal {
  subject: string;
  issuer: string;
  email: string | null;
  display_name: string | null;
  verified_by: string;
}

export interface Organization {
  id: string;
  slug: string;
  name: string;
  created_at: string;
  max_concurrent_jobs: number;
  role: Role | null;
}

export interface Me {
  principal: Principal;
  organizations: Organization[];
}

export interface Membership {
  id: string;
  organization_id: string;
  subject: string;
  email: string | null;
  role: Role;
  created_at: string;
}

export interface CredentialReference {
  provider: "secret-manager" | "env" | "none";
  ref: string;
}

export interface Registration {
  id: string;
  organization_id: string;
  agent_id: string;
  name: string;
  card_url: string;
  risk_level: RiskLevel;
  owner: string;
  sandbox_declared: boolean;
  sandbox_idempotent: boolean;
  credential: CredentialReference;
  deployment_mode: "public" | "private_network" | "local";
  bring_your_own_model_key: boolean;
  created_at: string;
  created_by: string;
  archived_at: string | null;
}

export interface RegisterAgentBody {
  name: string;
  card_url: string;
  risk_level: RiskLevel;
  owner: string;
  sandbox_declared: boolean;
  sandbox_idempotent: boolean;
  credential: CredentialReference;
  bring_your_own_model_key: boolean;
}

export interface ContractDetail {
  contract: Contract;
  content_hash: string;
  source: string;
  card_version: { id: string; card_hash: string; fetched_at: string };
  card: Record<string, unknown>;
  registration_id: string;
  test_cases: TestCase[];
  not_testable: Array<{ skill_id: string; reason: string }>;
  uncovered_skills: string[];
  suite: Record<string, unknown> | null;
}

export interface JobSummary {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "cancelled";
  attempts: number;
  max_attempts: number;
  cancel_requested: boolean;
  last_error: string | null;
  run_after: string;
  finished_at: string | null;
}

export interface AttestationMeta {
  attestation_id: string;
  organization_id: string;
  registration_id: string;
  created_by: string;
  runs_planned: number;
  runs_per_test_case: number;
  suite_version: string;
  contract_content_hash: string;
  judge_version: string;
  policy_version: string | null;
  policy_content_hash: string | null;
  issued_at: string | null;
  expires_at: string | null;
  payload_version: number | null;
  decided_by_reviewer: string | null;
  [key: string]: unknown;
}

export interface AttestationItem {
  attestation: Attestation;
  registration_id: string;
  contract: { id: string; version: number; content_hash: string };
  meta: AttestationMeta;
  job: JobSummary | null;
  progress: Record<string, unknown>;
}

export interface StartAttestationBody {
  registration_id: string;
  contract_id: string;
  runs: number;
  budget_limit?: string;
  trigger: "ci" | "manual";
  external_tools: Array<"a2a-tck" | "promptfoo">;
}

export interface Evidence {
  result: ResultDocument & { external_results?: Array<Record<string, unknown>>; decision_notes?: Array<Record<string, unknown>> };
  transcripts: Record<string, string>;
  summary: { decision_line: string; decision_detail: string; not_tested: string[][] };
}

export interface VerificationLayer {
  ok: boolean;
  checks: Array<{ name: string; ok: boolean; detail: string }>;
}

export interface Verification {
  accepted: boolean;
  cryptographic: VerificationLayer;
  issuer_trust: VerificationLayer;
  freshness: VerificationLayer;
  policy: VerificationLayer;
  [key: string]: unknown;
}

export interface DecisionResult {
  decision: { id: string; outcome: DecisionOutcome; policy_version: string; decided_by: string; decided_at: string };
  note: { decision_id: string; reviewer_subject: string; rationale: string; created_at: string };
}

export interface PolicyRecord {
  id: string;
  organization_id: string;
  policy_version: string;
  content_hash: string;
  configuration: Record<string, unknown>;
  created_at: string;
  created_by: string;
}

export interface Entitlement {
  organization_id: string;
  can_start_attestations: boolean;
  reason: string;
  subscription_status: string;
  plan_id: string | null;
  currency: string | null;
  included_allowance_minor: number;
  allowance_used_minor: number;
  settled_minor: number;
  reserved_minor: number;
  unknown_minor_held: number;
  period_limit_minor: number | null;
}

export interface UsageEvent {
  id: string;
  attestation_id: string | null;
  operation: string;
  outcome: string;
  billable_minor: number;
  allowance_minor: number;
  settlement: string;
  recorded_at: string;
  note: string;
  [key: string]: unknown;
}

export interface Reservation {
  id: string;
  attestation_id: string | null;
  amount_minor: number;
  currency: string;
  state: "held" | "settled" | "released";
  created_at: string;
  note: string;
  [key: string]: unknown;
}

export interface Usage {
  entitlement: Entitlement;
  events: UsageEvent[];
  reservations: Reservation[];
}

export interface Plan {
  id: string;
  name: string;
  included_allowance_minor: number;
  [key: string]: unknown;
}

export interface Plans {
  catalog_version: string;
  price_table_version: string;
  plans: Plan[];
  note: string;
}

export interface Subscription {
  subscription: Record<string, unknown> | null;
  entitlement: Entitlement;
}

export interface TrustedKeys {
  issuer: string;
  keys: Array<{ key_id: string; issuer: string; public_key: string; created_at: string; revoked_at: string | null; revocation_reason: string | null }>;
}
