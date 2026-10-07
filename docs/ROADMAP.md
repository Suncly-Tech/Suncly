# Roadmap

Suncly is built in the six stages of schema §9. "Stage 1 is enough to run a
first pilot by hand" (schema §9). The CLI and the API call the same core
library, which is built first (schema §6).

**Status:** MVP implemented, beyond stage 1 and short of stages 2 to 6. Every
stage 1 item below is ticked with the test that proves it. Of the later
stages, the MVP implements: a deterministic Contract builder with the recorded
human approval (stage 2, without a model); the Postgres store, the Evidence
store behind one interface, transcript storage and Ed25519 signing (stage 3);
and a flag-only Policy engine (stage 5, without policy configuration); and,
since 2026-10-07, Judge Layer 2 with its judge subprocess (stage 4, items 1 to
3, without a real provider adapter; [STAGE_4_BRIEF.md](STAGE_4_BRIEF.md)). Not
implemented: model-based drafting and probes, a real model provider adapter,
policy thresholds and `approve`/`block` decisions, human resolution of a flag,
the HTTP API, the CI and registry adapters, the job table. The placeholder
modules `api.py`, `adapters/ci.py` and `adapters/registry.py` name their
stage. Choices the code made are recorded in
[IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md).

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md), **Proposed** marks what the schema does not
define, and `OQ-…` marks open questions. A stage is done when every item in
its definition of done is true.

| Stage | Scope (schema §9) |
|---|---|
| 1 | Core library: runner + deterministic judge + CLI + file report. |
| 2 | Contract builder with human approval step. |
| 3 | Postgres, evidence store, signing. |
| 4 | Model-based judge and probes. |
| 5 | API, policy engine, CI adapter. |
| 6 | Registry adapters. |

