"""The Orchestrator and the attestation use case, on fakes."""

from __future__ import annotations

import threading
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest

from suncly.adapters.file_store import FileEvidenceStore
from suncly.core.attestation import AttestationService, AttestRequest, Services
from suncly.core.cards import agent_id_for_url
from suncly.core.config import Config
from suncly.domain.card import parse_agent_card
from suncly.domain.contract_file import parse_contract_file
from suncly.domain.errors import (
    ApprovalRequiredError,
    CardFetchError,
    CardNotAttestableError,
    CardNotParsableError,
    SigningError,
)
from suncly.domain.evidence import NotExecutedReason
from suncly.domain.models import AttestationStatus, ContractStatus, RunVerdict
from suncly.domain.transcript import RunOutcome
from suncly.ports.card_fetcher import FetchedCard
from suncly.ports.run_executor import RunJob, RunResult
from tests.fakes import (
    FailingSigner,
    FakeExecutor,
    MemoryReportWriter,
    MemorySigningKeys,
    StaticFetcher,
    card_text,
    make_transcript,
)

CARD_URL = "https://agent.example.com/.well-known/agent-card.json"
ServicesFactory = Callable[..., Services]


def request(**overrides: object) -> AttestRequest:
    base: dict[str, object] = {
        "card_url": CARD_URL,
        "sandbox_declared": True,
        "runs": 2,
        "approve_as": "tester",
    }
    base.update(overrides)
    return AttestRequest(**base)  # type: ignore[arg-type]


