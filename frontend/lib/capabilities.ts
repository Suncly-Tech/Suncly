/**
 * The capability map: what Suncly does today, what is in pilot, and what is planned.
 *
 * One source for the website and the workspace. Every "available" entry names the code
 * and the test that prove it; every "planned" entry names the roadmap stage or the
 * founder input that decides it. Components read status from here, so changing a status
 * later is a one-line edit (or one line in lib/launch.ts for the launch-state items).
 *
 * The three public status words:
 *  - available: a visitor can do it today. Implemented in src/suncly and covered by tests.
 *               A limitation a buyer must know about is stated in `limit`, in normal type.
 *  - pilot:     exists and is used with pilots (the CLI as a whole; programme states).
 *  - planned:   not implemented. Written in the future tense, no date promised.
 */

import { launch } from "./launch";

export type Availability = "available" | "pilot" | "planned";

export const AVAILABILITY_LABEL: Record<Availability, string> = {
  available: "Available",
  pilot: "Pilot",
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
  /** The limitation (for available) or what is missing (for planned). */
  limit?: string;
  /** Where it lives in the repository, or which founder input decides it. */
  evidence: string;
  group: "evaluation" | "evidence" | "approval" | "operations" | "integration" | "commercial" | "agents";
}

const testedStatus = (tool: keyof typeof launch.testedIn): Availability => (launch.testedIn[tool] ? "available" : "planned");

