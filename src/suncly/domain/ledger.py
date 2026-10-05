"""The usage ledger: money in integer minor units, append-only events, reservations.

``cost_total`` and ``budget_limit`` on the attestation keep counting attempts
(the execution metric, OQ-D1). Money lives here, never as a float. Every
provider call that can cost money produces one ``UsageEvent``; the ledger is
the source of truth for what a tenant may still spend, and Stripe only ever
receives settled events.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

JsonObject = dict[str, Any]

#: ISO 4217 currencies the ledger accepts, with their minor-unit exponent.
CURRENCY_EXPONENT = {"EUR": 2, "USD": 2, "GBP": 2}


class Money(BaseModel):
    """An amount in integer minor units (cents) of one currency. Never a float."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    amount_minor: int
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    @model_validator(mode="after")
    def _known_currency(self) -> Money:
        if self.currency not in CURRENCY_EXPONENT:
            raise ValueError(f"unsupported currency {self.currency}")
        return self

    def __add__(self, other: Money) -> Money:
        self._same(other)
        return Money(amount_minor=self.amount_minor + other.amount_minor, currency=self.currency)

    def __sub__(self, other: Money) -> Money:
        self._same(other)
        return Money(amount_minor=self.amount_minor - other.amount_minor, currency=self.currency)

    def _same(self, other: Money) -> None:
        if other.currency != self.currency:
            raise ValueError(f"currency mismatch: {self.currency} and {other.currency}")

    @classmethod
    def zero(cls, currency: str) -> Money:
        return cls(amount_minor=0, currency=currency)

    def as_decimal(self) -> Decimal:
        return Decimal(self.amount_minor).scaleb(-CURRENCY_EXPONENT[self.currency])


def micro_to_minor(amount_micro: int, currency: str) -> int:
    """Round a price expressed in micro-units (10^-6) to minor units, half up."""
    exponent = CURRENCY_EXPONENT[currency]
    value = (Decimal(amount_micro) / Decimal(10**6)).scaleb(exponent)
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


class UsageOperation(StrEnum):
    AGENT_CALL = "agent_call"
    """One attempt by the Runner against the sandbox (a Suncly execution cost)."""
    DRAFT = "draft"
    JUDGE = "judge"
    PROBE = "probe"
    EXTERNAL_TOOL = "external_tool"
    ADJUSTMENT = "adjustment"
    """A reconciliation correction; corrections are new records, never edits."""


class UsageOutcome(StrEnum):
    SETTLED = "settled"
    """The provider reported the usage; the cost is known."""
    UNKNOWN = "unknown"
    """The provider was called but no answer arrived; the cost is not known and is held."""
    FAILED = "failed"
    """The call failed before anything was consumed; nothing is owed."""


class SettlementState(StrEnum):
    PENDING = "pending"
    """Recorded, included in the tenant's balance, not yet reported to Stripe."""
    REPORTED = "reported"
    """Delivered to Stripe as a meter event (deduplicated by the event id)."""
    NOT_BILLABLE = "not_billable"
    """Within the included allowance, BYOK, or a zero amount: never reported."""


class UsageEvent(BaseModel):
    """One append-only ledger line."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    attestation_id: UUID | None
    logical_run_id: UUID | None
    """The attestation (logical run) the usage belongs to; the same across retries."""
    execution_attempt_id: UUID | None
    """The job attempt that incurred it, so retries are visible but never double counted."""
    reservation_id: UUID | None
    provider: str = Field(min_length=1, max_length=64)
    provider_request_id: str | None = Field(default=None, max_length=256)
    model: str | None = Field(default=None, max_length=128)
    operation: UsageOperation
    outcome: UsageOutcome
    measured: JsonObject = Field(default_factory=dict)
    """What was measured: tokens in and out, calls, seconds. Provider-specific keys."""
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    provider_cost_minor: int | None = None
    """What the provider charges Suncly, when known. None for unknown outcomes and BYOK."""
    price_table_version: str = Field(min_length=1)
    billable_minor: int = Field(ge=0)
    """What the customer is charged for this line, before the included allowance."""
    allowance_minor: int = Field(ge=0)
    """The part of ``billable_minor`` absorbed by the subscription's included allowance."""
    settlement: SettlementState
    recorded_at: AwareDatetime
    note: str = ""

    @property
    def overage_minor(self) -> int:
        return self.billable_minor - self.allowance_minor

    @model_validator(mode="after")
    def _consistent(self) -> UsageEvent:
        if self.allowance_minor > self.billable_minor:
            raise ValueError("the allowance cannot exceed the billable amount")
        if self.outcome is UsageOutcome.UNKNOWN and self.provider_cost_minor is not None:
            raise ValueError("an unknown outcome has no known provider cost")
        return self