def test_plan_expands_test_cases_times_runs_with_deterministic_keys(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    executor = FakeExecutor(lambda job, n: RunResult(transcript=make_transcript(job)))
    card = card_text(
        skills=[
            {"id": "a", "name": "A", "description": "", "tags": ["t"], "examples": ["x", "y"]},
            {"id": "b", "name": "B", "description": "", "tags": ["t"], "examples": ["z"]},
        ]
    )
    services = services_factory(StaticFetcher({CARD_URL: card}), executor=executor)
    outcome = AttestationService(services).attest(request(runs=3))
    assert outcome.planned_runs == 9
    keys = {(j.test_case_id, j.attempt) for j in executor.jobs}
    assert len(keys) == 9 and {a for _, a in keys} == {1, 2, 3}
    assert all(j.sandbox_declared and j.protocol_version == "1.0" for j in executor.jobs)
    assert len({j.message_id for j in executor.jobs}) == 9
    assert outcome.attestation is not None and outcome.attestation.cost_total == Decimal(9)
    assert outcome.attestation.budget_limit == Decimal(18), "default budget is twice the plan"
    assert len(file_store.list_runs(outcome.attestation.id)) == 9


def test_a_runner_that_keeps_crashing_leaves_the_run_not_executed(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    executor = FakeExecutor(lambda job, n: RunResult(crashed=True, error="dead"))
    services = services_factory(StaticFetcher({CARD_URL: card_text()}), executor=executor)
    outcome = AttestationService(services).attest(request())
    assert outcome.kind == "completed", "an undecidable run is reported, not hidden"
    assert outcome.bundle is not None
    assert [n.reason for n in outcome.bundle.not_executed] == [NotExecutedReason.RUNNER_CRASHED] * 2
    assert all("dead" in n.detail for n in outcome.bundle.not_executed)
    assert outcome.attestation is not None
    assert file_store.list_runs(outcome.attestation.id) == []
    assert outcome.attestation.cost_total == Decimal(4), "two attempts each, all charged"


def test_a_withheld_transcript_is_not_recorded_and_not_retried(
    services_factory: ServicesFactory,
) -> None:
    executor = FakeExecutor(lambda job, n: RunResult(withheld=True, error="redaction failed"))
    services = services_factory(StaticFetcher({CARD_URL: card_text()}), executor=executor)
    outcome = AttestationService(services).attest(request())
    assert outcome.bundle is not None
    assert {n.reason for n in outcome.bundle.not_executed} == {NotExecutedReason.WITHHELD}
    assert all(n == 1 for n in executor.attempts.values())


def test_an_exploding_executor_counts_as_a_crash(services_factory: ServicesFactory) -> None:
    def explode(job: RunJob, n: int) -> RunResult:
        raise RuntimeError("kaboom")

    services = services_factory(
        StaticFetcher({CARD_URL: card_text()}), executor=FakeExecutor(explode)
    )
    outcome = AttestationService(services).attest(request())
    assert outcome.bundle is not None
    assert all("RuntimeError: kaboom" in n.detail for n in outcome.bundle.not_executed)


def test_card_changed_mid_run_invalidates_without_a_decision(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    fetcher = StaticFetcher({CARD_URL: [card_text(name="v1"), card_text(name="v2")]})
    services = services_factory(fetcher)
    outcome = AttestationService(services).attest(request())
    assert outcome.kind == "invalidated" and outcome.decision is None
    assert outcome.attestation is not None
    assert outcome.attestation.status is AttestationStatus.INVALIDATED
    assert outcome.attestation.signature is not None
    assert outcome.bundle is not None and outcome.bundle.card_recheck.outcome == "changed"
    assert file_store.list_decisions(outcome.attestation.id) == []
    assert len(file_store.list_runs(outcome.attestation.id)) == 2, "the runs stay as evidence"


def test_a_card_that_cannot_be_refetched_makes_the_attestation_failed(
    services_factory: ServicesFactory,
) -> None:
    class OnceFetcher(StaticFetcher):
        def fetch(self, url: str) -> FetchedCard:
            if self.fetches >= 1:
                self.fetches += 1
                raise CardFetchError("gone", "", "")
            return super().fetch(url)

    services = services_factory(OnceFetcher({CARD_URL: card_text()}))
    outcome = AttestationService(services).attest(request())
    assert outcome.kind == "failed" and outcome.decision is None
    assert outcome.bundle is not None and outcome.bundle.card_recheck.outcome == "unavailable"


def test_concurrency_is_bounded(services_factory: ServicesFactory, config: Config) -> None:
    active = 0
    peak = 0
    lock = threading.Lock()
    gate = threading.Event()

    def slow(job: RunJob, n: int) -> RunResult:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        gate.wait(0.05)
        with lock:
            active -= 1
        return RunResult(transcript=make_transcript(job))

    services = services_factory(StaticFetcher({CARD_URL: card_text()}), executor=FakeExecutor(slow))
    AttestationService(services).attest(request(runs=6))
    assert 1 <= peak <= config.concurrency


def test_unparsable_and_skill_less_cards_create_no_records(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    services = services_factory(StaticFetcher({CARD_URL: "not json"}))
    with pytest.raises(CardNotParsableError):
        AttestationService(services).attest(request())
    services = services_factory(StaticFetcher({CARD_URL: card_text(skills=[])}))
    with pytest.raises(CardNotAttestableError, match="no skills"):
        AttestationService(services).attest(request())
    assert list((file_store._root / "agents").iterdir()) == []


def test_signing_failure_leaves_the_attestation_undecided_as_completed_and_raises(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    keys = MemorySigningKeys(FailingSigner())
    services = services_factory(StaticFetcher({CARD_URL: card_text()}), keys=keys)
    with pytest.raises(SigningError, match="could not be signed"):
        AttestationService(services).attest(request())
    card_hash = parse_agent_card(card_text()).card_hash
    card_version = file_store.find_card_version(agent_id_for_url(CARD_URL), card_hash)
    assert card_version is not None
    attestations = file_store.list_attestations(card_version.id)
    assert len(attestations) == 1
    assert attestations[0].status is AttestationStatus.RUNNING and attestations[0].signature is None
    assert len(file_store.list_decisions(attestations[0].id)) == 1, "the decision stays recorded"


def test_the_approved_contract_is_reused_and_a_changed_card_needs_a_new_approval(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    services = services_factory(StaticFetcher({CARD_URL: card_text()}))
    first = AttestationService(services).attest(request())
    second = AttestationService(services).attest(request(approve_as=None))
    assert first.attestation is not None and second.attestation is not None
    assert first.attestation.contract_id == second.attestation.contract_id
    assert first.attestation.card_version_id == second.attestation.card_version_id
    changed = services_factory(StaticFetcher({CARD_URL: card_text(name="changed")}))
    with pytest.raises(ApprovalRequiredError):
        AttestationService(changed).attest(request(approve_as=None))
    third = AttestationService(changed).attest(request())
    assert (
        third.attestation is not None
        and third.attestation.card_version_id != first.attestation.card_version_id
    )
    third_contract = file_store.get_contract(third.attestation.contract_id)
    assert third_contract is not None and third_contract.version == 1


def test_export_draft_runs_nothing(services_factory: ServicesFactory) -> None:
    executor = FakeExecutor(lambda job, n: RunResult(transcript=make_transcript(job)))
    services = services_factory(StaticFetcher({CARD_URL: card_text()}), executor=executor)
    outcome = AttestationService(services).attest(request(export_draft=True, approve_as=None))
    assert outcome.kind == "draft_exported" and outcome.exported_contract_file
    assert executor.jobs == []
    contract_file = parse_contract_file(outcome.exported_contract_file)
    assert contract_file.test_cases[0].skill_id == "echo"


def test_a_contract_file_creates_a_new_version_and_old_approved_versions_are_superseded(
    services_factory: ServicesFactory, file_store: FileEvidenceStore
) -> None:
    services = services_factory(StaticFetcher({CARD_URL: card_text()}))
    first = AttestationService(services).attest(request())
    exported = (
        AttestationService(services).attest(request(export_draft=True)).exported_contract_file
    )
    assert exported is not None
    edited = parse_contract_file(
        exported.replace('"latency_limit_ms": 2000', '"latency_limit_ms": 1')
    )
    second = AttestationService(services).attest(request(contract_file=edited))
    assert first.attestation is not None and second.attestation is not None
    old = file_store.get_contract(first.attestation.contract_id)
    new = file_store.get_contract(second.attestation.contract_id)
    assert old is not None and old.status is ContractStatus.SUPERSEDED
    assert new is not None and new.version == 2
    assert second.bundle is not None and second.bundle.results[0].fail_count == 2, (
        "the 1 ms limit fails"
    )


def test_results_separate_inconclusive_from_pass(services_factory: ServicesFactory) -> None:
    def mixed(job: RunJob, n: int) -> RunResult:
        if job.attempt == 1:
            return RunResult(
                transcript=make_transcript(job, outcome=RunOutcome.UNREACHABLE, failure="x")
            )
        return RunResult(transcript=make_transcript(job))

    services = services_factory(
        StaticFetcher({CARD_URL: card_text()}), executor=FakeExecutor(mixed)
    )
    outcome = AttestationService(services).attest(request())
    assert outcome.bundle is not None
    result = outcome.bundle.results[0]
    assert (result.pass_count, result.fail_count, result.inconclusive_count) == (1, 0, 1)
    verdicts = {r.run.verdict for r in outcome.bundle.runs}
    assert verdicts == {RunVerdict.PASS, RunVerdict.INCONCLUSIVE}


def test_the_report_writer_receives_the_bundle(
    services_factory: ServicesFactory, tmp_path: Path
) -> None:
    services = services_factory(StaticFetcher({CARD_URL: card_text()}))
    outcome = AttestationService(services).attest(request())
    writer = services.report_writer
    assert isinstance(writer, MemoryReportWriter) and len(writer.bundles) == 1
    assert outcome.attestation is not None
    assert outcome.report_dir == tmp_path / "reports" / str(outcome.attestation.id)
