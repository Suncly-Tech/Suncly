"""Subscriptions, entitlements and the record of processed payment-provider events.

Stripe is the payment provider, in test mode. It receives settled billing
events and sends webhooks; it is never the source of truth for the budget a
tenant has left: that is the ledger (``domain/ledger.py``).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]


class Plan(BaseModel):
    """A platform subscription plan, from the versioned pricing configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    name: str
    currency: str
    #: Usage included in each billing period, in minor units of the currency.
    included_allowance_minor: int = Field(ge=0)
    #: The provider's price id for the subscription (Stripe test-mode price).
    provider_price_id: str | None = None
    #: The provider's meter event name for overage reporting.
    overage_meter_event_name: str | None = None
    #: Disclosed overage: whether usage beyond the allowance is billed at the price table.
    overage_billed: bool = True


class SubscriptionStatus(StrEnum):
    NONE = "none"
    """No subscription: nothing hosted may run (only the sample workspace)."""
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    """A payment failed: existing evidence stays readable, new attestations are refused."""
    CANCELED = "canceled"
    UNPAID = "unpaid"


#: Statuses that entitle a tenant to start new attestations.
ENTITLED_STATUSES = frozenset({SubscriptionStatus.TRIALING, SubscriptionStatus.ACTIVE})


class Subscription(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: UUID
    plan_id: str
    status: SubscriptionStatus
    provider: str = "stripe"
    provider_customer_id: str | None = None
    provider_subscription_id: str | None = None
    current_period_start: AwareDatetime | None = None
    current_period_end: AwareDatetime | None = None
    #: The provider event time that last changed this record (out-of-order guard).
    provider_updated_at: AwareDatetime | None = None
    updated_at: AwareDatetime


class Entitlement(BaseModel):
    """What the tenant may do right now, derived from subscription and ledger."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: UUID
    can_start_attestations: bool
    reason: str
    subscription_status: SubscriptionStatus
    plan_id: str | None
    currency: str | None
    included_allowance_minor: int
    allowance_used_minor: int
    settled_minor: int
    reserved_minor: int
    unknown_minor_held: int
    period_limit_minor: int | None
    remaining_minor: int | None
    """What may still be reserved under the hard limit; None when no limit is set."""


class ProviderEvent(BaseModel):
    """A payment-provider webhook event, recorded for idempotent processing."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: str
    event_id: str = Field(min_length=1, max_length=128)
    event_type: str = Field(min_length=1, max_length=128)
    provider_created_at: AwareDatetime
    received_at: AwareDatetime
    processed: bool
    result: str = ""


class MeterReport(BaseModel):
    """One usage event reported to the provider's meter, keyed by the event id."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    usage_event_id: UUID
    provider: str
    identifier: str
    """The provider-side idempotency identifier (the usage event id)."""
    reported_at: AwareDatetime
    provider_response_id: str | None = None