class ReservationState(StrEnum):
    HELD = "held"
    SETTLED = "settled"
    RELEASED = "released"


class Reservation(BaseModel):
    """A bounded amount set aside before concurrent operations start.

    The hard spending limit is enforced against settled usage plus held
    reservations, so two concurrent attestations cannot both pass the check.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    organization_id: UUID
    attestation_id: UUID | None
    amount_minor: int = Field(ge=0)
    currency: str
    state: ReservationState
    created_at: AwareDatetime
    settled_minor: int = Field(default=0, ge=0)
    closed_at: AwareDatetime | None = None
    note: str = ""


class SpendingLimit(BaseModel):
    """The tenant-controlled hard limit per billing period. No default is invented."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: UUID
    currency: str
    period_limit_minor: int = Field(ge=0)
    set_by: str
    set_at: AwareDatetime


class PriceLine(BaseModel):
    """A unit price in micro-units of the currency per unit of ``unit``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    operation: UsageOperation
    model: str | None = None
    unit: str = Field(pattern=r"^(call|input_token|output_token|second)$")
    provider_cost_micro: int = Field(ge=0)
    """What the provider charges per unit (for the margin view). 0 when Suncly bears no cost."""
    price_micro: int = Field(ge=0)
    """What the customer pays per unit."""


class PriceTable(BaseModel):
    """Versioned pricing configuration. Every ledger line names the version that priced it."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1)
    currency: str
    lines: list[PriceLine]

    def line_for(self, provider: str, operation: UsageOperation, model: str | None) -> PriceLine:
        candidates = [
            line
            for line in self.lines
            if line.provider == provider
            and line.operation is operation
            and (line.model is None or line.model == model)
        ]
        if not candidates:
            raise KeyError(f"no price for {provider}/{operation.value}/{model}")
        # A model-specific line wins over a provider-wide one.
        return sorted(candidates, key=lambda line: line.model is None)[0]


def price_usage(table: PriceTable, line: PriceLine, measured: JsonObject) -> tuple[int, int]:
    """``(provider_cost_minor, billable_minor)`` for measured usage under one price line."""
    if line.unit == "call":
        units = int(measured.get("calls", 1))
    elif line.unit == "input_token":
        units = int(measured.get("input_tokens", 0))
    elif line.unit == "output_token":
        units = int(measured.get("output_tokens", 0))
    else:
        units = int(measured.get("seconds", 0))
    return (
        micro_to_minor(units * line.provider_cost_micro, table.currency),
        micro_to_minor(units * line.price_micro, table.currency),
    )


def price_model_usage(
    table: PriceTable, provider: str, model: str, measured: JsonObject
) -> tuple[int, int]:
    """Input and output tokens priced separately; both sides summed."""
    totals = [0, 0]
    for unit_key in ("input_token", "output_token"):
        lines = [
            line
            for line in table.lines
            if line.provider == provider
            and line.unit == unit_key
            and (line.model is None or line.model == model)
        ]
        if not lines:
            raise KeyError(f"no {unit_key} price for {provider}/{model}")
        line = sorted(lines, key=lambda candidate: candidate.model is None)[0]
        cost, billable = price_usage(table, line, measured)
        totals[0] += cost
        totals[1] += billable
    return totals[0], totals[1]