The Orchestrator is not assigned to any stage ([OQ-R1](#open-questions)).

## Stage 1: Core library

**Scope:** the Runner, Layer 1 of the Judge, the CLI
`suncly attest <card-url> --runs 50`, and the file report. **Proposed:** the
file report is the first version of the Report adapter
([OQ-R6](#open-questions)).

**Definition of done**

- [x] `suncly attest <card-url> --runs <n>` fetches the Agent Card from
      `<card-url>`, canonicalizes it and computes `card_hash`.
      Proof: `tests/unit/test_card.py::test_identical_cards_with_different_key_order_and_whitespace_hash_the_same`,
      `tests/e2e/test_cli.py::test_attest_from_a_url_alone_completes_and_verifies`.
- [x] The CLI holds no logic of its own. It calls the core library
      (schema §6).
      Proof: `tests/unit/test_architecture.py::test_imports_point_inward_only` (the core never imports the CLI; the CLI only calls `AttestationService`),
      `tests/unit/test_non_negotiable_rules.py` (every rule is proven on the core alone, without the CLI).
- [x] The Runner runs in its own process or container, with network access
      limited to the target (schema §2).
      Proof: `tests/unit/test_runner.py::test_the_transport_refuses_any_host_other_than_the_target`,
      `tests/unit/test_adapters.py::test_subprocess_executor_treats_garbage_output_and_timeouts_as_crashes`,
      every test in `tests/e2e/test_mock_agents.py` (a real Runner process per run).
- [x] The Runner works as an A2A client. It sends each test case's input as a
      Message, follows the Task to a terminal state, and captures every
      message, including a direct Message reply when the agent sends one
      instead of a Task. Which protocol versions and bindings it supports is
      open ([OQ-A4](ARCHITECTURE.md#open-questions)).
      Proof: `tests/unit/test_runner.py::test_send_message_builds_a_1_0_message_and_records_both_exchanges`,
      `::test_a_non_terminal_task_is_polled_with_get_task_until_final`, `::test_direct_message_reply`,
      `tests/e2e/test_mock_agents.py::test_honest_async_agent_is_followed_by_polling_get_task`,
      `::test_direct_message_reply_is_handled_without_error_and_is_not_a_pass`.
- [x] The Runner calls only a sandbox or dry-run endpoint
      ([DR-006](DECISIONS.md#dr-006-tests-hit-a-sandbox-or-dry-run-endpoint)).
      Proof: `tests/unit/test_non_negotiable_rules.py::test_dr_006_tests_hit_only_a_declared_sandbox`,
      `tests/unit/test_runner.py::test_process_refuses_undeclared_sandboxes_and_bad_jobs`,
      `tests/e2e/test_cli.py::test_attest_without_sandbox_declaration_is_refused`.
- [x] Transcripts are redacted inside the Runner before they are returned
      ([DR-003](DECISIONS.md#dr-003-secrets-never-leave-the-runner)).
      Proof: `tests/unit/test_non_negotiable_rules.py::test_dr_003_secrets_never_leave_the_runner`,
      `tests/unit/test_runner.py::test_process_runs_a_job_against_a_local_sandbox_and_redacts_the_credential`,
      `tests/e2e/test_mock_agents.py::test_leaky_agent_cannot_make_the_credential_appear_anywhere`.
- [x] Every run has a deterministic run key. Re-running a crashed or retried
      run never produces a second counted result
      ([DR-001](DECISIONS.md#dr-001-idempotent-runs)).
      Proof: `tests/unit/test_non_negotiable_rules.py::test_dr_001_idempotent_runs_retry_under_the_same_key_and_count_once`,
      `tests/stores/test_store_contract.py::test_rejects_a_second_run_with_an_existing_run_key` (both stores),
      `tests/db/test_migration_constraints.py::test_rejects_a_second_run_with_an_existing_run_key`.
- [x] Layer 1 of the Judge checks valid schema, final task state, required
      fields and the latency limit. It assigns `pass`, `fail` or
      `inconclusive`, and `inconclusive` is never counted as a pass.
      Proof: `tests/unit/test_judge.py` (one test per check),
      `tests/unit/test_non_negotiable_rules.py::test_inconclusive_is_never_counted_as_a_pass`,
      `tests/unit/test_signing_policy_verify.py::test_aggregate_keeps_inconclusive_apart_and_lists_every_test_case`.
- [x] The file report shows the verdict counts for each test case and states
      what was NOT tested
      ([DR-007](DECISIONS.md#dr-007-reports-state-what-was-not-tested)).
      Proof: `tests/unit/test_non_negotiable_rules.py::test_dr_007_reports_state_what_was_not_tested`,
      `tests/unit/test_adapters.py::test_report_folder_is_self_contained_and_offline`,
      `tests/e2e/test_mock_agents.py::test_skill_without_examples_is_listed_as_not_tested`,
      `::test_budget_stop_ends_failed_and_reports_runs_never_executed`.
- [x] A person can run a pilot attestation by hand, from start to finish
      (schema §9).
      Proof: `tests/e2e/test_cli.py::test_attest_from_a_url_alone_completes_and_verifies`,
      `::test_demo_runs_both_agents_and_both_end_flagged`, and the walkthrough in
      [QUICKSTART.md](QUICKSTART.md).

**Beyond stage 1 as planned:** the implemented MVP also includes the
deterministic Contract builder with the recorded approval, the Postgres store
and signing, and the flag-only Policy engine, so every attestation is signed
and records a `flag` decision (decided 2026-10-04; see the status above).
Layer 2 is implemented as stage 4, items 1 to 3 (2026-10-07).

**Open:** [OQ-R1](#open-questions) (repetitions, and the non-negotiable budget
cap of [DR-005](DECISIONS.md#dr-005-budget-caps-live-in-the-orchestrator),
without an Orchestrator), [OQ-R2](#open-questions) (where test cases come from)
and [OQ-P4](API.md#open-questions) (credentials). A2A-T7, whether the Python
SDK supports protocol 1.0, is verified, and the own client is decided
([ARCHITECTURE.md](ARCHITECTURE.md#protocol-details-still-to-verify)).

## Stage 2: Contract builder with human approval

**Scope:** the Contract builder, including the human approval step.

**Definition of done**

- [ ] A card with a new `card_hash` gets a new `card_version` with
      `raw_json`, `card_hash` and `fetched_at`.
- [ ] A model drafts a `contract` with `status` `draft` and at least one
      `test_case` per declared skill, where `skill_id` is the skill's
      `AgentSkill.id`.
- [ ] Drafting uses the customer's own model keys (schema §7;
      [OQ-A1](ARCHITECTURE.md#open-questions)).
- [ ] Nothing runs against a contract until a human approves it. Approval sets
      `status` to `approved` and fills in `approved_by` and `approved_at`.
- [ ] An approved contract and its test cases cannot be changed. An edit
      creates a new contract version.
- [ ] A rejected draft gets `status` `rejected` and is never run.
- [ ] The CLI runs only approved contracts.

**Open:** [OQ-R3](#open-questions) (the approval interface and storage before
stages 3 and 5), [OQ-D5](DATA_MODEL.md#open-questions) (contract lifecycle),
[OQ-D7](DATA_MODEL.md#open-questions) (test case formats),
[OQ-P2](API.md#open-questions) (no interface yet for rejecting a contract), and
[OQ-A1](ARCHITECTURE.md#open-questions) (model keys).

## Stage 3: Postgres, Evidence store, signing

**Scope:** Postgres storage, the Evidence store, and attestation signing.

**Definition of done**

- [ ] The seven entities exist in Postgres with the fields, keys and enum
      values in [DATA_MODEL.md](DATA_MODEL.md).
- [ ] Transcripts are stored in object storage and referenced by
      `run.transcript_ref`.
- [ ] The Evidence store is append-only. `run` and `decision` records cannot
      be updated or deleted, and corrections are new records
      ([DR-002](DECISIONS.md#dr-002-evidence-is-immutable)).
- [ ] **Proposed**, to implement
      [DR-001](DECISIONS.md#dr-001-idempotent-runs): a second record with an
      existing run key is rejected.
- [ ] Attestations are signed with an asymmetric key of the Suncly deployment,
      over the canonicalized payload in schema §11. For the decision fields,
      see [OQ-R4](#open-questions). `signing_key_id` identifies the key, and
      the signature can be checked with the matching public key.

**Open:** [OQ-R4](#open-questions) (the payload includes a decision that
stage 3 cannot make yet), [OQ-D6](DATA_MODEL.md#open-questions),
[OQ-D8](DATA_MODEL.md#open-questions) and
[OQ-A8](ARCHITECTURE.md#open-questions).

## Stage 4: Model-based judge and probes

**Scope:** Layer 2 of the Judge, and probe test cases.

**Definition of done**

- [x] Layer 2 judges only criteria that Layer 1 cannot decide, with a fixed
      rubric and a model pinned by version. Its rationale is stored on the
      run, and `judge_layer` is `model`.
      Proof: `tests/unit/test_judge_layer_2.py::test_layer_2_is_not_asked_when_layer_1_decided`,
      `::test_layer_2_is_not_asked_when_there_is_no_response_to_judge`,
      `::test_layer_2_asks_once_per_undecided_model_check_with_the_criterion_in_the_prompt`,
      `::test_pass_when_the_pinned_model_answers_in_shape_and_the_rule_passes`,
      `::test_the_evidence_document_records_everything_layer_2_saw_and_said` (rationale on the run, `judge_layer` `model`, rubric version and hash, model id).
- [x] Changing the judge model or the rubric takes an explicit configuration
      change ([DR-004](DECISIONS.md#dr-004-judge-model-is-pinned)).
      Proof: `tests/unit/test_judge_layer_2.py::test_without_a_configured_model_a_model_check_is_inconclusive_and_layer_1_decided` (no default model),
      `::test_the_pinned_model_comes_from_the_configuration_alone`,
      `::test_an_answer_from_another_model_than_the_pinned_one_is_no_verdict`,
      `::test_a_rubric_version_this_build_does_not_carry_is_refused`,
      `::test_the_rubric_is_versioned_and_hashed_and_a_changed_frame_changes_the_hash`,
      `::test_a_judge_configured_only_in_part_is_refused_before_anything_runs`.
- [x] A Layer 2 failure never produces `pass`.
      Proof: `tests/unit/test_judge_layer_2.py::test_inconclusive_never_pass_when_the_model_fails`,
      `::test_inconclusive_on_a_timeout`, `::test_inconclusive_on_malformed_output`,
      `::test_a_score_must_be_a_whole_number_from_0_to_10`,
      `::test_a_mix_of_decided_and_undecided_model_checks_stays_inconclusive`,
      `::test_the_adapter_treats_a_killed_silent_or_garbled_process_as_a_model_failure`.
- [ ] The Contract builder drafts probes with `kind` `probe_undeclared`,
      `probe_injection` and `probe_failure`. They go through the same human
      approval as skill test cases.
- [ ] Probes run only against the sandbox or dry-run endpoint
      ([DR-006](DECISIONS.md#dr-006-tests-hit-a-sandbox-or-dry-run-endpoint)).
- [ ] Model calls use the customer's own keys (schema §7). The judge
      subprocess reads the customer's key and speaks the Anthropic Messages
      API (`judge/process.py`, 2026-10-07), but no call to the real API has
      been made from this repository yet. Tick when
      `tests/live/test_messages_api_live.py` has passed with a customer key;
      CI skips it.

**Decided 2026-10-07:** [OQ-A1](ARCHITECTURE.md#open-questions),
[OQ-D4](DATA_MODEL.md#open-questions), [OQ-D7](DATA_MODEL.md#open-questions)
for the model checks, [OQ-PO6](POLICY.md#open-questions) for the aggregation
level, the pinned model and the rubric
([IMPLEMENTATION_NOTES.md](IMPLEMENTATION_NOTES.md), section 3). **Open:** the
probe kinds (OQ-D7, OQ-PO6) and the judge model id (a recommendation is in
[STAGE_4_BRIEF.md](STAGE_4_BRIEF.md)).

## Stage 5: API, Policy engine, CI adapter

**Scope:** the four HTTP endpoints, the Policy engine and the CI adapter.

**Definition of done**

- [ ] The four endpoints in [API.md](API.md) work and call the same core
      library as the CLI (schema §6).
- [ ] The Policy engine applies the customer's per-risk-level thresholds to
      aggregated results. It writes a `decision` with `outcome` `approve`,
      `flag` or `block`, plus `policy_version`, `decided_by` `"policy"` and
      `decided_at`.
- [ ] It follows [POLICY.md](POLICY.md): it never approves a `high` risk agent
      automatically, it flags borderline and dropping results, and it never
      counts `inconclusive` as a pass.
- [ ] No decision is made for an attestation that is `failed` or
      `invalidated` (schema §11).
- [ ] A human resolution of a `flag` is stored as a second `decision`, and the
      first is never edited (schema §11).
- [ ] No numeric threshold is built into the code. Thresholds come from the
      customer's configuration (schema §5).
- [ ] The CI adapter returns pass or fail to the pipeline.

**Open:** [OQ-P1](API.md#open-questions), [OQ-P2](API.md#open-questions),
[OQ-P3](API.md#open-questions), [OQ-PO1](POLICY.md#open-questions) to
[OQ-PO7](POLICY.md#open-questions), and
[OQ-A9](ARCHITECTURE.md#open-questions).

## Stage 6: Registry adapters

**Scope:** adapters that write approval status into companies' agent
registries.

**Definition of done**

- [ ] Each Registry adapter in scope writes the approval status, derived from
      decisions, to its registry.
- [ ] Adapters stay thin and outside the core, with no decision logic of
      their own (schema §2).
- [ ] Suncly does not become a registry (schema §10).

**Open:** [OQ-A9](ARCHITECTURE.md#open-questions) and
[OQ-R5](#open-questions).

## Not on the roadmap

These are out of scope (schema §10): registry, gateway, identity system,
monitoring platform, universal score, payments. What that means for each
component is in
[ARCHITECTURE.md: Out of scope](ARCHITECTURE.md#out-of-scope).

## Open questions

- **OQ-R1 The Orchestrator has no stage.** Schema §9 never assigns the
  Orchestrator to a stage. But stage 1's repeated runs (`--runs`) already need
  the repetitions, timeouts and retries that schema §2 gives the
  Orchestrator, and the budget cap that schema §8 places there. The Postgres-backed job table cannot exist before stage 3.
  **Proposed:** a minimal Orchestrator inside the process in stage 1, and the
  job table in stage 3.
- **OQ-R2 Stage 1 test cases.** The Contract builder arrives in stage 2. Where
  do stage 1's test cases come from? **Proposed:** a contract file written by
  hand.
- **OQ-R3 Stages 2 to 4.** How does a human approve a contract before the API
  exists (stage 5)? And where are contracts and results stored before Postgres
  (stage 3)?
- **OQ-R4 Signing before decisions exist.** Signing arrives in stage 3, but
  the schema §11 payload includes the decision outcome and `policy_version`,
  which do not exist until the Policy engine in stage 5. What do stage 3 and 4
  signatures cover? And which component signs in those stages, given that the
  signer in schema §4, step 6 is the Policy engine?
- **OQ-R5 Which registries.** Schema §9 says "Registry adapters", plural.
  Which registry products does stage 6 target?
- **OQ-R6 The stage 1 file report.** Schema §9 lists the file report under the
  core library, while schema §2 places adapters outside the core. Is the file
  report the first version of the Report adapter (this document's reading),
  or part of the core library?
