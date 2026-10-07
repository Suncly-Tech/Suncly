# Decision records

These records cover the seven non-negotiable rules in schema §8. Each one
gives the decision, the reason for it, and its consequences. All seven are
**Accepted**, because the schema makes them non-negotiable. Changing one means
changing [SCHEMA.md](../SCHEMA.md) first.

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md), **Proposed** marks what the schema does not
define, and `OQ-…` marks open questions.

## DR-001 Idempotent runs

- **Status:** Accepted (schema §8).
- **Decision:** Every run has a deterministic key. Retries never double count.
- **Reason:**
  - The Orchestrator retries runs, and its stateless workers can pick up the
    same job twice after a crash (schema §2).
  - If a run could be counted twice, the aggregated results the Policy engine
    decides on would be wrong.
  - The signed attestation would then describe runs that did not happen the
    way it says.
- **Consequence:**
  - The run key is (`attestation_id`, `test_case_id`, `attempt`), a
    **Proposed** unique key ([DATA_MODEL.md](DATA_MODEL.md#run)).
  - A retry reuses its run's key.
  - **Proposed:** the Evidence store rejects a second record with a key that
    already exists.
  - This depends on what `attempt` means ([OQ-D3](DATA_MODEL.md#open-questions)).

## DR-002 Evidence is immutable

- **Status:** Accepted (schema §8).
- **Decision:** Evidence is never changed. Corrections are new records.
- **Reason:**
  - An attestation is signed evidence behind an approval.
  - If records could be edited afterwards, neither the signature nor the
    approval it supports could be trusted, and nobody could check later what
    was actually decided.
- **Consequence:**
  - The Evidence store is append-only (schema §2).
  - `run` and `decision` records are never updated or deleted.
  - A human resolution of a `flag` is a second `decision` record, and the
    first is never edited (schema §11).
  - Approved contracts are immutable, and an edit creates a new version
    (schema §2).
  - Still open: which `attestation` fields may change while it runs
    ([OQ-D6](DATA_MODEL.md#open-questions)), and the `superseded` status on
    approved contracts ([OQ-D5](DATA_MODEL.md#open-questions)).

## DR-003 Secrets never leave the Runner

- **Status:** Accepted (schema §8).
- **Decision:** Secrets never leave the Runner. Transcripts are redacted
  before storage.
- **Reason:**
  - Customer credentials give access to the customer's agent.
  - Transcripts are stored, signed over and shown to reviewers.
  - Keeping credentials in one isolated component, the only one that calls the
    agent (schema §2), limits who can ever see them.
- **Consequence:**
  - The Runner redacts every transcript before returning it. The Judge,
    Evidence store, adapters and API only ever see redacted transcripts.
  - The transcript hashes in the signature (schema §11) are necessarily
    hashes of the redacted transcripts, because only those are stored.
  - This is what allows the Runner to run inside the customer's network later
    (schema §2): the credentials can stay there.
  - Still open: the customer's own model keys
    ([OQ-A1](ARCHITECTURE.md#open-questions)), what counts as a secret
    ([OQ-A3](ARCHITECTURE.md#open-questions)), and how credentials reach the
    Runner ([OQ-P4](API.md#open-questions)).

## DR-004 Judge model is pinned

- **Status:** Accepted (schema §8).
- **Decision:** The judge model is pinned. Results must not drift when the
  judge changes.
- **Reason:**
  - An attestation should measure the agent, not changes in the judge.
  - Comparing attestations, for example to spot "dropping results"
    (schema §5), only makes sense if the judge stays the same.
- **Consequence:**
  - Layer 2 uses a model pinned by version (schema §7) and a fixed rubric
    (schema §2). A change of judge model is a deliberate configuration change,
    never drift.
  - Layer 2 runs only for criteria that Layer 1 cannot decide (schema §2), so
    fewer verdicts depend on a model at all.
  - How the code enforces it (decided 2026-10-07): the model id comes from the
    configuration with no default; the rubric frame is versioned and the
    configuration must name the version in use; the model id, the rubric
    version and the rubric hash are written into every Layer 2 evidence
    document ([OQ-D4](DATA_MODEL.md#open-questions), decided;
    [STAGE_4_BRIEF.md](STAGE_4_BRIEF.md)).

## DR-005 Budget caps live in the Orchestrator

- **Status:** Accepted (schema §8).
- **Decision:** Budget caps live in the Orchestrator, so there are no surprise
  bills.
- **Reason:**
  - The number of runs is test cases times repetitions, so costs multiply
    quickly.
  - The Orchestrator is the component that enqueues runs, which makes it the
    one place that can stop a run before it costs anything.
- **Consequence:**
  - Each attestation has a `budget_limit` and a running `cost_total`
    (schema §11).
  - The Orchestrator stops enqueuing runs when `cost_total` reaches
    `budget_limit`. The attestation ends as `failed`, and no decision is made
    (schema §11).
  - Still open: what counts as cost ([OQ-D1](DATA_MODEL.md#open-questions)),
    runs already in flight ([OQ-F4](FLOW.md#open-questions)), and the fact
    that the Orchestrator has no build stage
    ([OQ-R1](ROADMAP.md#open-questions)).

## DR-006 Tests hit a sandbox or dry-run endpoint

- **Status:** Accepted (schema §8).
- **Decision:** Tests hit a sandbox or dry-run endpoint. Nothing real is
  booked, paid or deleted.
- **Reason:**
  - Every test case runs many times, and probes deliberately try injected
    instructions and failure conditions (probe definitions:
    [OQ-D7](DATA_MODEL.md#open-questions)).
  - Against a production endpoint, that could cause real bookings, payments
    or deletions, and `high` risk agents handle payments and personal data
    (schema §5).
- **Consequence:**
  - The Runner calls only a sandbox or dry-run endpoint.
  - **Proposed:** reports say that results come from that endpoint, not from
    production ([DR-007](#dr-007-reports-state-what-was-not-tested),
    [OQ-A11](ARCHITECTURE.md#open-questions)).
  - Still open: how a sandbox is identified and enforced, and which Agent Card
    is attested ([OQ-A2](ARCHITECTURE.md#open-questions)).

## DR-007 Reports state what was NOT tested

- **Status:** Accepted (schema §8).
- **Decision:** Reports state what was NOT tested.
- **Reason:**
  - An approval based on partial evidence misleads if the gaps are invisible.
  - Reviewers need to see the limits of an attestation, and Suncly does not
    produce a universal score that would hide them (schema §10).
- **Consequence:**
  - Every report from the Report adapter has a "not tested" statement.
  - **Proposed:** examples of what it covers are runs never executed after a
    budget stop, `inconclusive` runs, declared capabilities and protocol
    bindings that no test exercised, and the production endpoint
    ([ARCHITECTURE.md: Report adapter](ARCHITECTURE.md#report-adapter),
    [OQ-A11](ARCHITECTURE.md#open-questions)).
  - Still open: the planned number of repetitions is not stored, so runs that
    were never executed cannot be counted
    ([OQ-D3](DATA_MODEL.md#open-questions)).

## Related rules elsewhere in the schema

These rules are binding too, but are not in schema §8. They are documented
where they apply:

- An `inconclusive` verdict is never counted as a pass (schema §2):
  [ARCHITECTURE.md: Judge](ARCHITECTURE.md#judge) and
  [POLICY.md](POLICY.md#inconclusive-results).
- Approved contracts are immutable, and any edit creates a new version
  (schema §2): [ARCHITECTURE.md: Contract builder](ARCHITECTURE.md#contract-builder).
- A human is always required for first contract approval, new or changed
  skills, and borderline or dropping results (schema §5):
  [POLICY.md](POLICY.md#when-a-human-is-required).
- Budget, card-change and signature rules (schema §11):
  [FLOW.md](FLOW.md#failure-paths).

## Open questions

This document has no open questions of its own. The open questions that
affect each decision are listed under "Still open" in its record and are
defined in the documents that own them.
