"""The usage service: reservations, settlement, hard limits and entitlement.

Money is reserved before an attestation starts and settled when it ends.
Every provider call becomes one ledger line. The service never talks to the
payment provider: it only writes the ledger and the outbox; the relay
(``core/billing.py``) reports settled overage later.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from suncly.domain.billing import ENTITLED_STATUSES, Entitlement, Plan, SubscriptionStatus
from suncly.domain.errors import QuotaError
from suncly.domain.jobs import OutboxMessage
from suncly.domain.ledger import (
    PriceTable,
    Reservation,
    ReservationState,
    SettlementState,
    UsageEvent,
    UsageOperation,
    UsageOutcome,
    price_model_usage,
    price_usage,
)
from suncly.domain.models import JsonObject
from suncly.ports.app_store import ApplicationStore, LedgerTotals
from suncly.ports.clock import Clock, IdGenerator
from suncly.ports.model import ModelUsage

#: Topic of the outbox message that announces a settled ledger line.
USAGE_SETTLED_TOPIC = "usage.settled"


@dataclass(frozen=True)
class Estimate:
    """What an attestation may cost at most, in minor units, before it starts."""

    agent_calls_minor: int
    judge_minor: int

    @property
    def total_minor(self) -> int:
        return self.agent_calls_minor + self.judge_minor


class UsageService:
    def __init__(
        self,
        store: ApplicationStore,
        clock: Clock,
        ids: IdGenerator,
        table: PriceTable,
        plans: dict[str, Plan],
    ) -> None:
        self._store = store
        self._clock = clock
        self._ids = ids
        self._table = table
        self._plans = plans

    @property
    def currency(self) -> str:
        return self._table.currency

    # -- entitlement -----------------------------------------------------------

    def period_start(self, organization_id: UUID) -> datetime | None:
        subscription = self._store.get_subscription(organization_id)
        return subscription.current_period_start if subscription else None

    def entitlement(self, organization_id: UUID) -> Entitlement:
        subscription = self._store.get_subscription(organization_id)
        status = subscription.status if subscription else SubscriptionStatus.NONE
        plan = self._plans.get(subscription.plan_id) if subscription else None
        limit = self._store.get_spending_limit(organization_id)
        totals = self._store.ledger_totals(organization_id, self.period_start(organization_id))
        remaining: int | None = None
        if limit is not None:
            remaining = max(
                limit.period_limit_minor - totals.settled_minor - totals.reserved_minor, 0
            )
        if status not in ENTITLED_STATUSES:
            can_start, reason = False, f"subscription status is {status.value}"
        elif plan is None:
            can_start, reason = False, "the subscription names a plan that is not in the catalog"
        elif remaining == 0:
            can_start, reason = False, "the hard spending limit for this period is reached"
        else:
            can_start, reason = True, "entitled"
        return Entitlement(
            organization_id=organization_id,
            can_start_attestations=can_start,
            reason=reason,
            subscription_status=status,
            plan_id=plan.id if plan else None,
            currency=self.currency,
            included_allowance_minor=plan.included_allowance_minor if plan else 0,
            allowance_used_minor=totals.allowance_used_minor,
            settled_minor=totals.settled_minor,
            reserved_minor=totals.reserved_minor,
            unknown_minor_held=totals.unknown_held_minor,
            period_limit_minor=limit.period_limit_minor if limit else None,
            remaining_minor=remaining,
        )

    # -- estimates and reservations --------------------------------------------

    def estimate(
        self, planned_runs: int, model_judged_runs: int, model: str | None, byok: bool
    ) -> Estimate:
        call_line = self._table.line_for("suncly-runner", UsageOperation.AGENT_CALL, None)
        _, per_call = price_usage(self._table, call_line, {"calls": 1})
        judge_minor = 0
        if model_judged_runs and model and not byok:
            provider, _, name = model.partition(":")
            # A bounded guess per judged run: 4k input tokens and 1k output tokens.
            _, per_judge = price_model_usage(
                self._table, provider, name, {"input_tokens": 4000, "output_tokens": 1000}
            )
            judge_minor = per_judge * model_judged_runs
        return Estimate(agent_calls_minor=per_call * planned_runs, judge_minor=judge_minor)

    def reserve(
        self, organization_id: UUID, attestation_id: UUID | None, amount_minor: int, note: str = ""
    ) -> Reservation:
        """Hold ``amount_minor`` under the hard limit, or raise ``QuotaError``."""
        entitlement = self.entitlement(organization_id)
        if not entitlement.can_start_attestations:
            raise QuotaError(
                "The organization cannot start attestations.",
                entitlement.reason + ".",
                "Check the subscription and the spending limit under Settings.",
            )
        reservation = Reservation(
            id=self._ids.new_id(),
            organization_id=organization_id,
            attestation_id=attestation_id,
            amount_minor=amount_minor,
            currency=self.currency,
            state=ReservationState.HELD,
            created_at=self._clock.now(),
            note=note,
        )
        limit = self._store.get_spending_limit(organization_id)
        ok = self._store.try_reserve(
            reservation,
            limit.period_limit_minor if limit else None,
            self.period_start(organization_id),
        )
        if not ok:
            raise QuotaError(
                "The hard spending limit would be exceeded.",
                f"Reserving {amount_minor} {self.currency} minor units does not fit under the "
                f"period limit of {limit.period_limit_minor if limit else 'none'}; settled plus "
                f"held usage is {entitlement.settled_minor + entitlement.reserved_minor}.",
                "Raise the limit under Settings, or wait for held reservations to settle.",
            )
        return reservation

    # -- recording usage ---------------------------------------------------------

    def _allowance_for(self, organization_id: UUID, billable_minor: int) -> int:
        subscription = self._store.get_subscription(organization_id)
        plan = self._plans.get(subscription.plan_id) if subscription else None
        if plan is None:
            return 0
        used = self._store.ledger_totals(
            organization_id, self.period_start(organization_id)
        ).allowance_used_minor
        return max(min(plan.included_allowance_minor - used, billable_minor), 0)

    def record_agent_call(
        self,
        *,
        organization_id: UUID,
        attestation_id: UUID,
        execution_attempt_id: UUID | None,
        reservation_id: UUID | None,
        outcome: UsageOutcome,
        note: str = "",
        operation: UsageOperation = UsageOperation.AGENT_CALL,
        logical_run_id: UUID | None = None,
    ) -> UsageEvent:
        """One line per Runner call. ``logical_run_id`` is the recorded run's id, so a
        resumed execution can tell which runs the ledger already carries."""
        line = self._table.line_for("suncly-runner", operation, None)
        measured: JsonObject = {"calls": 1}
        cost, billable = price_usage(self._table, line, measured)
        if outcome is UsageOutcome.FAILED:
            cost, billable = 0, 0
        return self._record(
            organization_id=organization_id,
            attestation_id=attestation_id,
            execution_attempt_id=execution_attempt_id,
            reservation_id=reservation_id,
            provider="suncly-runner",
            provider_request_id=None,
            model=None,
            operation=operation,
            outcome=outcome,
            measured=measured,
            provider_cost=None if outcome is UsageOutcome.UNKNOWN else cost,
            billable=0 if outcome is UsageOutcome.UNKNOWN else billable,
            byok=False,
            note=note,
            logical_run_id=logical_run_id,
        )

    def record_model_call(
        self,
        *,
        organization_id: UUID,
        attestation_id: UUID | None,
        execution_attempt_id: UUID | None,
        reservation_id: UUID | None,
        provider: str,
        model: str,
        operation: UsageOperation,
        usage: ModelUsage,
        outcome: UsageOutcome,
        byok: bool,
        note: str = "",
    ) -> UsageEvent:
        measured: JsonObject = {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cache_read_tokens": usage.cache_read_tokens,
        }
        if outcome is UsageOutcome.SETTLED:
            cost, billable = price_model_usage(self._table, provider, model, measured)
        else:
            cost, billable = 0, 0
        return self._record(
            organization_id=organization_id,
            attestation_id=attestation_id,
            execution_attempt_id=execution_attempt_id,
            reservation_id=reservation_id,
            provider=provider,
            provider_request_id=usage.provider_request_id,
            model=model,
            operation=operation,
            outcome=outcome,
            measured=measured,
            provider_cost=None if outcome is UsageOutcome.UNKNOWN else cost,
            billable=billable,
            byok=byok,
            note=note,
        )

    def record_adjustment(
        self, organization_id: UUID, attestation_id: UUID | None, amount_minor: int, note: str
    ) -> UsageEvent:
        """A reconciliation correction: a new line, never an edit (negative amounts allowed)."""
        event = UsageEvent(
            id=self._ids.new_id(),
            organization_id=organization_id,
            attestation_id=attestation_id,
            logical_run_id=None,
            execution_attempt_id=None,
            reservation_id=None,
            provider="suncly",
            model=None,
            operation=UsageOperation.ADJUSTMENT,
            outcome=UsageOutcome.SETTLED,
            measured={"amount_minor": amount_minor},
            currency=self.currency,
            provider_cost_minor=0,
            price_table_version=self._table.version,
            billable_minor=max(amount_minor, 0),
            allowance_minor=0,
            settlement=SettlementState.PENDING
            if amount_minor > 0
            else SettlementState.NOT_BILLABLE,
            recorded_at=self._clock.now(),
            note=note if amount_minor >= 0 else f"{note} (credit of {-amount_minor})",
        )
        self._store.add_usage_event(event)
        return event

    def _record(
        self,
        *,
        organization_id: UUID,
        attestation_id: UUID | None,
        execution_attempt_id: UUID | None,
        reservation_id: UUID | None,
        provider: str,
        provider_request_id: str | None,
        model: str | None,
        operation: UsageOperation,
        outcome: UsageOutcome,
        measured: JsonObject,
        provider_cost: int | None,
        billable: int,
        byok: bool,
        note: str,
        logical_run_id: UUID | None = None,
    ) -> UsageEvent:
        if byok:
            billable_minor, allowance, settlement = 0, 0, SettlementState.NOT_BILLABLE
            note = (
                note + "; " if note else ""
            ) + "bring-your-own-key: provider usage billed by the provider"
            provider_cost = None
        else:
            billable_minor = billable
            allowance = self._allowance_for(organization_id, billable_minor)
            settlement = (
                SettlementState.PENDING
                if billable_minor - allowance > 0
                else SettlementState.NOT_BILLABLE
            )
        event = UsageEvent(
            id=self._ids.new_id(),
            organization_id=organization_id,
            attestation_id=attestation_id,
            logical_run_id=logical_run_id,
            execution_attempt_id=execution_attempt_id,
            reservation_id=reservation_id,
            provider=provider,
            provider_request_id=provider_request_id,
            model=model,
            operation=operation,
            outcome=outcome,
            measured=measured,
            currency=self.currency,
            provider_cost_minor=provider_cost,
            price_table_version=self._table.version,
            billable_minor=billable_minor,
            allowance_minor=allowance,
            settlement=settlement,
            recorded_at=self._clock.now(),
            note=note,
        )
        self._store.add_usage_event(event)
        if event.settlement is SettlementState.PENDING:
            self._store.add_outbox(
                OutboxMessage(
                    id=self._ids.new_id(),
                    organization_id=organization_id,
                    topic=USAGE_SETTLED_TOPIC,
                    dedup_key=f"usage:{event.id}",
                    payload={"usage_event_id": str(event.id), "overage_minor": event.overage_minor},
                    created_at=self._clock.now(),
                )
            )
        return event

    # -- settlement --------------------------------------------------------------

    def settle(self, reservation_id: UUID, unknown_attempts: int) -> Reservation:
        """Close the reservation: settle what the ledger recorded for it, release the rest.

        With unknown attempts the reservation stays held, marked, until a person
        reconciles it: a lost response can leave money owed that nobody can measure.
        """
        reservation = self._store.get_reservation(reservation_id)
        if reservation is None or reservation.state is not ReservationState.HELD:
            return reservation if reservation else self._missing(reservation_id)
        if unknown_attempts:
            return reservation
        settled = sum(
            event.billable_minor
            for event in self._store.list_usage_events(reservation.organization_id)
            if event.reservation_id == reservation_id and event.outcome is UsageOutcome.SETTLED
        )
        return self._store.close_reservation(
            reservation_id,
            min(settled, reservation.amount_minor),
            self._clock.now(),
            released=False,
        )

    def release(self, reservation_id: UUID) -> Reservation | None:
        reservation = self._store.get_reservation(reservation_id)
        if reservation is None or reservation.state is not ReservationState.HELD:
            return reservation
        return self._store.close_reservation(reservation_id, 0, self._clock.now(), released=True)

    def reconcile(self, reservation_id: UUID, settled_minor: int, note: str) -> Reservation:
        """A person closes a reservation held for unknown outcomes, with a recorded reason."""
        reservation = self._store.get_reservation(reservation_id)
        if reservation is None:
            return self._missing(reservation_id)
        if settled_minor:
            self.record_adjustment(
                reservation.organization_id, reservation.attestation_id, settled_minor, note
            )
        return self._store.close_reservation(
            reservation_id, settled_minor, self._clock.now(), released=settled_minor == 0
        )

    @staticmethod
    def _missing(reservation_id: UUID) -> Reservation:
        raise QuotaError("The reservation does not exist.", f"No reservation {reservation_id}.")

    def totals(self, organization_id: UUID) -> LedgerTotals:
        return self._store.ledger_totals(organization_id, self.period_start(organization_id))
