# Approval policy

This document covers how the Policy engine turns attestation results into a
decision, and when a human is required. The source is the default approval
policy in schema §5, together with the Policy engine in schema §2 and the
decision rules in schema §11.

Conventions are as in [ARCHITECTURE.md](ARCHITECTURE.md): "schema §N" refers
to [SCHEMA.md](../SCHEMA.md), **Proposed** marks what the schema does not
define, and `OQ-…` marks open questions.

## What the Policy engine decides

- **Inputs:**
  - the attestation's run records from the Evidence store, which it
    aggregates per test case (schema §4, step 6);
  - `agent.risk_level`;
  - the customer's policy configuration, identified by `policy_version`.
- **Output:** a `decision` record whose `outcome` is `approve`, `flag` or
  `block`, with `decided_by` set to `"policy"`.
- **When:** only for an attestation whose runs have all finished and whose
  card did not change. An attestation that ended `failed` or `invalidated`
  gets no decision (schema §11).

## Risk levels

The default policy from schema §5:

| `risk_level` | Example | Approval |
|---|---|---|
| `low` | read-only lookup | automatic on pass |
| `medium` | writes to internal systems | automatic on pass, human on any drop |
| `high` | payments, personal data | human sign-off every time |

Customers configure the thresholds per risk level (schema §5). Every agent has
one `risk_level` (`agent.risk_level`). Who sets it, and how, is not defined
([OQ-P2](API.md#open-questions)).

## Decision outcomes

| `outcome` | Meaning | What follows |
|---|---|---|
| `approve` | The results meet the policy for the agent's risk level, and no human is required. | **Proposed:** the adapters report the agent as approved ([OQ-A9](ARCHITECTURE.md#open-questions)). |
| `flag` | A human must decide. Schema §2 calls this "flag for human review". | A human records a second decision. |
| `block` | The results do not meet the policy. | **Proposed:** the adapters report the agent as blocked ([OQ-A9](ARCHITECTURE.md#open-questions)). |

## When a human is required

"Human is always required: first contract approval, new or changed skills,
borderline or dropping results" (schema §5). A high-risk agent also needs
human sign-off every time.

| Situation | How the human is involved |
|---|---|
| First contract approval | A human must approve the drafted contract. Nothing runs before that (schema §2, §4). |
| New or changed skills | Any change to the card produces a new hash, which produces a new draft contract that a human must approve (schema §4, step 2). Because the whole card is hashed, changes outside the skills trigger this too, unless the hashing rule changes ([OQ-A7](ARCHITECTURE.md#open-questions)). This document reads the contract approval as the human step this rule requires ([OQ-PO8](#open-questions)). |
| Borderline results | The Policy engine outputs `flag`, and a human records a second decision. |
| Dropping results | The Policy engine outputs `flag`, and a human records a second decision. |
| `high` risk | The Policy engine never approves automatically. A human signs off every time ([OQ-PO4](#open-questions)). |

## Decision table

This table combines the rules above. Its result categories depend on
thresholds and definitions that are still open ([OQ-PO1](#open-questions) to
[OQ-PO3](#open-questions)):

- **pass:** the aggregated results meet the threshold for the risk level.
- **borderline:** close to the threshold. The definition is open.
- **drop:** worse than a baseline. The definition is open. A drop can come
  with any of the other categories.
- **fail:** below the threshold, and not borderline.

| Result | `low` | `medium` | `high` |
|---|---|---|---|
| pass, no drop | `approve` (schema §5) | `approve` (schema §5) | `flag` (schema §5: human sign-off every time) |
| pass, with a drop | `flag` (schema §5: dropping results) | `flag` (schema §5: human on any drop) | `flag` (schema §5) |
| borderline | `flag` (schema §5) | `flag` (schema §5) | `flag` (schema §5) |
| fail, with a drop | `flag` (schema §5: dropping results) | `flag` (schema §5: human on any drop) | `flag` (schema §5) |
| fail, no drop | `block` (**Proposed**, [OQ-PO4](#open-questions)) | `block` (**Proposed**, [OQ-PO4](#open-questions)) | `block` or `flag` ([OQ-PO4](#open-questions)) |

A result that both fails and drops needs a human, because schema §5 requires
one for dropping results. Whether a drop always takes precedence is open
([OQ-PO2](#open-questions)).

## Inconclusive results

- An `inconclusive` verdict is never counted as a pass (schema §2).
- **Proposed:** aggregated results report `inconclusive` separately. A test
  case cannot reach "pass" on its `inconclusive` runs. Whether a given number
  of `inconclusive` runs makes a result borderline or failing depends on
  thresholds that are open ([OQ-PO3](#open-questions)).

## When no decision is made

- `failed`: `cost_total` reached `budget_limit` (schema §11).
- `invalidated`: the card changed during the attestation (schema §11).
- `cancelled`: **Proposed** ([OQ-F6](FLOW.md#open-questions)).

No decision is never an approval. **Proposed:** the adapters treat it as not
approved ([OQ-A9](ARCHITECTURE.md#open-questions)).

## Recording human decisions

- When a human resolves a flagged attestation, it gets a second decision
  record. The first record is never edited (schema §11).
- The second record has `decided_by` set to the reviewer's identifier, and
  `decided_at` (schema §11).
- **Proposed:** a human chooses `approve` or `block`
  ([OQ-D11](DATA_MODEL.md#open-questions)).
- The interface for recording it is not defined
  ([OQ-P2](API.md#open-questions)), and neither is who may resolve a `flag`
  ([OQ-PO7](#open-questions)).
- The attestation's signature does not cover this second decision
  ([OQ-A8](ARCHITECTURE.md#open-questions)).

## Thresholds

"Numeric pass thresholds are not defined yet. They are configured per
customer and per risk level. Treat the exact values as an open question; do
not invent numbers" (schema §5).

This document deliberately contains no threshold values
([OQ-PO1](#open-questions)). Thresholds apply to aggregated results
(schema §2). At what level thresholds apply is open
([OQ-PO6](#open-questions)).

## Policy configuration and policy_version

- `policy_version` identifies the version of the customer's policy
  configuration (thresholds per risk level) that produced the decision
  (schema §3).
- The Policy engine's decision (`decided_by` `"policy"`) stores
  `policy_version`, and the attestation signature covers it (schema §11). So an
  automatic decision can be traced to the exact configuration that produced
  it. What `policy_version` a human decision carries is open
  ([OQ-D11](DATA_MODEL.md#open-questions)).
- Where the configuration is stored, and in what format, is not defined. It is
  not one of the seven entities ([OQ-PO5](#open-questions)).

## Open questions

- **OQ-PO1 Numeric thresholds.** Thresholds are deliberately undefined. They
  are set per customer and per risk level (schema §5).
- **OQ-PO2 What counts as a drop.**
  - What is the baseline: the previous completed attestation of the same
    agent, or the last approved one?
  - Is a drop measured per test case or overall?
  - Schema §5 requires a human for "dropping results" at every risk level, and
    for "any drop" at `medium`. How do the two rules differ for `low`?
  - A result can fail and drop at the same time. **Proposed:** the drop takes
    precedence, so the outcome is `flag`, because schema §5 requires a human
    for dropping results.
- **OQ-PO3 What counts as borderline, and how `inconclusive` counts.**
  - How close to a threshold is borderline?
  - Do `inconclusive` verdicts count against a test case like `fail`, or are
    they weighed separately?
- **OQ-PO4 Failing results.** May the Policy engine `block` automatically on
  failing results that did not drop? **Proposed:** yes for `low` and `medium`.
  A `high` risk agent is never approved automatically: does it `block`
  automatically on failing results, or always `flag`?
- **OQ-PO5 The policy configuration.**
  - Where is the configuration stored, given it is not among the seven
    entities?
  - What format does `policy_version` have?
  - What happens when no configuration exists for a customer or risk level?
    **Proposed:** `flag`, never `approve`.
  - Every decision record needs a `policy_version`. What does a `flag` made
    because no configuration exists carry?
- **OQ-PO6 Aggregation level and probes.**
  - Are thresholds applied per test case (the level the signature uses), per
    skill, or per attestation?
  - How do probe results (`probe_undeclared`, `probe_injection`,
    `probe_failure`) count toward the decision?
- **OQ-PO7 Who may resolve a flag.** Who may resolve a `flag` or sign off on a
  high-risk agent, and how is that authorized? Building an identity system is
  out of scope (schema §10).
- **OQ-PO8 New or changed skills.** Schema §5 requires a human for new or
  changed skills. This document reads the contract approval as that human
  step. So once a human has approved the new contract, a `low` risk agent with
  a new skill can be approved automatically on its next attestation. Should
  the first attestation after a skill change also get `flag`?