const programmeStatus: Availability =
  launch.certificationProgramme === "open" ? "available" : launch.certificationProgramme === "pilot" ? "pilot" : "planned";

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
    status: "available",
    summary:
      "One test case per declared example of each skill, up to a cap. Criteria: completes, answers, uses the declared output modes, within a latency limit.",
    benefit: "The test plan comes from the agent's own claims, not from a reviewer's mood that day.",
    limit: "Drafting is deterministic; no model is used. A skill that declares no examples gets no test case and is reported as not tested.",
    evidence: "src/suncly/core/contract_builder.py (DeterministicDrafter); tests/e2e/test_mock_agents.py::test_skill_without_examples_is_listed_as_not_tested",
    group: "evaluation",
  },
  {
    id: "human-approval",
    name: "Human review of the test plan",
    status: "available",
    summary: "Nothing runs until a named person approves the drafted contract; approved_by and approved_at are recorded and the contract becomes immutable.",
    benefit: "Someone is accountable for what was tested, and the record says who.",
    evidence: "src/suncly/core/contract_builder.py; tests/unit/test_non_negotiable_rules.py::test_nothing_runs_against_a_contract_until_a_human_has_approved_it",
    group: "approval",
  },
  {
    id: "custom-criteria",
    name: "Customer-defined criteria and known-answer checks",
    status: "available",
    summary: "Export the draft, add required fields, a JSON schema, latency limits or expected final states, and run with the file.",
    benefit: "Your reviewers decide what a pass means for your agent.",
    limit: "Criteria are structural. A model_check makes the run inconclusive until the model-based judge exists.",
    evidence: "src/suncly/domain/contract_file.py, domain/criteria.py; tests/unit/test_judge.py::test_model_checks_make_the_run_inconclusive_until_layer_2_exists",
    group: "evaluation",
  },
  {
    id: "repeated-runs",
    name: "Repeated runs that expose inconsistent behaviour",
    status: "available",
    summary: "Each test case runs --runs times (default 5) under a deterministic run key; retries never double count.",
    benefit: "An agent that works three times in five shows up as three passes and two fails, not as a lucky demo.",
    evidence: "src/suncly/core/orchestrator.py; tests/unit/test_non_negotiable_rules.py::test_dr_001_idempotent_runs_retry_under_the_same_key_and_count_once",
    group: "evaluation",
  },
  {
    id: "deterministic-judge",
    name: "Deterministic verdicts: pass, fail, inconclusive",
    status: "available",
    summary: "Valid schema, final task state, latency, response present, declared output modes, required fields, response schema. Any failed check is a fail; any undecided check is inconclusive.",
    benefit: "The same evidence always gets the same verdict, and inconclusive is never counted as a pass.",
    limit: "Layer 1 only. Whether the content of an answer is correct needs Layer 2 (stage 4), and every report says so.",
    evidence: "src/suncly/core/judge.py; tests/unit/test_non_negotiable_rules.py::test_inconclusive_is_never_counted_as_a_pass",
    group: "evaluation",
  },
  {
    id: "probes",
    name: "Prompt-injection, undeclared-behaviour and failure-handling probes",
    status: "planned",
    summary: "Test cases of kind probe_injection, probe_undeclared and probe_failure will run alongside the skill tests.",
    benefit: "Behaviour outside the declared skills will be exercised, not assumed.",
    limit: "Not implemented. Every report lists probes under what was not tested.",
    evidence: "docs/ROADMAP.md stage 4; src/suncly/core/coverage.py (the unconditional 'probes' item)",
    group: "evaluation",
  },
  {
    id: "sandbox-only",
    name: "Sandbox or dry-run endpoints only",
    status: "available",
    summary: "Nothing runs without --sandbox. The Runner refuses undeclared targets a second time, and the report records the declaration.",
    benefit: "Nothing real is booked, paid or deleted by a test.",
    limit: "Suncly cannot verify that an endpoint is a sandbox. The declaration is yours and is recorded as such.",
    evidence: "src/suncly/core/attestation.py, runner/process.py; tests/unit/test_non_negotiable_rules.py::test_dr_006_tests_hit_only_a_declared_sandbox",
    group: "operations",
  },
  {
    id: "credentials",
    name: "Credentials held only by the Runner, redacted from evidence",
    status: "available",
    summary: "One Authorization value from an environment variable that only the Runner process reads; redacted from every transcript before it leaves the process.",
    benefit: "Your agent credential never reaches the evidence store, the report or the workspace.",
    evidence: "src/suncly/runner/credentials.py, runner/redaction.py; tests/unit/test_architecture.py::test_only_the_runner_reads_the_credential; tests/e2e/test_mock_agents.py::test_leaky_agent_cannot_make_the_credential_appear_anywhere",
    group: "operations",
  },
  {
    id: "budget",
    name: "Budget and execution controls",
    status: "available",
    summary: "A budget of attempts (default twice the planned runs), a per-run timeout, concurrency limits and retries. A budget stop ends the attestation as failed with no decision.",
    benefit: "No surprise bills and no half-counted results.",
    evidence: "src/suncly/core/orchestrator.py; tests/e2e/test_mock_agents.py::test_budget_stop_ends_failed_and_reports_runs_never_executed",
    group: "operations",
  },
  {
    id: "signed-evidence",
    name: "Signed, verifiable evidence",
    status: "available",
    summary: "Ed25519 over the RFC 8785 form of the attestation id, card hash, contract, per-test-case counts, every transcript hash and the decision. suncly verify re-checks it offline.",
    benefit: "Anyone with the report folder can prove it was not altered after signing.",
    evidence: "src/suncly/core/signing.py, core/verify.py; tests/unit/test_signing_policy_verify.py",
    group: "evidence",
  },
  {
    id: "not-tested",
    name: "Explicit inconclusive outcomes and coverage gaps",
    status: "available",
    summary: "Every report ends with what was NOT tested: skills without a test case, runs never executed, inconclusive runs, declared capabilities not exercised, interfaces not used, probes, semantic correctness, the production endpoint.",
    benefit: "The gaps are on the page, not in the reviewer's memory.",
    evidence: "src/suncly/core/coverage.py; tests/unit/test_non_negotiable_rules.py::test_dr_007_reports_state_what_was_not_tested",
    group: "evidence",
  },
  {
    id: "reports",
    name: "Exportable evaluation reports",
    status: "available",
    summary: "A report folder with report.html (offline), report.md, result.json and one redacted transcript per run.",
    benefit: "The evidence travels with the ticket.",
    evidence: "src/suncly/adapters/report/; tests/unit/test_adapters.py::test_report_folder_is_self_contained_and_offline",
    group: "evidence",
  },
  {
    id: "storage",
    name: "Append-only evidence store, file or Postgres",
    status: "available",
    summary: "Run and decision records are never updated or deleted; corrections are new records. Files under ~/.suncly/store by default, or Postgres with DATABASE_URL.",
    benefit: "What was decided can be checked later, unchanged.",
    limit: "Transcripts stay on local disk until an object storage adapter exists.",
    evidence: "src/suncly/adapters/file_store.py, adapters/postgres/; db/migrations/0001_initial_schema.sql (append-only triggers)",
    group: "evidence",
  },
  {
    id: "policy",
    name: "Automatic approval decisions",
    status: "available",
    summary: "The Policy engine records one signed decision per completed evaluation.",
    benefit: "Every evaluation ends with a recorded decision and a reviewer in the loop.",
    limit: "Flag only. Without a configured policy Suncly never approves or blocks an agent; approve and block thresholds are stage 5.",
    evidence: "src/suncly/core/policy_engine.py; tests/unit/test_non_negotiable_rules.py::test_suncly_never_writes_an_approve_decision",
    group: "approval",
  },
  {
    id: "human-decision",
    name: "Recording the reviewer's decision in the evidence store",
    status: "planned",
    summary: "A human resolution of a flag will be a second decision record; the first is never edited.",
    benefit: "The reviewer's decision will sit next to the evidence it was made on.",
    limit: "No interface records it yet. The workspace keeps reviewer notes locally and exports them.",
    evidence: "docs/ROADMAP.md stage 5; docs/API.md OQ-P2",
    group: "approval",
  },
  {
    id: "comparison",
    name: "Regression comparisons between evaluations",
    status: "available",
    summary: "An unchanged card reuses its approved contract, so two evaluations run the same tests and their counts are comparable.",
    benefit: "An unchanged card is not treated as an unchanged agent.",
    limit: "Computed in the workspace from two signed bundles; the store has no comparison operation of its own.",
    evidence: "frontend/lib/evidence/compare.ts; src/suncly/core/cards.py::ensure_card_version",
    group: "evidence",
  },
  {
    id: "cli",
    name: "Command-line interface",
    status: launch.cli,
    summary: "suncly attest, demo, verify, keys init, db migrate, db check and doctor. Installed from a clone with pip install -e .",
    benefit: "A person can run a complete evaluation by hand today.",
    limit: "Installed from the repository; there is no published package.",
    evidence: "src/suncly/cli/main.py; docs/QUICKSTART.md; run in the build session (VERIFICATION.md)",
    group: "integration",
  },
  {
    id: "http-api",
    name: "HTTP API",
    status: launch.httpApi === "live" ? "available" : launch.httpApi === "pilot" ? "pilot" : "planned",
    summary: "POST /attestations, GET /attestations/{id}, POST /contracts/{id}/approve and GET /agents/{id}/evidence will call the same core library as the CLI.",
    benefit: "Evaluations will be started and read from pipelines and the workspace.",
    limit: "Not implemented; src/suncly/api.py is a placeholder.",
    evidence: "docs/ROADMAP.md stage 5; docs/API.md (Proposed)",
    group: "integration",
  },
  {
    id: "ci",
    name: "CI gate",
    status: "available",
    summary: "Run suncly attest in a pipeline with --approve-as and a committed contract file; the exit code says whether the evaluation completed.",
    benefit: "Every build of an agent can carry a fresh evaluation.",
    limit: "Exit code 0 means completed and signed, never approved. A CI adapter that gates on a decision is stage 5.",
    evidence: "src/suncly/cli/exit_codes.py; docs/API.md exit codes",
    group: "integration",
  },
  {
    id: "registry",
    name: "Registry integration",
    status: "planned",
    summary: "Adapters will write an approval status to an agent registry.",
    benefit: "The registry will show the evidence behind each entry.",
    limit: "Not implemented; src/suncly/adapters/registry.py is a placeholder.",
    evidence: "docs/ROADMAP.md stage 6",
    group: "integration",
  },
  {
    id: "usage-billing",
    name: "Usage-only billing of the Suncly API",
    status: launch.usageBilling === "live" ? "available" : "planned",
    summary: "Suncly will charge for a customer's usage of the Suncly API and for nothing else: no seats, no plans. Connecting and the badge are free.",
    benefit: "You will pay for evaluations you run, not for a tier.",
    limit: "Billing is not live. The billable unit and the price are not yet published.",
    evidence: "Founder inputs block 4 (lib/launch.ts); SCHEMA.md §10 keeps payments outside the core",
    group: "commercial",
  },
  {
    id: "certification",
    name: "Suncly Certified badge",
    status: programmeStatus,
    summary: "Agents that meet Suncly's published criteria will carry a badge that links to its record: what was tested, when, on which version, and what was not.",
    benefit: "A buyer can see the evidence behind a badge instead of trusting the badge.",
    limit: "The programme opens with our pilots. No criteria are published as accepted and no agent is certified.",
    evidence: "Founder inputs blocks 3 and 6 (lib/launch.ts); /certified/policy (draft)",
    group: "commercial",
  },
  {
    id: "agent-cursor",
    name: "Cursor",
    status: testedStatus("cursor"),
    summary: "Guided setup for running Suncly from Cursor.",
    benefit: "Run the evaluation from the editor your team already uses.",
    limit: "Planned. Until then, run the Terminal steps from the tool's terminal.",
    evidence: "Founder inputs block 3 tested_in (lib/launch.ts)",
    group: "agents",
  },
  {
    id: "agent-claude-code",
    name: "Claude Code",
    status: testedStatus("claude-code"),
    summary: "Guided setup for running Suncly from Claude Code.",
    benefit: "Run the evaluation from the agent your team already uses.",
    limit: "Planned. Until then, run the Terminal steps from the tool's terminal.",
    evidence: "Founder inputs block 3 tested_in (lib/launch.ts)",
    group: "agents",
  },
  {
    id: "agent-codex",
    name: "Codex",
    status: testedStatus("codex"),
    summary: "Guided setup for running Suncly from Codex.",
    benefit: "Run the evaluation from the agent your team already uses.",
    limit: "Planned. Until then, run the Terminal steps from the tool's terminal.",
    evidence: "Founder inputs block 3 tested_in (lib/launch.ts)",
    group: "agents",
  },
  {
    id: "agent-omp",
    name: "omp",
    status: testedStatus("omp"),
    summary: "Guided setup for running Suncly from omp.",
    benefit: "Run the evaluation from the agent your team already uses.",
    limit: "Planned. Until then, run the Terminal steps from the tool's terminal.",
    evidence: "Founder inputs block 3 tested_in (lib/launch.ts)",
    group: "agents",
  },
  {
    id: "agent-pi",
    name: "Pi",
    status: testedStatus("pi"),
    summary: "Guided setup for running Suncly from Pi.",
    benefit: "Run the evaluation from the agent your team already uses.",
    limit: "Planned. Until then, run the Terminal steps from the tool's terminal.",
    evidence: "Founder inputs block 3 tested_in (lib/launch.ts)",
    group: "agents",
  },
];

export const byGroup = (group: Capability["group"]) => capabilities.filter((c) => c.group === group);
export const byStatus = (status: Availability) => capabilities.filter((c) => c.status === status);
export const capability = (id: string) => capabilities.find((c) => c.id === id);

/** The coding agents, in the brief's order and spelling. */
export const codingAgents = () => ["agent-cursor", "agent-claude-code", "agent-codex", "agent-omp", "agent-pi"].map((id) => capability(id)!);
export const anyAgentVerified = () => codingAgents().some((c) => c.status === "available");

/** The hero's status line, generated from the map so it cannot drift from it. */
export function heroStatusLine(): string[] {
  const cli = capability("cli")!;
  return [`CLI in ${AVAILABILITY_LABEL[cli.status].toLowerCase()}`, "A2A 1.0 over JSON-RPC", "The decision stays yours."];
}
