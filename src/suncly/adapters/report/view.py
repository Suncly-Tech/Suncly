"""The report's content, computed once and rendered as Markdown, HTML and terminal text.

Every renderer shows the same facts: verdict counts per test case (never a
combined score), the decision with its explanation, the signature and how to
verify it, what was NOT tested, and the proposals in effect.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from suncly.core.policy_engine import FLAG_EXPLANATION
from suncly.domain.evidence import EvidenceBundle
from suncly.domain.models import AttestationStatus

HASH_SCHEME = "SHA-256 of the RFC 8785 (JCS) form of the card without the `signatures` field"


@dataclass(frozen=True)
class TestCaseRow:
    test_case_id: str
    skill_id: str
    kind: str
    input_preview: str
    pass_count: int
    fail_count: int
    inconclusive_count: int
    criteria: dict[str, Any]


@dataclass(frozen=True)
class RunRow:
    run_id: str
    test_case_id: str
    skill_id: str
    attempt: int
    verdict: str
    latency_ms: int | None
    outcome: str
    summary: str
    checks: list[dict[str, Any]]
    transcript_file: str


@dataclass(frozen=True)
class ReportView:
    title: str
    agent_name: str
    status: str
    decision_line: str
    decision_detail: str
    verdict_rows: list[TestCaseRow]
    runs: list[RunRow]
    attestation: dict[str, str]
    card: dict[str, str]
    contract: dict[str, str]
    signature: dict[str, str]
    recheck: dict[str, str]
    not_tested: list[tuple[str, str]]
    not_executed: list[str]
    proposals: list[str]
    generated_at: str
    pass_total: int = 0
    fail_total: int = 0
    inconclusive_total: int = 0
    notes: list[str] = field(default_factory=list)


def _stamp(value: datetime | None) -> str:
    return value.isoformat(timespec="seconds") if value else "-"


def _preview(text: str, limit: int = 80) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def decision_lines(bundle: EvidenceBundle) -> tuple[str, str]:
    """The decision sentence shown everywhere, and one more line of detail."""
    status = bundle.attestation.status
    decision = bundle.policy_decision
    if decision is not None:
        return f"Decision: {decision.outcome.value}. {FLAG_EXPLANATION}", (
            f"Recorded by '{decision.decided_by}' at {_stamp(decision.decided_at)} under "
            f"policy_version '{decision.policy_version}'."
        )
    if status is AttestationStatus.FAILED:
        return "No decision: the attestation ended failed.", (
            "The budget cap stopped it, or the card could not be re-fetched at the end "
            f"({bundle.card_recheck.outcome}). No decision is made for a failed attestation "
            "(schema §11)."
        )
    if status is AttestationStatus.INVALIDATED:
        return "No decision: the attestation ended invalidated.", (
            "The Agent Card changed while the attestation ran; a new contract needs approval "
            "(schema §11)."
        )
    return f"No decision yet: the attestation is {status.value}.", ""


def build_view(bundle: EvidenceBundle) -> ReportView:
    attestation = bundle.attestation
    card = bundle.parsed_card.card
    decision_line, decision_detail = decision_lines(bundle)
    by_id = {tc.id: tc for tc in bundle.test_cases}

    verdict_rows: list[TestCaseRow] = []
    for result in bundle.results:
        tc = by_id[result.test_case_id]
        raw_input = tc.input.get("text") or str(tc.input.get("parts"))
        verdict_rows.append(
            TestCaseRow(
                test_case_id=str(tc.id),
                skill_id=tc.skill_id or "-",
                kind=tc.kind.value,
                input_preview=_preview(str(raw_input)),
                pass_count=result.pass_count,
                fail_count=result.fail_count,
                inconclusive_count=result.inconclusive_count,
                criteria=dict(tc.criteria),
            )
        )

    runs: list[RunRow] = []
    for evidence in bundle.runs:
        run = evidence.run
        judgement = evidence.document.get("judgement") or {}
        transcript = evidence.document.get("transcript") or {}
        run_tc = by_id.get(run.test_case_id)
        runs.append(
            RunRow(
                run_id=str(run.id),
                test_case_id=str(run.test_case_id),
                skill_id=(run_tc.skill_id if run_tc and run_tc.skill_id else "-"),
                attempt=run.attempt,
                verdict=run.verdict.value,
                latency_ms=run.latency_ms,
                outcome=str(transcript.get("outcome", "-")),
                summary=str(judgement.get("summary", "")),
                checks=list(judgement.get("checks") or []),
                transcript_file=f"transcripts/{run.id}.json",
            )
        )

    interface = bundle.parsed_card.card.supported_interfaces[0]
    signature = {
        "signing_key_id": attestation.signing_key_id or "-",
        "signature": attestation.signature or "-",
        "public_key": bundle.signer_public_key or "-",
        "payload": "attestation id, card_hash, contract id and version, per-test-case results, "
        "the hash of every transcript, the decision outcome and policy_version (schema §11)",
        "verify": f"suncly verify suncly-reports/{attestation.id}",
    }
    notes = [
        (
            "Verdict counts are shown per test case. Suncly never combines them into a single "
            "score, and inconclusive runs are never counted as passes."
        ),
    ]
    if attestation.status is AttestationStatus.COMPLETED:
        notes.append(
            "Exit code 0 and status completed mean the attestation ran to the end and was signed. "
            "They do not mean the agent was approved."
        )
    return ReportView(
        title=f"Suncly attestation report: {card.name}",
        agent_name=card.name,
        status=attestation.status.value,
        decision_line=decision_line,
        decision_detail=decision_detail,
        verdict_rows=verdict_rows,
        runs=runs,
        attestation={
            "id": str(attestation.id),
            "status": attestation.status.value,
            "trigger": attestation.trigger.value,
            "started_at": _stamp(attestation.started_at),
            "finished_at": _stamp(attestation.finished_at),
            "budget_limit": f"{attestation.budget_limit} attempt(s)",
            "cost_total": f"{attestation.cost_total} attempt(s)",
            "planned_runs": str(bundle.planned_runs) if bundle.planned_runs is not None else "-",
            "recorded_runs": str(len(bundle.runs)),
            "not_executed": str(len(bundle.not_executed)),
        },
        card={
            "url": bundle.card_url or "-",
            "name": card.name,
            "version": card.version or "-",
            "card_hash": bundle.card_version.card_hash,
            "hash_scheme": HASH_SCHEME,
            "fetched_at": _stamp(bundle.card_version.fetched_at),
            "interface": (
                f"{interface.protocol_binding} {interface.protocol_version} at {interface.url}"
            ),
            "skills": ", ".join(card.skill_ids()) or "-",
            "sandbox": "declared by the user with --sandbox (DR-006)"
            if bundle.sandbox_declared
            else "not declared",
            "agent_id": str(bundle.agent.id),
            "owner": bundle.agent.owner,
            "risk_level": bundle.agent.risk_level.value,
        },
        contract={
            "id": str(bundle.contract.id),
            "version": str(bundle.contract.version),
            "status": bundle.contract.status.value,
            "approved_by": bundle.contract.approved_by or "-",
            "approved_at": _stamp(bundle.contract.approved_at),
            "source": bundle.drafter_name or "-",
            "test_cases": str(len(bundle.test_cases)),
        },
        signature=signature,
        recheck={
            "outcome": bundle.card_recheck.outcome,
            "detail": bundle.card_recheck.detail or "-",
        },
        not_tested=[(item.category, item.detail) for item in bundle.not_tested],
        not_executed=[
            f"test case {item.test_case_id} attempt {item.attempt}: {item.reason.value}"
            + (f" ({item.detail})" if item.detail else "")
            for item in bundle.not_executed
        ],
        proposals=list(bundle.proposals),
        generated_at=_stamp(bundle.generated_at),
        pass_total=sum(r.pass_count for r in bundle.results),
        fail_total=sum(r.fail_count for r in bundle.results),
        inconclusive_total=sum(r.inconclusive_count for r in bundle.results),
        notes=notes,
    )
