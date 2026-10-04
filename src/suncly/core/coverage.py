"""What was NOT tested (schema §8, DR-007).

Computed once from the evidence, so the report, the CLI and the API say the
same thing. The categories are the documents' proposal (ARCHITECTURE.md:
Report adapter; OQ-A11).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from suncly.domain.a2a import BINDING_JSONRPC, PROTOCOL_VERSION
from suncly.domain.card import ParsedCard
from suncly.domain.evidence import NotExecutedRun, NotTestedItem, TestCaseResult
from suncly.domain.models import TestCase, TestCaseKind


def not_tested(
    *,
    parsed: ParsedCard,
    test_cases: Sequence[TestCase],
    results: Sequence[TestCaseResult],
    not_executed: Sequence[NotExecutedRun],
    planned_runs: int | None,
    target_url: str,
    sandbox_declared: bool,
) -> list[NotTestedItem]:
    items: list[NotTestedItem] = []
    card = parsed.card

    covered = {tc.skill_id for tc in test_cases if tc.kind is TestCaseKind.SKILL}
    for skill in card.skills:
        if skill.id not in covered:
            items.append(
                NotTestedItem(
                    category="skill without test case",
                    detail=f"skill '{skill.id}' has no test case; invariant 1 (one test case per "
                    "declared skill) is not satisfied for it",
                )
            )

    if not_executed:
        by_reason = Counter(item.reason.value for item in not_executed)
        planned = f" of {planned_runs} planned" if planned_runs is not None else ""
        items.append(
            NotTestedItem(
                category="runs never executed",
                detail=f"{len(not_executed)} run(s){planned} were never executed: "
                + ", ".join(
                    f"{count} because of {reason}" for reason, count in sorted(by_reason.items())
                ),
            )
        )

    inconclusive = sum(result.inconclusive_count for result in results)
    if inconclusive:
        items.append(
            NotTestedItem(
                category="inconclusive runs",
                detail=f"{inconclusive} run(s) ended inconclusive; they count neither as pass "
                "nor as fail",
            )
        )

    caps = card.capabilities
    declared = [
        name
        for name, value in (
            ("streaming", caps.streaming),
            ("pushNotifications", caps.push_notifications),
            ("extendedAgentCard", caps.extended_agent_card),
        )
        if value
    ]
    if caps.extensions:
        declared.append(f"extensions ({len(caps.extensions)})")
    for name in declared:
        items.append(
            NotTestedItem(
                category="declared capability not exercised",
                detail=f"the card declares {name}; no test case exercises it",
            )
        )

    for interface in card.supported_interfaces:
        if interface.url != target_url or interface.protocol_binding != BINDING_JSONRPC:
            items.append(
                NotTestedItem(
                    category="interface not used",
                    detail=f"{interface.protocol_binding} {interface.protocol_version} at "
                    f"{interface.url} was not used; only {BINDING_JSONRPC} {PROTOCOL_VERSION} at "
                    f"{target_url} was",
                )
            )

    probe_kinds = {tc.kind for tc in test_cases if tc.kind is not TestCaseKind.SKILL}
    if not probe_kinds:
        items.append(
            NotTestedItem(
                category="probes",
                detail="no probe_undeclared, probe_injection or probe_failure test cases exist yet "
                "(stage 4)",
            )
        )

    items.append(
        NotTestedItem(
            category="semantic correctness",
            detail="Layer 1 checks structure, state, output modes and latency; whether the "
            "content of each answer is correct needs Layer 2 (stage 4)",
        )
    )

    if sandbox_declared:
        items.append(
            NotTestedItem(
                category="production endpoint",
                detail=f"tests ran against the declared sandbox or dry-run endpoint {target_url}; "
                "the production endpoint itself was not tested (DR-006)",
            )
        )

    missing = parsed.missing_required_fields()
    if missing:
        items.append(
            NotTestedItem(
                category="card observation",
                detail="the card omits fields the A2A specification marks REQUIRED: "
                + ", ".join(missing),
            )
        )
    return items
