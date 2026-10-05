"""The usage ledger, reservations, hard limits, entitlements and Stripe test-mode billing."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from suncly.adapters.memory_app_store import MemoryApplicationStore
from suncly.adapters.stripe_billing import (
    FakeBillingProvider,
    StripeBillingProvider,
    sign_webhook_payload,
    webhook_event,
)
from suncly.core.billing import BillingService
from suncly.core.pricing import TEST_PLANS, TEST_PRICE_TABLE
from suncly.core.usage import UsageService
from suncly.domain.billing import Subscription, SubscriptionStatus
from suncly.domain.errors import BillingError, QuotaError
from suncly.domain.ledger import (
    Money,
    ReservationState,
    SettlementState,
    UsageOperation,
    UsageOutcome,
    micro_to_minor,
)
from suncly.domain.tenancy import Organization
from suncly.ports.model import ModelUsage
from tests.fakes import FakeClock, SeqIds

NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


World = tuple[
    MemoryApplicationStore,
    UsageService,
    BillingService,
    FakeBillingProvider,
    Organization,
    FakeClock,
]


@pytest.fixture
def world() -> World:
    store = MemoryApplicationStore()
    clock = FakeClock(NOW)
    provider = FakeBillingProvider()
    usage = UsageService(store, clock, SeqIds(), TEST_PRICE_TABLE, TEST_PLANS)
    billing = BillingService(
        store, provider, clock, TEST_PLANS, "https://s", "https://c", "https://p"
    )
    org = Organization(id=uuid4(), slug="acme", name="Acme", created_at=NOW)
    store.add_organization(org)
    return store, usage, billing, provider, org, clock


def subscribe(
    store: MemoryApplicationStore,
    org: Organization,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
) -> None:
    store.upsert_subscription(
        Subscription(
            organization_id=org.id,
            plan_id="pilot",
            status=status,
            provider_customer_id="cus_123",
            current_period_start=NOW - timedelta(days=1),
            provider_updated_at=NOW - timedelta(days=1),
            updated_at=NOW,
        )
    )


def test_money_is_integer_minor_units() -> None:
    assert (
        Money(amount_minor=150, currency="EUR") + Money(amount_minor=50, currency="EUR")
    ).amount_minor == 200
    assert Money(amount_minor=150, currency="EUR").as_decimal() == 1.5
    with pytest.raises(ValueError, match="currency mismatch"):
        Money(amount_minor=1, currency="EUR") + Money(amount_minor=1, currency="USD")
    with pytest.raises(ValueError, match="unsupported"):
        Money(amount_minor=1, currency="XXX")
    assert micro_to_minor(20_000, "EUR") == 2 and micro_to_minor(4_999, "EUR") == 0
    assert micro_to_minor(5_000, "EUR") == 1, "half up"


def test_without_a_subscription_nothing_can_start(world: tuple) -> None:  # type: ignore[type-arg]
    _, usage, _, _, org, _ = world
    entitlement = usage.entitlement(org.id)
    assert not entitlement.can_start_attestations and "none" in entitlement.reason
    with pytest.raises(QuotaError, match="cannot start"):
        usage.reserve(org.id, None, 100)


def test_reservations_respect_the_hard_limit_and_settle_what_was_used(world: tuple) -> None:  # type: ignore[type-arg]
    store, usage, _, _, org, _ = world
    subscribe(store, org)
    from suncly.domain.ledger import SpendingLimit

    store.add_spending_limit(
        SpendingLimit(
            organization_id=org.id, currency="EUR", period_limit_minor=500, set_by="a", set_at=NOW
        )
    )
    estimate = usage.estimate(planned_runs=10, model_judged_runs=0, model=None, byok=False)
    assert estimate.total_minor == 20, "10 attempts at 2 cents in the test table"
    reservation = usage.reserve(org.id, None, 300)
    with pytest.raises(QuotaError, match="hard spending limit"):
        usage.reserve(org.id, None, 300)
    assert usage.entitlement(org.id).remaining_minor == 200
    attestation_id = uuid4()
    for _ in range(3):
        usage.record_agent_call(
            organization_id=org.id,
            attestation_id=attestation_id,
            execution_attempt_id=None,
            reservation_id=reservation.id,
            outcome=UsageOutcome.SETTLED,
        )
    settled = usage.settle(reservation.id, unknown_attempts=0)
    assert settled.state is ReservationState.SETTLED and settled.settled_minor == 6
    totals = usage.totals(org.id)
    assert totals.settled_minor == 6 and totals.reserved_minor == 0
    assert totals.allowance_used_minor == 6, "within the pilot allowance of 20 EUR"
    assert all(
        e.settlement is SettlementState.NOT_BILLABLE for e in store.list_usage_events(org.id)
    )
    assert usage.entitlement(org.id).remaining_minor == 494


def test_concurrent_reservations_cannot_both_pass_the_limit(world: tuple) -> None:  # type: ignore[type-arg]
    store, usage, _, _, org, _ = world
    subscribe(store, org)
    from suncly.domain.ledger import SpendingLimit

    store.add_spending_limit(
        SpendingLimit(
            organization_id=org.id, currency="EUR", period_limit_minor=100, set_by="a", set_at=NOW
        )
    )
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt() -> None:
        try:
            usage.reserve(org.id, None, 60)
            result = "ok"
        except QuotaError:
            result = "refused"
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert outcomes.count("ok") == 1 and outcomes.count("refused") == 5


def test_unknown_outcomes_hold_the_reservation_until_a_person_reconciles(world: tuple) -> None:  # type: ignore[type-arg]
    store, usage, _, _, org, _ = world
    subscribe(store, org)
    reservation = usage.reserve(org.id, None, 100, note="unknown: attestation x")
    event = usage.record_agent_call(
        organization_id=org.id,
        attestation_id=uuid4(),
        execution_attempt_id=None,
        reservation_id=reservation.id,
        outcome=UsageOutcome.UNKNOWN,
        note="runner died after sending",
    )
    assert event.provider_cost_minor is None and event.billable_minor == 0
    held = usage.settle(reservation.id, unknown_attempts=1)
    assert held.state is ReservationState.HELD
    assert usage.totals(org.id).unknown_held_minor == 100
    closed = usage.reconcile(reservation.id, 40, "operator confirmed two calls with the customer")
    assert closed.state is ReservationState.SETTLED and closed.settled_minor == 40
    adjustments = [
        e for e in store.list_usage_events(org.id) if e.operation is UsageOperation.ADJUSTMENT
    ]
    assert len(adjustments) == 1 and adjustments[0].billable_minor == 40


def test_model_usage_is_priced_from_the_table_and_byok_is_never_billed(world: tuple) -> None:  # type: ignore[type-arg]
    store, usage, _, _, org, _ = world
    subscribe(store, org)
    measured = ModelUsage(
        input_tokens=1_000_000, output_tokens=100_000, provider_request_id="req_1"
    )
    billed = usage.record_model_call(
        organization_id=org.id,
        attestation_id=None,
        execution_attempt_id=None,
        reservation_id=None,
        provider="anthropic",
        model="claude-opus-5-5",
        operation=UsageOperation.JUDGE,
        usage=measured,
        outcome=UsageOutcome.SETTLED,
        byok=False,
    )
    assert billed.billable_minor == 400 + 200 and billed.provider_cost_minor == 600
    assert billed.price_table_version == "2026-10-test"
    byok = usage.record_model_call(
        organization_id=org.id,
        attestation_id=None,
        execution_attempt_id=None,
        reservation_id=None,
        provider="anthropic",
        model="claude-opus-5-5",
        operation=UsageOperation.JUDGE,
        usage=ModelUsage(input_tokens=1000, output_tokens=10, provider_request_id="req_2"),
        outcome=UsageOutcome.SETTLED,
        byok=True,
    )
    assert byok.billable_minor == 0 and byok.settlement is SettlementState.NOT_BILLABLE
    assert "bring-your-own-key" in byok.note
    failed = usage.record_model_call(
        organization_id=org.id,
        attestation_id=None,
        execution_attempt_id=None,
        reservation_id=None,
        provider="anthropic",
        model="claude-opus-5-5",
        operation=UsageOperation.DRAFT,
        usage=ModelUsage(),
        outcome=UsageOutcome.FAILED,
        byok=False,
    )
    assert failed.billable_minor == 0
    with pytest.raises(Exception, match="already recorded"):
        usage.record_model_call(
            organization_id=org.id,
            attestation_id=None,
            execution_attempt_id=None,
            reservation_id=None,
            provider="anthropic",
            model="claude-opus-5-5",
            operation=UsageOperation.JUDGE,
            usage=measured,
            outcome=UsageOutcome.SETTLED,
            byok=False,
        )


def test_overage_beyond_the_allowance_is_reported_once_to_the_meter(world: tuple) -> None:  # type: ignore[type-arg]
    store, usage, billing, provider, org, _ = world
    subscribe(store, org)
    big = ModelUsage(input_tokens=10_000_000, output_tokens=0, provider_request_id="req_big")
    event = usage.record_model_call(
        organization_id=org.id,
        attestation_id=None,
        execution_attempt_id=None,
        reservation_id=None,
        provider="anthropic",
        model="claude-opus-5-5",
        operation=UsageOperation.JUDGE,
        usage=big,
        outcome=UsageOutcome.SETTLED,
        byok=False,
    )
    assert (
        event.billable_minor == 4000
        and event.allowance_minor == 2000
        and event.overage_minor == 2000
    )
    assert event.settlement is SettlementState.PENDING
    assert [m.topic for m in store.claim_outbox(10, NOW)] == ["usage.settled"]
    first = billing.report_pending_usage()
    assert first == [f"{event.id}: reported"]
    assert (
        provider.meter_events[0].identifier == str(event.id)
        and provider.meter_events[0].value == 2000
    )
    assert billing.report_pending_usage() == [], "nothing pending after the report"
    assert store.mark_usage_reported(store.meter_reports[event.id]) is False, "deduplicated"
    reconciliation = billing.reconciliation(org.id)
    assert (
        reconciliation["reported_overage_minor"] == 2000
        and reconciliation["pending_overage_minor"] == 0
    )


def _signed(
    provider: FakeBillingProvider, payload: bytes, at: int | None = None
) -> tuple[bytes, str]:
    import time

    return payload, sign_webhook_payload(payload, provider.webhook_secret, at or int(time.time()))


def test_webhooks_are_verified_recorded_once_and_applied_in_order(world: tuple) -> None:  # type: ignore[type-arg]
    store, _, billing, provider, org, _ = world
    checkout = webhook_event(
        "evt_1",
        "checkout.session.completed",
        1_800_000_000,
        {
            "id": "cs_1",
            "customer": "cus_9",
            "subscription": "sub_9",
            "metadata": {"suncly_organization_id": str(org.id), "suncly_plan_id": "team"},
        },
    )
    payload, signature = _signed(provider, checkout)
    assert billing.handle_webhook(payload, signature) == "checkout applied: plan team"
    assert billing.handle_webhook(payload, signature) == "duplicate: already recorded"
    with pytest.raises(BillingError, match="signature"):
        billing.handle_webhook(payload, "t=1,v1=deadbeef")
    with pytest.raises(BillingError, match="signature"):
        billing.handle_webhook(payload + b" ", signature)
    tampered = payload.replace(b"cus_9", b"cus_evil")
    with pytest.raises(BillingError, match="signature"):
        billing.handle_webhook(tampered, signature)
    subscription = store.get_subscription(org.id)
    assert subscription is not None and subscription.provider_customer_id == "cus_9"

    newer = webhook_event(
        "evt_3",
        "customer.subscription.updated",
        1_800_000_200,
        {
            "id": "sub_9",
            "customer": "cus_9",
            "status": "past_due",
            "items": {
                "data": [
                    {"current_period_start": 1_800_000_000, "current_period_end": 1_802_592_000}
                ]
            },
        },
    )
    older = webhook_event(
        "evt_2",
        "customer.subscription.updated",
        1_800_000_100,
        {"id": "sub_9", "customer": "cus_9", "status": "active"},
    )
    assert billing.handle_webhook(*_signed(provider, newer)) == "subscription past_due"
    assert (
        billing.handle_webhook(*_signed(provider, older))
        == "stale: a newer event was already applied"
    )
    current = store.get_subscription(org.id)
    assert current is not None and current.status is SubscriptionStatus.PAST_DUE
    assert current.current_period_end == datetime.fromtimestamp(1_802_592_000, tz=UTC)

    paid = webhook_event(
        "evt_4", "invoice.paid", 1_800_000_300, {"id": "in_1", "customer": "cus_9"}
    )
    assert billing.handle_webhook(*_signed(provider, paid)) == "invoice applied: active"
    failed = webhook_event(
        "evt_5", "invoice.payment_failed", 1_800_000_400, {"id": "in_2", "customer": "cus_9"}
    )
    assert billing.handle_webhook(*_signed(provider, failed)) == "invoice applied: past_due"
    usage = UsageService(store, FakeClock(NOW), SeqIds(), TEST_PRICE_TABLE, TEST_PLANS)
    assert not usage.entitlement(org.id).can_start_attestations, "a failed payment blocks new work"
    unknown = webhook_event(
        "evt_6",
        "customer.subscription.updated",
        1_800_000_500,
        {"id": "sub_x", "customer": "cus_unknown", "status": "active"},
    )
    assert billing.handle_webhook(*_signed(provider, unknown)).startswith("ignored")
    ignored = webhook_event("evt_7", "charge.refunded", 1_800_000_600, {"id": "ch_1"})
    assert billing.handle_webhook(*_signed(provider, ignored)) == "ignored: charge.refunded"
    deleted = webhook_event(
        "evt_8",
        "customer.subscription.deleted",
        1_800_000_700,
        {"id": "sub_9", "customer": "cus_9", "status": "canceled"},
    )
    assert billing.handle_webhook(*_signed(provider, deleted)) == "subscription canceled"
    late_paid = webhook_event(
        "evt_9", "invoice.paid", 1_800_000_800, {"id": "in_3", "customer": "cus_9"}
    )
    assert "canceled" in billing.handle_webhook(*_signed(provider, late_paid))


def test_checkout_and_portal_go_through_the_provider_with_the_organization_in_metadata(
    world: World,
) -> None:
    store, _, billing, provider, org, _ = world
    with pytest.raises(BillingError, match="no provider price"):
        billing.start_checkout(org.id, org.slug, "pilot", "a@x")
    plans = dict(TEST_PLANS)
    plans["pilot"] = plans["pilot"].model_copy(update={"provider_price_id": "price_test_123"})
    priced = BillingService(
        store, provider, FakeClock(NOW), plans, "https://s", "https://c", "https://p"
    )
    session = priced.start_checkout(org.id, org.slug, "pilot", "a@x")
    assert session.url.startswith("https://checkout.stripe.com/")
    assert (
        provider.checkouts[0].organization_id == str(org.id)
        and provider.checkouts[0].provider_price_id == "price_test_123"
    )
    with pytest.raises(Exception, match="no billing customer"):
        priced.open_portal(org.id)
    subscribe(store, org)
    assert priced.open_portal(org.id).url.startswith("https://billing.stripe.com/")
    from suncly.domain.errors import NotFoundError

    with pytest.raises(NotFoundError):
        priced.start_checkout(org.id, org.slug, "enterprise", None)


def test_the_real_adapter_refuses_live_keys() -> None:
    with pytest.raises(BillingError, match="test-mode"):
        StripeBillingProvider("sk_live_abc", "whsec_x")
    adapter = StripeBillingProvider("sk_test_abc", "whsec_x")
    assert adapter.test_mode
    payload = webhook_event("evt_1", "invoice.paid", 1, {"id": "in_1"})
    with pytest.raises(BillingError, match="signature"):
        adapter.verify_webhook(payload, None)
    event = adapter.verify_webhook(
        payload, sign_webhook_payload(payload, "whsec_x", int(datetime.now(UTC).timestamp()))
    )
    assert event.event_type == "invoice.paid" and json.loads(payload)["id"] == event.event_id
