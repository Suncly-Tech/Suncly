/**
 * The capability map: what Suncly does today, with limits, and what is planned.
 *
 * One source for the website and the workspace. Every "available" entry names the code
 * and the test that prove it; every "planned" entry names the roadmap stage. Edit this
 * file when the implementation changes, then the pages follow.
 *
 * Status meanings:
 *  - available: implemented in src/suncly and covered by tests.
 *  - limited:   implemented, with a limitation a buyer must know about.
 *  - planned:   not implemented. Named in docs/ROADMAP.md; no date is promised.
 */

export type Availability = "available" | "limited" | "planned";

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  available: "Available",
  limited: "Available with limits",
  planned: "Planned",
};

export interface Capability {
  id: string;
  name: string;
  status: Availability;
  /** What it does, in a sentence. */
  summary: string;
  /** Why a buyer cares. */
  benefit: string;
  /** The limitation (for limited) or what is missing (for planned). */
  limit?: string;
  /** Where it lives in the repository. */
  evidence: string;
  group: "evaluation" | "evidence" | "approval" | "operations" | "integration";
}

export const capabilities: Capability[] = [
  {
    id: "card-read",
    name: "Reads the A2A Agent Card and hashes it",
    status: "available",
    summary:
      "Fetches the card over https, keeps it byte for byte, and computes card_hash as SHA-256 of its RFC 8785 form without the signatures field.",
    benefit: "Every evaluation is pinned to an exact version of what the agent claimed.",
    evidence: "src/suncly/domain/card.py, core/cards.py; tests/unit/test_card.py",
    group: "evaluation",
  },
  {
    id: "drafting",
    name: "Tests derived from declared skills",
    status: "limited",
    summary:
      "One test case per declared example of each skill, up to a cap. Criteria: completes, answers, uses the declared output modes, within a latency limit.",
    benefit: "Nobody writes the first test plan by hand, and every declared skill with an example is covered.",
    limit:
      "The CLI drafts deterministically. The hosted API can also let the configured model draft a behavioural suite (reference examples, assertions, rubrics, negative cases, acknowledged gaps); a human approves it before anything runs. A skill without examples and no suite case is listed as not tested.",
    evidence: "src/suncly/core/contract_builder.py, core/model_drafter.py, domain/behavioral.py; tests/unit/test_behavioral_and_drafter.py",
    group: "evaluation",
  },
  {
    id: "human-approval",
    name: "Human review of the test plan",
    status: "available",
    summary:
      "Nothing runs until a person approves the drafted contract and their identifier is recorded as approved_by. Approved contracts are immutable; an edit is a new version.",
    benefit: "The test plan is a reviewed artefact with a name on it, not a side effect of a run.",
    evidence: "src/suncly/core/contract_builder.py (ContractService.approve); tests/unit/test_non_negotiable_rules.py",
    group: "approval",
  },
  {
    id: "custom-criteria",
    name: "Customer-defined criteria and known-answer checks",
    status: "limited",
    summary:
      "Export the draft, edit the contract file, run with it: expected final state, required fields (JSON pointers), a JSON Schema for the response, latency limit, declared output modes.",
    benefit: "Your acceptance criteria become repeatable checks instead of a reviewer's memory.",
    limit:
      "Format-2 criteria add deterministic assertions, rubrics and negative cases. A rubric is judged by the configured model (Layer 2); without a model provider, or when the model fails, the run is inconclusive and says so.",
    evidence: "src/suncly/domain/criteria.py, domain/contract_file.py, core/model_judge.py; tests/unit/test_judge_v2.py",
    group: "evaluation",
  },
  {
    id: "repeated-runs",
    name: "Repeated runs that expose inconsistent behaviour",
    status: "available",
    summary:
      "Each test case runs N times (default 5) from a separate Runner process, with a deterministic run key per attempt so retries never double count.",
    benefit: "An agent that works four times out of five shows up as four passes and one fail, not as a pass.",
    evidence: "src/suncly/core/orchestrator.py; tests/e2e/test_mock_agents.py (flaky agent)",
    group: "evaluation",
  },
  {
    id: "deterministic-judge",
    name: "Deterministic verdicts: pass, fail, inconclusive",
    status: "limited",
    summary:
      "Layer 1 checks the response is a well-formed A2A Task or Message, reached the expected final state, answered within the latency limit, carries content, uses the declared output modes, and satisfies required fields and schema.",
    benefit: "Verdicts are reproducible and explained check by check. Inconclusive is a third outcome, never counted as a pass.",
    limit:
      "Layer 2 (a pinned model behind a port, structured output, identity and usage recorded on the run) exists for rubric criteria and runs in the hosted worker when a provider is configured. The CLI and CI run without a model; a model-judged criterion is then inconclusive. Calibration against a human-labelled dataset is measured, never asserted for the real provider.",
    evidence: "src/suncly/core/judge.py, core/model_judge.py, core/model_calibration.py; tests/unit/test_judge_calibration.py",
    group: "evaluation",
  },
  {
    id: "probes",
    name: "Prompt-injection, undeclared-behaviour and failure-handling probes",
    status: "planned",
    summary: "Test cases of kind probe_injection, probe_undeclared and probe_failure, drafted alongside skill tests and approved the same way.",
    benefit: "Would show how the agent behaves outside what its card declares.",
    limit: "Not drafted automatically. A behavioural suite can carry negative security cases (category security, negative: true) that the judge evaluates; the probe kinds of the data model are not yet produced by any drafter, and every report says so.",
    evidence: "docs/ROADMAP.md stage 4; src/suncly/core/coverage.py lists the gap",
    group: "evaluation",
  },
  {
    id: "sandbox-only",
    name: "Sandbox or dry-run endpoints only",
    status: "limited",
    summary: "Nothing runs unless the caller declares the endpoint a sandbox with --sandbox. The Runner refuses undeclared targets a second time.",
    benefit: "Tests cannot book, pay or delete anything real.",
    limit: "Suncly cannot verify that an endpoint is a sandbox. The flag is your declaration, and the report records it as such.",
    evidence: "src/suncly/core/attestation.py, runner/process.py; tests/e2e/test_cli.py",
    group: "operations",
  },
  {
    id: "credentials",
    name: "Credentials held only by the Runner, redacted from evidence",
    status: "available",
    summary:
      "The agent's Authorization value comes from one environment variable, read only inside the Runner process. Transcripts are redacted before they leave it: the credential, sensitive headers, known token patterns.",
    benefit: "A reviewer can read every transcript without seeing a secret, and the component that holds secrets is small enough to audit.",
    evidence: "src/suncly/runner/credentials.py, runner/redaction.py; tests/unit/test_architecture.py::test_only_the_runner_reads_the_credential",
    group: "operations",
  },
  {
    id: "budget",
    name: "Budget and execution controls",
    status: "available",
    summary:
      "A budget in attempts per attestation (default twice the planned runs), a per-run timeout, retries under the same run key, and a concurrency limit. When the budget is reached the attestation ends failed and the report lists every run never executed.",
    benefit: "No runaway cost, and no silent partial result dressed up as a complete one.",
    evidence: "src/suncly/core/orchestrator.py (_Budget); tests/e2e/test_mock_agents.py::test_budget_stop_ends_failed_and_reports_runs_never_executed",
    group: "operations",
  },
  {
    id: "signed-evidence",
    name: "Signed, verifiable evidence",
    status: "available",
    summary:
      "Every attestation is signed with the deployment's Ed25519 key over the card hash, contract version, per-test-case counts, the hash of every transcript and the decision. suncly verify re-checks a report folder offline.",
    benefit: "Evidence can be handed to an auditor and checked without trusting the person who handed it over.",
    evidence: "src/suncly/core/signing.py, core/verify.py; tests/unit/test_signing_policy_verify.py",
    group: "evidence",
  },
  {
    id: "not-tested",
    name: "Explicit inconclusive outcomes and coverage gaps",
    status: "available",
    summary:
      "Every report has a 'What was NOT tested' section: skills without a test case, runs never executed, inconclusive runs, declared capabilities not exercised, interfaces not used, probes and semantic checks that do not exist yet, and the production endpoint.",
    benefit: "An approval on partial evidence is visible as such.",
    evidence: "src/suncly/core/coverage.py; tests/unit/test_non_negotiable_rules.py::test_dr_007_reports_state_what_was_not_tested",
    group: "evidence",
  },
  {
    id: "reports",
    name: "Exportable evaluation reports",
    status: "available",
    summary:
      "One folder per attestation: result.json (the evidence bundle and signed payload), the redacted transcripts, report.md and a self-contained report.html that opens offline.",
    benefit: "Results travel as files you can attach to a ticket, archive, or load into this workspace.",
    evidence: "src/suncly/adapters/report/; tests/unit/test_adapters.py::test_report_folder_is_self_contained_and_offline",
    group: "evidence",
  },
  {
    id: "storage",
    name: "Append-only evidence store, file or Postgres",
    status: "limited",
    summary:
      "Runs and decisions are append-only; the database rejects updates and deletes. The same store interface runs on local files or Postgres (set DATABASE_URL and run suncly db migrate).",
    benefit: "Evidence cannot be quietly edited after the fact.",
    limit: "The CLI keeps transcripts on local disk. The hosted worker can write them to a Cloud Storage bucket (SUNCLY_EVIDENCE_BUCKET); that adapter is tested against an in-memory bucket, not a live one.",
    evidence: "src/suncly/adapters/file_store.py, adapters/postgres/, adapters/gcs_transcripts.py; tests/stores/, tests/db/",
    group: "evidence",
  },
  {
    id: "policy",
    name: "Automatic approval decisions",
    status: "available",
    summary:
      "A versioned policy per organization sets thresholds per risk level, required categories, how inconclusive runs count, regression and freshness rules. The engine records one signed decision per completed attestation: approve, flag or block. Without a policy the only outcome is flag.",
    benefit: "Every completed evaluation ends with an explicit, signed decision under numbers the customer chose, and a human in the loop wherever the policy or the risk level says so.",
    limit: "High-risk agents are never approved automatically; that setting cannot be turned off. No threshold is built into the code.",
    evidence: "src/suncly/domain/policy.py, core/policy_engine.py; tests/unit/test_policy.py",
    group: "approval",
  },
  {
    id: "human-decision",
    name: "Recording the reviewer's decision in the evidence store",
    status: "available",
    summary: "On a hosted attestation, a reviewer resolves a flag with approve or block and a rationale; a second decision is recorded under the verified identity with an append-only note. The first decision is never edited.",
    benefit: "The loop closes inside Suncly, with a name on the decision.",
    limit: "For report folders loaded offline this workspace still keeps a local note outside the signed evidence, clearly marked as such.",
    evidence: "src/suncly/core/resolution.py, adapters/api/app.py; tests/unit/test_api_workflow.py",
    group: "approval",
  },
  {
    id: "comparison",
    name: "Regression comparisons between evaluations",
    status: "limited",
    summary:
      "The same card hash reuses its approved contract, so two attestations of the same agent run the same tests and can be compared test case by test case.",
    benefit: "You see what changed since the last evaluation, with the test conditions held constant.",
    limit:
      "Offline, the comparison is computed in this workspace from two signed bundles. Hosted, the policy's regression rule compares each attestation with the previous completed one of the same registration and flags a drop above the customer's threshold; scheduled re-evaluations use the same rule.",
    evidence: "frontend/lib/evidence/compare.ts; src/suncly/core/worker.py (_baseline), domain/policy.py (RegressionRule); tests/unit/test_worker_and_jobs.py",
    group: "evidence",
  },
  {
    id: "cli",
    name: "Command-line interface",
    status: "available",
    summary: "suncly attest, demo, verify, gate, keys init, db migrate, db check, doctor, plus the hosted commands api, worker, auth, trust and judge calibrate. Documented exit codes; --json for scripts.",
    benefit: "Runs anywhere Python 3.12 runs, including inside your network, with no data leaving it.",
    evidence: "src/suncly/cli/; docs/API.md",
    group: "integration",
  },
  {
    id: "api",
    name: "HTTP API",
    status: "limited",
    summary:
      "A hosted API with organizations and roles (administrator, reviewer, viewer), OpenID Connect tokens, one error envelope and an OpenAPI document: register sandbox agents, draft and approve contracts, start attestations within a spending limit, follow progress, read evidence and the four verification layers, resolve flags. A durable worker runs the jobs.",
    benefit: "This workspace's hosted pages start runs and read evidence directly, with a name on every approval.",
    limit: "Implemented and tested against local fakes and Postgres; the Cloud Run deployment is configured and validated but not yet deployed. Access to a hosted deployment is arranged with the team.",
    evidence: "src/suncly/adapters/api/, core/jobs.py, core/worker.py; tests/unit/test_api_workflow.py, tests/unit/test_worker_and_jobs.py; deploy/",
    group: "integration",
  },
  {
    id: "ci",
    name: "CI gate",
    status: "available",
    summary:
      "suncly gate answers three questions separately (did it complete, does it verify against trusted keys and freshness, does the policy approve) and exits 0 only when all three are yes. suncly attest keeps its exit codes: 0 there means completed and signed, never approved.",
    benefit: "A pipeline gates on an approval, not on a signature or on a run having finished.",
    evidence: "src/suncly/core/ci_gate.py, cli/hosted.py; tests/unit/test_integrity.py",
    group: "integration",
  },
  {
    id: "tenancy",
    name: "Organizations, roles and verified identities",
    status: "available",
    summary:
      "Every hosted request is checked against the caller's membership in the organization of the URL; a body never names an organization or a reviewer. Non-members see not found. Identities come from your OpenID Connect provider; Suncly runs no identity system.",
    benefit: "Approvals, contracts and decisions carry verified names, and one tenant cannot read another's evidence.",
    evidence: "src/suncly/core/authz.py, adapters/auth.py; tests/unit/test_auth_and_authz.py, tests/unit/test_api_workflow.py",
    group: "operations",
  },
  {
    id: "jobs",
    name: "Durable jobs that resume without double counting",
    status: "available",
    summary:
      "Attestations run as Postgres-backed jobs with leases, heartbeats, persisted progress, bounded retries and cancellation. A worker that dies is recovered; the next one resumes from the recorded runs and bills nothing twice. A run whose outcome is unknown is reported as unknown, never as a pass.",
    benefit: "A crash mid-evaluation costs a retry, not a duplicated or silently missing result.",
    limit: "At least once, not exactly once: Suncly says so, and keeps the money for an unknown outcome held until a person reconciles it.",
    evidence: "src/suncly/core/jobs.py, core/worker.py; tests/unit/test_worker_and_jobs.py, tests/stores/test_app_store_contract.py",
    group: "operations",
  },
  {
    id: "egress",
    name: "Runner egress controls",
    status: "available",
    summary:
      "In public mode the Runner connects only to public https hosts on 443 or 8443, checks every resolved address at connection time and on every redirect, and refuses loopback, private, link-local and cloud metadata ranges. A private-network deployment is a separate, authorized deployment, never a per-agent option.",
    benefit: "A customer-named URL cannot turn the Runner into a probe of Suncly's own network.",
    evidence: "src/suncly/domain/network.py, runner/http_transport.py; tests/unit/test_network_guard.py; deploy/terraform (egress firewall)",
    group: "operations",
  },
  {
    id: "external-tools",
    name: "A2A TCK and Promptfoo packs as additional evidence",
    status: "limited",
    summary:
      "The A2A protocol TCK (pinned) and an approved Promptfoo pack (pinned) can run after the contract's tests. Their checks are normalized into protocol, semantic, security and operational results and their output files are kept and bound into the signature.",
    benefit: "Protocol conformance and your own test pack sit next to Suncly's evidence, under the same signature.",
    limit: "The tools run only where the worker image installs them; a failed or undecided external check can flag, never approve.",
    evidence: "src/suncly/adapters/external/; tests/unit/test_external_adapters.py",
    group: "evaluation",
  },
  {
    id: "billing",
    name: "Usage ledger, spending limits and subscriptions",
    status: "limited",
    summary:
      "An append-only ledger in whole minor units records every Runner and judge call; a reservation under the organization's hard limit is taken before a job starts and settled when it ends. Plans carry an included allowance; overage is reported to the billing provider once per line; webhooks are verified and replay-safe.",
    benefit: "Spending is bounded before it happens and explained line by line afterwards.",
    limit: "The billing provider runs in test mode only; no live product or price exists.",
    evidence: "src/suncly/core/usage.py, core/billing.py, adapters/stripe_billing.py; tests/unit/test_usage_and_billing.py",
    group: "operations",
  },
  {
    id: "registry",
    name: "Registry integration",
    status: "planned",
    summary: "Adapters that write approval status into your agent registry.",
    benefit: "Would make approval visible where agents are discovered.",
    limit: "Stage 6. Target registries are not chosen (OQ-R5).",
    evidence: "src/suncly/adapters/registry.py (placeholder)",
    group: "integration",
  },
];

export const byGroup = (group: Capability["group"]) => capabilities.filter((c) => c.group === group);
export const byStatus = (status: Availability) => capabilities.filter((c) => c.status === status);
export const capability = (id: string) => capabilities.find((c) => c.id === id);
