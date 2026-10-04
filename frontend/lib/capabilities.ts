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
      "Drafting is deterministic and uses no model. A skill without examples gets no test case and is listed as not tested. Model-drafted tests and probes are stage 2 and 4.",
    evidence: "src/suncly/core/contract_builder.py (DeterministicDrafter); tests/unit/test_contract_builder.py",
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
      "Checks are structural. A criterion about the meaning of an answer (model_checks) makes the run inconclusive until Judge Layer 2 exists (stage 4).",
    evidence: "src/suncly/domain/criteria.py, domain/contract_file.py; docs/API.md 'Contract file'",
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
    limit: "No model-based judgement yet. Whether an answer is correct in meaning is listed under what was not tested.",
    evidence: "src/suncly/core/judge.py; tests/unit/test_judge.py",
    group: "evaluation",
  },
  {
    id: "probes",
    name: "Prompt-injection, undeclared-behaviour and failure-handling probes",
    status: "planned",
    summary: "Test cases of kind probe_injection, probe_undeclared and probe_failure, drafted alongside skill tests and approved the same way.",
    benefit: "Would show how the agent behaves outside what its card declares.",
    limit: "Stage 4. The data model and the contract file format already carry the kinds; no probe is drafted or run today, and every report says so.",
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
    limit: "Transcripts stay on local disk until an object-storage adapter exists.",
    evidence: "src/suncly/adapters/file_store.py, adapters/postgres/; tests/stores/test_store_contract.py, tests/db/",
    group: "evidence",
  },
  {
    id: "policy",
    name: "Automatic approval decisions",
    status: "limited",
    summary:
      "The Policy engine records one decision per completed attestation and signs it. Today the only outcome it can produce is flag, because no policy configuration exists.",
    benefit: "Every completed evaluation ends with an explicit, signed decision record and a human in the loop.",
    limit:
      "approve and block are never produced automatically; thresholds per risk level are stage 5 and a customer configuration. Risk levels are recorded but do not yet change the outcome.",
    evidence: "src/suncly/core/policy_engine.py; tests/unit/test_architecture.py::test_no_code_path_constructs_an_approve_or_block_decision",
    group: "approval",
  },
  {
    id: "human-decision",
    name: "Recording the reviewer's decision in the evidence store",
    status: "planned",
    summary: "A second decision record with the reviewer's identity, resolving the flag.",
    benefit: "Would close the loop inside Suncly.",
    limit:
      "No CLI command or endpoint records it yet (OQ-P2, stage 5). This workspace lets a reviewer record and export a decision note, kept outside the signed evidence and clearly marked as such.",
    evidence: "docs/API.md 'Operations without an interface'",
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
      "The comparison is computed in this workspace from the two signed bundles. Suncly's store has no comparison or baseline operation; what counts as a drop is an open policy question (OQ-PO2).",
    evidence: "frontend/lib/evidence/compare.ts over result.json; core/cards.py (card hash reuse)",
    group: "evidence",
  },
  {
    id: "cli",
    name: "Command-line interface",
    status: "available",
    summary: "suncly attest, demo, verify, keys init, db migrate, db check, doctor. Documented exit codes; --json for scripts.",
    benefit: "Runs anywhere Python 3.12 runs, including inside your network, with no data leaving it.",
    evidence: "src/suncly/cli/; docs/API.md",
    group: "integration",
  },
  {
    id: "api",
    name: "HTTP API",
    status: "planned",
    summary: "POST /attestations, GET /attestations/{id}, POST /contracts/{id}/approve, GET /agents/{id}/evidence, calling the same core library.",
    benefit: "Would let this workspace start runs and read evidence directly.",
    limit: "Stage 5. api.py is a placeholder; payloads and authentication are open questions (OQ-P1, OQ-P3).",
    evidence: "src/suncly/api.py; docs/API.md",
    group: "integration",
  },
  {
    id: "ci",
    name: "CI gate",
    status: "limited",
    summary: "The CLI runs in a pipeline today with --approve-as, --json and distinct exit codes. Exit code 0 means completed and signed, never approved.",
    benefit: "A pipeline can run the evaluation and archive the report on every release.",
    limit: "A CI adapter that turns a decision into a pass or fail gate is stage 5. Because decisions are flag-only, no pipeline should gate on them yet.",
    evidence: "src/suncly/cli/exit_codes.py; src/suncly/adapters/ci.py (placeholder)",
    group: "integration",
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
