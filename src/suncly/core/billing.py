"""Billing: subscriptions, checkout, the customer portal, webhooks and meter reporting.

Stripe (test mode) sells the subscription and receives settled overage. The
ledger stays the source of truth for the budget. Webhooks are verified by the
provider adapter, recorded once by event id, and applied only when they are
newer than what the subscription already reflects, so replays and
out-of-order deliveries change nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from suncly.domain.billing import MeterReport, Plan, ProviderEvent, Subscription, SubscriptionStatus
from suncly.domain.errors import BillingError, ConflictError, NotFoundError
from suncly.domain.ledger import SettlementState
from suncly.domain.models import JsonObject
from suncly.ports.app_store import ApplicationStore
from suncly.ports.billing_provider import (
    BillingProvider,
    CheckoutRequest,
    CheckoutSession,
    MeterEventRequest,
    PortalSession,
    ProviderWebhook,
)
from suncly.ports.clock import Clock

#: Provider subscription statuses mapped onto Suncly's.
_STATUS_MAP = {
    "trialing": SubscriptionStatus.TRIALING,
    "active": SubscriptionStatus.ACTIVE,
    "past_due": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "unpaid": SubscriptionStatus.UNPAID,
    "incomplete": SubscriptionStatus.NONE,
    "incomplete_expired": SubscriptionStatus.NONE,
    "paused": SubscriptionStatus.PAST_DUE,
}

HANDLED_EVENTS = frozenset(
    {
        "checkout.session.completed",
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
        "invoice.paid",
        "invoice.payment_failed",
    }
)


def _epoch(value: Any) -> datetime | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), tz=UTC)
    return None


class BillingService:
    def __init__(
        self,
        store: ApplicationStore,
        provider: BillingProvider,
        clock: Clock,
        plans: dict[str, Plan],
        success_url: str,
        cancel_url: str,
        portal_return_url: str,
    ) -> None:
        self._store = store
        self._provider = provider
        self._clock = clock
        self._plans = plans
        self._success_url = success_url
        self._cancel_url = cancel_url
        self._portal_return_url = portal_return_url

    @property
    def plans(self) -> dict[str, Plan]:
        return self._plans

    # -- checkout and portal ------------------------------------------------------

    def start_checkout(
        self, organization_id: UUID, slug: str, plan_id: str, email: str | None
    ) -> CheckoutSession:
        plan = self._plans.get(plan_id)
        if plan is None:
            raise NotFoundError("Unknown plan.", f"No plan {plan_id!r} in the catalog.")
        if plan.provider_price_id is None:
            raise BillingError(
                "This plan has no provider price configured.",
                f"Plan {plan_id} needs STRIPE_PRICE_{plan_id.upper()} (a test-mode price id).",
                "Create the price in the Stripe test dashboard and set the variable.",
            )
        existing = self._store.get_subscription(organization_id)
        return self._provider.create_checkout(
            CheckoutRequest(
                organization_id=str(organization_id),
                organization_slug=slug,
                plan_id=plan_id,
                provider_price_id=plan.provider_price_id,
                customer_email=email,
                existing_customer_id=existing.provider_customer_id if existing else None,
                success_url=self._success_url,
                cancel_url=self._cancel_url,
            )
        )

    def open_portal(self, organization_id: UUID) -> PortalSession:
        subscription = self._store.get_subscription(organization_id)
        if subscription is None or not subscription.provider_customer_id:
            raise ConflictError(
                "There is no billing customer yet.",
                "The organization has not completed a checkout.",
                "Start a checkout first.",
            )
        return self._provider.create_portal(
            subscription.provider_customer_id, self._portal_return_url
        )

    # -- webhooks ------------------------------------------------------------------

    def handle_webhook(self, payload: bytes, signature_header: str | None) -> str:
        """Verify, record once, apply if newer. Returns a short description of what happened."""
        event = self._provider.verify_webhook(payload, signature_header)
        record = ProviderEvent(
            provider=self._provider.name,
            event_id=event.event_id,
            event_type=event.event_type,
            provider_created_at=datetime.fromtimestamp(event.created, tz=UTC),
            received_at=self._clock.now(),
            processed=False,
        )
        if not self._store.record_provider_event(record):
            return "duplicate: already recorded"
        try:
            result = self.apply_event(event)
        except Exception as exc:
            self._store.mark_provider_event(self._provider.name, event.event_id, f"error: {exc}")
            raise
        self._store.mark_provider_event(self._provider.name, event.event_id, result)
        return result

    def apply_event(self, event: ProviderWebhook) -> str:
        if event.event_type not in HANDLED_EVENTS:
            return f"ignored: {event.event_type}"
        obj = event.data.get("object") if isinstance(event.data, dict) else None
        if not isinstance(obj, dict):
            return "ignored: no object"
        occurred = datetime.fromtimestamp(event.created, tz=UTC)
        if event.event_type == "checkout.session.completed":
            return self._apply_checkout(obj, occurred)
        if event.event_type.startswith("customer.subscription."):
            return self._apply_subscription(obj, occurred)
        if event.event_type == "invoice.payment_failed":
            return self._apply_invoice(obj, occurred, SubscriptionStatus.PAST_DUE)
        if event.event_type == "invoice.paid":
            return self._apply_invoice(obj, occurred, SubscriptionStatus.ACTIVE)
        return f"ignored: {event.event_type}"

    def _organization_from_metadata(self, obj: JsonObject) -> UUID | None:
        metadata: JsonObject = obj["metadata"] if isinstance(obj.get("metadata"), dict) else {}
        raw = metadata.get("suncly_organization_id")
        try:
            return UUID(str(raw)) if raw else None
        except ValueError:
            return None

    def _apply_checkout(self, session: JsonObject, occurred: datetime) -> str:
        organization_id = self._organization_from_metadata(session)
        if organization_id is None or self._store.get_organization(organization_id) is None:
            return "ignored: checkout without a known organization"
        metadata = session.get("metadata") or {}
        plan_id = str(metadata.get("suncly_plan_id") or "")
        if plan_id not in self._plans:
            return "ignored: checkout without a known plan"
        current = self._store.get_subscription(organization_id)
        if current and current.provider_updated_at and current.provider_updated_at > occurred:
            return "stale: a newer event was already applied"
        subscription = Subscription(
            organization_id=organization_id,
            plan_id=plan_id,
            status=current.status if current else SubscriptionStatus.ACTIVE,
            provider=self._provider.name,
            provider_customer_id=str(session.get("customer") or "") or None,
            provider_subscription_id=str(session.get("subscription") or "") or None,
            current_period_start=current.current_period_start if current else occurred,
            current_period_end=current.current_period_end if current else None,
            provider_updated_at=occurred,
            updated_at=self._clock.now(),
        )
        self._store.upsert_subscription(subscription)
        return f"checkout applied: plan {plan_id}"

    def _apply_subscription(self, sub: JsonObject, occurred: datetime) -> str:
        customer_id = str(sub.get("customer") or "")
        organization_id = self._organization_from_metadata(sub)
        current = (self._store.get_subscription(organization_id) if organization_id else None) or (
            self._store.find_subscription_by_customer(self._provider.name, customer_id)
            if customer_id
            else None
        )
        if current is None:
            return "ignored: subscription for an unknown customer"
        if current.provider_updated_at and current.provider_updated_at > occurred:
            return "stale: a newer event was already applied"
        status = _STATUS_MAP.get(str(sub.get("status")), current.status)
        items: JsonObject = sub["items"] if isinstance(sub.get("items"), dict) else {}
        data = items.get("data")
        first: JsonObject = data[0] if isinstance(data, list) and data else {}
        updated = current.model_copy(
            update={
                "status": status,
                "provider_subscription_id": str(sub.get("id") or current.provider_subscription_id),
                "current_period_start": _epoch(first.get("current_period_start"))
                or _epoch(sub.get("current_period_start"))
                or current.current_period_start,
                "current_period_end": _epoch(first.get("current_period_end"))
                or _epoch(sub.get("current_period_end"))
                or current.current_period_end,
                "provider_updated_at": occurred,
                "updated_at": self._clock.now(),
            }
        )
        self._store.upsert_subscription(updated)
        return f"subscription {status.value}"

    def _apply_invoice(
        self, invoice: JsonObject, occurred: datetime, status: SubscriptionStatus
    ) -> str:
        customer_id = str(invoice.get("customer") or "")
        current = (
            self._store.find_subscription_by_customer(self._provider.name, customer_id)
            if customer_id
            else None
        )
        if current is None:
            return "ignored: invoice for an unknown customer"
        if current.provider_updated_at and current.provider_updated_at > occurred:
            return "stale: a newer event was already applied"
        if status is SubscriptionStatus.ACTIVE and current.status is SubscriptionStatus.CANCELED:
            return "ignored: invoice paid for a canceled subscription"
        self._store.upsert_subscription(
            current.model_copy(
                update={
                    "status": status,
                    "provider_updated_at": occurred,
                    "updated_at": self._clock.now(),
                }
            )
        )
        return f"invoice applied: {status.value}"

    # -- meter reporting ---------------------------------------------------------------

    def report_pending_usage(self, limit: int = 100) -> list[str]:
        """Deliver settled overage to the provider's meter, once per usage event."""
        outcomes: list[str] = []
        for event in self._store.list_unreported_usage(limit):
            if event.settlement is not SettlementState.PENDING or event.overage_minor <= 0:
                continue
            subscription = self._store.get_subscription(event.organization_id)
            plan = self._plans.get(subscription.plan_id) if subscription else None
            if (
                subscription is None
                or plan is None
                or not plan.overage_billed
                or not subscription.provider_customer_id
                or not plan.overage_meter_event_name
            ):
                outcomes.append(f"{event.id}: no billable subscription; kept pending")
                continue
            response_id = self._provider.report_meter_event(
                MeterEventRequest(
                    event_name=plan.overage_meter_event_name,
                    customer_id=subscription.provider_customer_id,
                    value=event.overage_minor,
                    identifier=str(event.id),
                    timestamp=int(event.recorded_at.timestamp()),
                )
            )
            recorded = self._store.mark_usage_reported(
                MeterReport(
                    usage_event_id=event.id,
                    provider=self._provider.name,
                    identifier=str(event.id),
                    reported_at=self._clock.now(),
                    provider_response_id=response_id,
                )
            )
            outcomes.append(f"{event.id}: {'reported' if recorded else 'already reported'}")
        return outcomes

    def reconciliation(self, organization_id: UUID) -> JsonObject:
        """What the ledger says versus what was reported, for an operator to compare with Stripe."""
        since = None
        subscription = self._store.get_subscription(organization_id)
        if subscription is not None:
            since = subscription.current_period_start
        events = self._store.list_usage_events(organization_id, since)
        reported = sum(e.overage_minor for e in events if e.settlement is SettlementState.REPORTED)
        pending = sum(e.overage_minor for e in events if e.settlement is SettlementState.PENDING)
        unknown = [str(e.id) for e in events if e.outcome.value == "unknown"]
        held = [
            {"id": str(r.id), "amount_minor": r.amount_minor, "note": r.note}
            for r in self._store.list_reservations(organization_id)
            if r.state.value == "held"
        ]
        return {
            "organization_id": str(organization_id),
            "period_start": since.isoformat() if since else None,
            "reported_overage_minor": reported,
            "pending_overage_minor": pending,
            "unknown_outcome_events": unknown,
            "held_reservations": held,
            "note": "Stripe meter totals are compared out of band; this is the ledger's view.",
        }
