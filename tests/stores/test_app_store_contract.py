"""One contract suite for every application store: in memory and on Postgres."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from suncly.adapters.memory_app_store import MemoryApplicationStore
from suncly.domain.billing import MeterReport, ProviderEvent, Subscription, SubscriptionStatus
from suncly.domain.errors import ConflictError, JobError
from suncly.domain.jobs import AttemptOutcome, Job, JobKind, JobStatus, OutboxMessage
from suncly.domain.ledger import (
    Reservation,
    ReservationState,
    SettlementState,
    SpendingLimit,
    UsageEvent,
    UsageOperation,
    UsageOutcome,
)
from suncly.domain.models import (
    Agent,
    Attestation,
    AttestationStatus,
    AttestationTrigger,
    CardVersion,
    Contract,
    ContractStatus,
    RiskLevel,
    TestCase,
    TestCaseKind,
)
from suncly.domain.policy import (
    InconclusiveHandling,
    PolicyConfiguration,
    PolicyRecord,
    RiskThresholds,
)
from suncly.domain.tenancy import (
    AgentRegistration,
    CredentialReference,
    Membership,
    Organization,
    Role,
)
from suncly.ports.app_store import (
    ApplicationStore,
    AttestationMeta,
    DecisionNote,
    SigningKeyRecord,
)
from suncly.ports.store import EvidenceStore

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
STORE_KINDS = ["memory"] + (["postgres"] if os.environ.get("DATABASE_URL") else [])


@pytest.fixture(params=STORE_KINDS)
def stores(
    request: pytest.FixtureRequest, tmp_path: object
) -> Iterator[tuple[ApplicationStore, EvidenceStore | None]]:
    if request.param == "memory":
        yield MemoryApplicationStore(), None
        return
    migrated = request.getfixturevalue("migrated_database")
    from suncly.adapters.postgres.app_store import PostgresApplicationStore
    from suncly.adapters.postgres.store import PostgresEvidenceStore

    app = PostgresApplicationStore(migrated)
    core = PostgresEvidenceStore(migrated)
    try:
        yield app, core
    finally:
        app.close()
        core.close()


def organization(slug: str | None = None, max_jobs: int = 2) -> Organization:
    return Organization(
        id=uuid4(),
        slug=slug or f"org-{uuid4().hex[:8]}",
        name="Org",
        created_at=NOW,
        max_concurrent_jobs=max_jobs,
    )


def job(org: Organization, logical: UUID | None = None, **overrides: object) -> Job:
    data: dict[str, object] = {
        "id": uuid4(),
        "organization_id": org.id,
        "kind": JobKind.ATTESTATION,
        "logical_id": logical or uuid4(),
        "status": JobStatus.QUEUED,
        "created_at": NOW,
        "run_after": NOW,
        "max_attempts": 3,
    }
    data.update(overrides)
    return Job.model_validate(data)


def core_agent(core: EvidenceStore | None) -> UUID:
    """A core agent record exists in Postgres (the registration references it)."""
    agent_id = uuid4()
    if core is not None:
        core.add_agent(Agent(id=agent_id, name="A", owner="o", risk_level=RiskLevel.LOW))
    return agent_id


def core_attestation(core: EvidenceStore | None, agent_id: UUID) -> UUID:
    attestation_id = uuid4()
    if core is None:
        return attestation_id
    cv = CardVersion(
        id=uuid4(), agent_id=agent_id, card_hash="sha256:x", raw_json="{}", fetched_at=NOW
    )
    core.add_card_version(cv)
    contract = Contract(
        id=uuid4(), card_version_id=cv.id, version=1, status=ContractStatus.DRAFT, created_at=NOW
    )
    tc = TestCase(
        id=uuid4(),
        contract_id=contract.id,
        skill_id="s",
        input={"text": "x"},
        criteria={},
        kind=TestCaseKind.SKILL,
    )
    core.add_contract(contract, [tc])
    core.approve_contract(contract.id, "reviewer", NOW)
    core.add_attestation(
        Attestation(
            id=attestation_id,
            contract_id=contract.id,
            card_version_id=cv.id,
            trigger=AttestationTrigger.MANUAL,
            status=AttestationStatus.QUEUED,
            started_at=NOW,
            budget_limit=Decimal(1),
            cost_total=Decimal(0),
        )
    )
    return attestation_id


# -- tenancy ----------------------------------------------------------------------


def test_organizations_memberships_and_registrations_are_scoped(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, core = stores
    org_a, org_b = organization(), organization()
    store.add_organization(org_a)
    store.add_organization(org_b)
    with pytest.raises(ConflictError):
        store.add_organization(org_a.model_copy(update={"id": uuid4()}))
    assert store.get_organization_by_slug(org_a.slug) == org_a
    store.add_membership(
        Membership(
            id=uuid4(),
            organization_id=org_a.id,
            subject="alice",
            email="a@x",
            role=Role.ADMINISTRATOR,
            created_at=NOW,
        )
    )
    with pytest.raises(ConflictError):
        store.add_membership(
            Membership(
                id=uuid4(),
                organization_id=org_a.id,
                subject="alice",
                role=Role.VIEWER,
                created_at=NOW,
            )
        )
    assert store.get_membership(org_a.id, "alice") is not None
    assert store.get_membership(org_b.id, "alice") is None
    assert [o.id for o in store.list_organizations_for_subject("alice")] == [org_a.id]

    agent_id = core_agent(core)
    registration = AgentRegistration(
        id=uuid4(),
        organization_id=org_a.id,
        agent_id=agent_id,
        name="Agent",
        card_url="https://a.example/.well-known/agent-card.json",
        risk_level=RiskLevel.LOW,
        owner="team",
        sandbox_declared=True,
        credential=CredentialReference(provider="none"),
        created_at=NOW,
        created_by="alice",
    )
    store.add_registration(registration)
    with pytest.raises(ConflictError):
        store.add_registration(registration.model_copy(update={"id": uuid4()}))
    assert store.get_registration(org_a.id, registration.id) == registration
    assert store.get_registration(org_b.id, registration.id) is None, "other tenants never see it"
    assert store.get_registration_by_agent(agent_id) == registration
    archived = store.archive_registration(org_a.id, registration.id, NOW)
    assert archived is not None and archived.archived_at == NOW
    assert store.archive_registration(org_b.id, registration.id, NOW) is None


def test_attestation_meta_policies_and_notes(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, core = stores
    org = organization()
    store.add_organization(org)
    agent_id = core_agent(core)
    registration = AgentRegistration(
        id=uuid4(),
        organization_id=org.id,
        agent_id=agent_id,
        name="A",
        card_url="https://a.example/c.json",
        risk_level=RiskLevel.HIGH,
        owner="o",
        sandbox_declared=True,
        credential=CredentialReference(provider="none"),
        created_at=NOW,
        created_by="alice",
    )
    store.add_registration(registration)
    attestation_id = core_attestation(core, agent_id)
    meta = AttestationMeta(
        attestation_id=attestation_id,
        organization_id=org.id,
        registration_id=registration.id,
        created_by="alice",
        runs_planned=4,
        runs_per_test_case=2,
        suite_version="1",
        contract_content_hash="sha256:c",
        judge_version="layer1/1",
    )
    store.add_attestation_meta(meta)
    with pytest.raises(ConflictError):
        store.add_attestation_meta(meta)
    updated = meta.model_copy(
        update={"issued_at": NOW, "expires_at": NOW + timedelta(days=30), "payload_version": 2}
    )
    store.update_attestation_meta(updated)
    assert store.get_attestation_meta(attestation_id) == updated
    assert store.list_attestation_meta(org.id, registration.id) == [updated]

    config = PolicyConfiguration(
        policy_version="v1",
        thresholds={RiskLevel.LOW: RiskThresholds(min_pass_ratio=0.9)},
        inconclusive=InconclusiveHandling.COUNT_AS_FAIL,
    )
    record = PolicyRecord(
        id=uuid4(),
        organization_id=org.id,
        policy_version="v1",
        content_hash=config.content_hash(),
        configuration=config,
        created_at=NOW,
        created_by="alice",
    )
    store.add_policy(record)
    with pytest.raises(ConflictError):
        store.add_policy(record.model_copy(update={"id": uuid4()}))
    assert store.list_policies(org.id) == [record]
    assert store.get_policy(organization().id, record.id) is None

    if core is not None:
        from suncly.domain.models import Decision, DecisionOutcome

        core.update_attestation(
            core.get_attestation(attestation_id).model_copy(
                update={"status": AttestationStatus.RUNNING}
            )
        )  # type: ignore[union-attr]
        decision = Decision(
            id=uuid4(),
            attestation_id=attestation_id,
            outcome=DecisionOutcome.FLAG,
            policy_version="v1",
            decided_by="policy",
            decided_at=NOW,
        )
        core.add_decision(decision)
        decision_id = decision.id
    else:
        decision_id = uuid4()
    note = DecisionNote(
        decision_id=decision_id,
        organization_id=org.id,
        attestation_id=attestation_id,
        reviewer_subject="alice",
        rationale="because",
        created_at=NOW,
    )
    store.add_decision_note(note)
    with pytest.raises(ConflictError):
        store.add_decision_note(note)
    assert store.list_decision_notes(attestation_id) == [note]


# -- jobs -------------------------------------------------------------------------


def test_jobs_are_claimed_atomically_within_the_tenant_limit(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization(max_jobs=1)
    store.add_organization(org)
    first, second = job(org), job(org, created_at=NOW + timedelta(seconds=1))
    store.enqueue_job(
        first,
        [
            OutboxMessage(
                id=uuid4(),
                organization_id=org.id,
                topic="t",
                dedup_key=f"k-{first.id}",
                payload={},
                created_at=NOW,
            )
        ],
    )
    store.enqueue_job(second)
    with pytest.raises(ConflictError, match="already"):
        store.enqueue_job(job(org, logical=first.logical_id))
    assert store.find_job(JobKind.ATTESTATION, first.logical_id) is not None
    assert len(store.claim_outbox(10, NOW)) == 1

    claimed = store.claim_job("w1", NOW, 30.0, [JobKind.ATTESTATION])
    assert claimed is not None
    claimed_job, attempt = claimed
    assert claimed_job.id == first.id and claimed_job.status is JobStatus.RUNNING
    assert claimed_job.attempts == 1 and attempt.number == 1 and claimed_job.lease_owner == "w1"
    assert store.claim_job("w2", NOW, 30.0, [JobKind.ATTESTATION]) is None, "tenant limit is 1"
    assert store.claim_job("w2", NOW, 30.0, [JobKind.REEVALUATION]) is None

    assert store.heartbeat(first.id, attempt.id, NOW + timedelta(seconds=10), 30.0) is not None
    store.update_progress(first.id, {"phase": "running", "recorded": 1})
    assert store.get_job(first.id).progress == {"phase": "running", "recorded": 1}  # type: ignore[union-attr]

    finished = store.finish_attempt(
        first.id, attempt.id, AttemptOutcome.SUCCEEDED, NOW + timedelta(seconds=20), None, None
    )
    assert (
        finished.status is JobStatus.SUCCEEDED
        and finished.lease_owner is None
        and finished.finished_at is not None
    )
    with pytest.raises(JobError):
        store.finish_attempt(first.id, attempt.id, AttemptOutcome.SUCCEEDED, NOW, None, None)
    assert store.heartbeat(first.id, attempt.id, NOW, 30.0) is None

    second_claim = store.claim_job("w2", NOW + timedelta(seconds=21), 30.0, [JobKind.ATTESTATION])
    assert second_claim is not None and second_claim[0].id == second.id
    assert [j.id for j in store.list_jobs(org.id, JobStatus.RUNNING)] == [second.id]


def test_concurrent_claimers_never_take_the_same_job(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization(max_jobs=8)
    store.add_organization(org)
    for i in range(6):
        store.enqueue_job(job(org, created_at=NOW + timedelta(seconds=i)))
    taken: list[UUID] = []
    lock = threading.Lock()

    def worker(name: str) -> None:
        while True:
            claimed = store.claim_job(name, NOW + timedelta(minutes=1), 30.0, [JobKind.ATTESTATION])
            if claimed is None:
                return
            with lock:
                taken.append(claimed[0].id)

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(taken) == 6 and len(set(taken)) == 6


def test_failed_attempts_retry_with_backoff_until_max_then_fail(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization()
    store.add_organization(org)
    j = job(org, max_attempts=2)
    store.enqueue_job(j)
    claimed = store.claim_job("w", NOW, 30.0, [JobKind.ATTESTATION])
    assert claimed is not None
    later = NOW + timedelta(seconds=30)
    retried = store.finish_attempt(j.id, claimed[1].id, AttemptOutcome.FAILED, NOW, "boom", later)
    assert (
        retried.status is JobStatus.QUEUED
        and retried.run_after == later
        and retried.last_error == "boom"
    )
    assert store.claim_job("w", NOW + timedelta(seconds=5), 30.0, [JobKind.ATTESTATION]) is None, (
        "backoff"
    )
    claimed = store.claim_job("w", later, 30.0, [JobKind.ATTESTATION])
    assert claimed is not None and claimed[0].attempts == 2
    failed = store.finish_attempt(
        j.id, claimed[1].id, AttemptOutcome.FAILED, later, "boom again", None
    )
    assert failed.status is JobStatus.FAILED and failed.finished_at is not None
    assert [a.outcome for a in store.list_attempts(j.id)] == [
        AttemptOutcome.FAILED,
        AttemptOutcome.FAILED,
    ]


def test_expired_leases_are_recovered_and_requeued(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization()
    store.add_organization(org)
    j = job(org, max_attempts=2)
    store.enqueue_job(j)
    claimed = store.claim_job("w", NOW, 10.0, [JobKind.ATTESTATION])
    assert claimed is not None
    assert store.recover_expired_leases(NOW + timedelta(seconds=5)) == []
    recovered = store.recover_expired_leases(NOW + timedelta(seconds=11))
    assert [r.id for r in recovered] == [j.id] and recovered[0].status is JobStatus.QUEUED
    assert store.list_attempts(j.id)[0].outcome is AttemptOutcome.LOST
    assert store.heartbeat(j.id, claimed[1].id, NOW + timedelta(seconds=12), 10.0) is None, (
        "the old worker lost its lease"
    )
    with pytest.raises(JobError):
        store.finish_attempt(j.id, claimed[1].id, AttemptOutcome.SUCCEEDED, NOW, None, None)
    again = store.claim_job("w2", NOW + timedelta(seconds=12), 10.0, [JobKind.ATTESTATION])
    assert again is not None and again[0].attempts == 2
    lost_again = store.recover_expired_leases(NOW + timedelta(seconds=30))
    assert lost_again[0].status is JobStatus.FAILED


def test_cancellation_of_queued_and_running_jobs(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization(max_jobs=4)
    store.add_organization(org)
    queued, running = job(org), job(org, created_at=NOW - timedelta(seconds=1))
    store.enqueue_job(queued)
    store.enqueue_job(running)
    claimed = store.claim_job("w", NOW, 30.0, [JobKind.ATTESTATION])
    assert claimed is not None and claimed[0].id == running.id
    cancelled = store.request_cancel(queued.id, NOW)
    assert cancelled is not None and cancelled.status is JobStatus.CANCELLED
    requested = store.request_cancel(running.id, NOW)
    assert (
        requested is not None
        and requested.status is JobStatus.RUNNING
        and requested.cancel_requested
    )
    seen = store.heartbeat(running.id, claimed[1].id, NOW, 30.0)
    assert seen is not None and seen.cancel_requested, "the worker sees the request on heartbeat"
    done = store.finish_attempt(
        running.id, claimed[1].id, AttemptOutcome.CANCELLED, NOW, None, None
    )
    assert done.status is JobStatus.CANCELLED
    assert store.request_cancel(uuid4(), NOW) is None


# -- outbox and ledger ------------------------------------------------------------


def test_outbox_deduplicates_and_marks_delivery(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization()
    store.add_organization(org)
    message = OutboxMessage(
        id=uuid4(),
        organization_id=org.id,
        topic="usage.settled",
        dedup_key="u-1",
        payload={"n": 1},
        created_at=NOW,
    )
    assert store.add_outbox(message) is True
    assert store.add_outbox(message.model_copy(update={"id": uuid4()})) is False
    store.mark_outbox(message.id, NOW, "network")
    pending = [m for m in store.claim_outbox(100, NOW) if m.organization_id == org.id]
    assert len(pending) == 1 and pending[0].attempts == 1 and pending[0].last_error == "network"
    store.mark_outbox(message.id, NOW, None)
    assert [m for m in store.claim_outbox(100, NOW) if m.organization_id == org.id] == []


def usage(org: Organization, **overrides: object) -> UsageEvent:
    data: dict[str, object] = {
        "id": uuid4(),
        "organization_id": org.id,
        "attestation_id": None,
        "logical_run_id": None,
        "execution_attempt_id": None,
        "reservation_id": None,
        "provider": "suncly-runner",
        "provider_request_id": None,
        "model": None,
        "operation": UsageOperation.AGENT_CALL,
        "outcome": UsageOutcome.SETTLED,
        "measured": {"calls": 1},
        "currency": "EUR",
        "provider_cost_minor": 0,
        "price_table_version": "test",
        "billable_minor": 100,
        "allowance_minor": 0,
        "settlement": SettlementState.PENDING,
        "recorded_at": NOW,
    }
    data.update(overrides)
    return UsageEvent.model_validate(data)


def test_ledger_reservations_enforce_the_hard_limit_atomically(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization()
    store.add_organization(org)
    store.add_spending_limit(
        SpendingLimit(
            organization_id=org.id,
            currency="EUR",
            period_limit_minor=500,
            set_by="alice",
            set_at=NOW,
        )
    )
    store.add_spending_limit(
        SpendingLimit(
            organization_id=org.id,
            currency="EUR",
            period_limit_minor=300,
            set_by="alice",
            set_at=NOW + timedelta(seconds=1),
        )
    )
    assert store.get_spending_limit(org.id).period_limit_minor == 300  # type: ignore[union-attr]
    store.add_usage_event(usage(org, billable_minor=100, allowance_minor=40))
    store.add_usage_event(
        usage(org, provider="anthropic", provider_request_id="req-1", billable_minor=0)
    )
    with pytest.raises(ConflictError):
        store.add_usage_event(usage(org, provider="anthropic", provider_request_id="req-1"))

    def reservation(amount: int) -> Reservation:
        return Reservation(
            id=uuid4(),
            organization_id=org.id,
            attestation_id=None,
            amount_minor=amount,
            currency="EUR",
            state=ReservationState.HELD,
            created_at=NOW,
        )

    assert store.try_reserve(reservation(150), 300, None) is True
    assert store.try_reserve(reservation(100), 300, None) is False, (
        "100 settled + 150 held + 100 > 300"
    )
    assert store.try_reserve(reservation(50), 300, None) is True
    totals = store.ledger_totals(org.id, None)
    assert (totals.settled_minor, totals.reserved_minor, totals.allowance_used_minor) == (
        100,
        200,
        40,
    )
    assert totals.pending_report_minor == 60, "overage of the one billable line"

    successes: list[bool] = []
    lock = threading.Lock()

    def racer() -> None:
        ok = store.try_reserve(reservation(100), 400, None)
        with lock:
            successes.append(ok)

    threads = [threading.Thread(target=racer) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert successes.count(True) == 1, "only one of five concurrent reservations fits"

    held = [r for r in store.list_reservations(org.id) if r.state is ReservationState.HELD]
    closed = store.close_reservation(held[0].id, 120, NOW, released=False)
    assert closed.state is ReservationState.SETTLED and closed.settled_minor == 120
    with pytest.raises(ConflictError):
        store.close_reservation(held[0].id, 0, NOW, released=True)
    released = store.close_reservation(held[1].id, 0, NOW, released=True)
    assert released.state is ReservationState.RELEASED
    assert store.try_reserve(reservation(10), None, None) is True, "no limit set means no check"

    event = usage(org, billable_minor=70)
    store.add_usage_event(event)
    report = MeterReport(
        usage_event_id=event.id, provider="stripe", identifier=str(event.id), reported_at=NOW
    )
    assert store.mark_usage_reported(report) is True
    assert store.mark_usage_reported(report) is False, "deduplicated by usage event id"
    assert all(u.id != event.id for u in store.list_unreported_usage(100))


def test_billing_records_subscriptions_and_dedupes_provider_events(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    org = organization()
    store.add_organization(org)
    subscription = Subscription(
        organization_id=org.id,
        plan_id="team",
        status=SubscriptionStatus.ACTIVE,
        provider_customer_id="cus_1",
        updated_at=NOW,
    )
    store.upsert_subscription(subscription)
    store.upsert_subscription(
        subscription.model_copy(update={"status": SubscriptionStatus.PAST_DUE})
    )
    assert store.get_subscription(org.id).status is SubscriptionStatus.PAST_DUE  # type: ignore[union-attr]
    assert store.find_subscription_by_customer("stripe", "cus_1") is not None
    event = ProviderEvent(
        provider="stripe",
        event_id="evt_1",
        event_type="invoice.paid",
        provider_created_at=NOW,
        received_at=NOW,
        processed=False,
    )
    assert store.record_provider_event(event) is True
    assert store.record_provider_event(event) is False
    store.mark_provider_event("stripe", "evt_1", "ok")


def test_signing_keys_are_registered_and_revoked_once(
    stores: tuple[ApplicationStore, EvidenceStore | None],
) -> None:
    store, _ = stores
    record = SigningKeyRecord(
        key_id=f"ed25519-{uuid4().hex[:16]}",
        issuer="suncly-test",
        public_key=b"\x01" * 32,
        created_at=NOW,
    )
    store.add_signing_key(record)
    with pytest.raises(ConflictError):
        store.add_signing_key(record)
    assert store.get_signing_key(record.key_id) == record
    revoked = store.revoke_signing_key(record.key_id, NOW, "rotated")
    assert (
        revoked is not None and revoked.revoked_at == NOW and revoked.revocation_reason == "rotated"
    )
    again = store.revoke_signing_key(record.key_id, NOW + timedelta(days=1), "again")
    assert again is not None and again.revoked_at == NOW, "the first revocation stands"
    assert store.revoke_signing_key("missing", NOW, "x") is None
    assert record.key_id in {k.key_id for k in store.list_signing_keys()}
