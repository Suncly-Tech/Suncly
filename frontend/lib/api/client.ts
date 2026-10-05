/**
 * A small typed client for the hosted API. Every call sends the bearer token the reviewer
 * saved in Settings and surfaces the backend's error envelope as an `ApiError`, so pages
 * can show the message, the next step and the request id instead of a generic failure.
 */

import type {
  ApiErrorBody,
  AttestationItem,
  ContractDetail,
  DecisionResult,
  Evidence,
  Me,
  Membership,
  Organization,
  Plans,
  PolicyRecord,
  RegisterAgentBody,
  Registration,
  StartAttestationBody,
  Subscription,
  TrustedKeys,
  Usage,
  Verification,
} from "./types";
import type { DecisionOutcome } from "@/lib/evidence/types";

export class ApiError extends Error {
  status: number;
  body: ApiErrorBody | null;

  constructor(status: number, body: ApiErrorBody | null, fallback: string) {
    super(body?.message ?? fallback);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }

  get code(): string {
    return this.body?.code ?? (this.status === 0 ? "unreachable" : `http_${this.status}`);
  }

  get requestId(): string | null {
    return this.body?.request_id ?? null;
  }

  get nextStep(): string {
    return this.body?.next_step ?? "";
  }

  /** The caller is signed in but their role does not allow this action. */
  get forbidden(): boolean {
    return this.status === 403;
  }

  /** The token is missing, expired or not accepted. */
  get unauthenticated(): boolean {
    return this.status === 401;
  }
}

export interface ConnectionConfig {
  baseUrl: string;
  token: string;
}

async function parseError(response: Response): Promise<ApiErrorBody | null> {
  try {
    const body = (await response.json()) as { error?: ApiErrorBody };
    return body.error ?? null;
  } catch {
    return null;
  }
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly token: string;

  constructor(config: ConnectionConfig) {
    this.baseUrl = config.baseUrl.replace(/\/+$/, "");
    this.token = config.token.trim();
  }

  private async request<T>(method: string, path: string, body?: unknown): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (this.token) headers.Authorization = `Bearer ${this.token}`;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        mode: "cors",
      });
    } catch (error) {
      throw new ApiError(0, null, `The API at ${this.baseUrl} could not be reached (${(error as Error).message}).`);
    }
    if (!response.ok) {
      throw new ApiError(response.status, await parseError(response), `The API answered ${response.status}.`);
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  health(): Promise<{ status: string; version: string }> {
    return this.request("GET", "/v1/health");
  }

  me(): Promise<Me> {
    return this.request("GET", "/v1/me");
  }

  keys(): Promise<TrustedKeys> {
    return this.request("GET", "/v1/keys");
  }

  createOrganization(slug: string, name: string): Promise<Organization> {
    return this.request("POST", "/v1/organizations", { slug, name });
  }

  members(org: string): Promise<{ members: Membership[] }> {
    return this.request("GET", `/v1/organizations/${org}/members`);
  }

  addMember(org: string, subject: string, role: string, email?: string): Promise<Membership> {
    return this.request("POST", `/v1/organizations/${org}/members`, { subject, role, email: email || null });
  }

  agents(org: string): Promise<{ agents: Registration[] }> {
    return this.request("GET", `/v1/organizations/${org}/agents`);
  }

  agent(org: string, registrationId: string): Promise<Registration> {
    return this.request("GET", `/v1/organizations/${org}/agents/${registrationId}`);
  }

  registerAgent(org: string, body: RegisterAgentBody): Promise<Registration> {
    return this.request("POST", `/v1/organizations/${org}/agents`, body);
  }

  archiveAgent(org: string, registrationId: string): Promise<Registration> {
    return this.request("DELETE", `/v1/organizations/${org}/agents/${registrationId}`);
  }

  contracts(org: string, registrationId: string): Promise<{ contracts: ContractDetail["contract"][] }> {
    return this.request("GET", `/v1/organizations/${org}/agents/${registrationId}/contracts`);
  }

  contract(org: string, contractId: string): Promise<ContractDetail> {
    return this.request("GET", `/v1/organizations/${org}/contracts/${contractId}`);
  }

  draftContract(org: string, registrationId: string, source: "deterministic" | "model"): Promise<ContractDetail> {
    return this.request("POST", `/v1/organizations/${org}/agents/${registrationId}/contracts/draft`, { source });
  }

  approveContract(org: string, contractId: string): Promise<ContractDetail> {
    return this.request("POST", `/v1/organizations/${org}/contracts/${contractId}/approve`);
  }

  rejectContract(org: string, contractId: string): Promise<ContractDetail> {
    return this.request("POST", `/v1/organizations/${org}/contracts/${contractId}/reject`);
  }

  attestations(org: string, registrationId?: string): Promise<{ attestations: AttestationItem[] }> {
    const query = registrationId ? `?registration_id=${encodeURIComponent(registrationId)}` : "";
    return this.request("GET", `/v1/organizations/${org}/attestations${query}`);
  }

  attestation(org: string, attestationId: string): Promise<AttestationItem> {
    return this.request("GET", `/v1/organizations/${org}/attestations/${attestationId}`);
  }

  startAttestation(org: string, body: StartAttestationBody): Promise<AttestationItem> {
    return this.request("POST", `/v1/organizations/${org}/attestations`, body);
  }

  cancelAttestation(org: string, attestationId: string): Promise<AttestationItem> {
    return this.request("POST", `/v1/organizations/${org}/attestations/${attestationId}/cancel`);
  }

  evidence(org: string, attestationId: string): Promise<Evidence> {
    return this.request("GET", `/v1/organizations/${org}/attestations/${attestationId}/evidence`);
  }

  verification(org: string, attestationId: string): Promise<Verification> {
    return this.request("GET", `/v1/organizations/${org}/attestations/${attestationId}/verification`);
  }

  resolve(org: string, attestationId: string, outcome: DecisionOutcome, rationale: string): Promise<DecisionResult> {
    return this.request("POST", `/v1/organizations/${org}/attestations/${attestationId}/decisions`, { outcome, rationale });
  }

  policies(org: string): Promise<{ policies: PolicyRecord[] }> {
    return this.request("GET", `/v1/organizations/${org}/policies`);
  }

  createPolicy(org: string, configuration: Record<string, unknown>): Promise<PolicyRecord> {
    return this.request("POST", `/v1/organizations/${org}/policies`, { configuration });
  }

  usage(org: string): Promise<Usage> {
    return this.request("GET", `/v1/organizations/${org}/usage`);
  }

  setSpendingLimit(org: string, periodLimitMinor: number): Promise<Record<string, unknown>> {
    return this.request("PUT", `/v1/organizations/${org}/spending-limit`, { period_limit_minor: periodLimitMinor });
  }

  plans(): Promise<Plans> {
    return this.request("GET", "/v1/billing/plans");
  }

  subscription(org: string): Promise<Subscription> {
    return this.request("GET", `/v1/organizations/${org}/subscription`);
  }

  checkout(org: string, planId: string): Promise<{ id: string; url: string }> {
    return this.request("POST", `/v1/organizations/${org}/billing/checkout`, { plan_id: planId });
  }

  portal(org: string): Promise<{ url: string }> {
    return this.request("POST", `/v1/organizations/${org}/billing/portal`);
  }
}
