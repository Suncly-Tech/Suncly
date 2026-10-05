"""The payment provider port (Stripe in test mode, or a fake).

The provider sells the subscription and receives settled usage. It never
decides whether a tenant may run: entitlement and the hard limit come from the
ledger (``core/usage.py``).
"""

from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field

JsonObject = dict[str, Any]


class CheckoutRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    organization_id: str
    organization_slug: str
    plan_id: str
    provider_price_id: str
    customer_email: str | None
    existing_customer_id: str | None
    success_url: str
    cancel_url: str


class CheckoutSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    url: str


class PortalSession(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    url: str


class MeterEventRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    event_name: str
    customer_id: str
    value: int = Field(ge=0)
    identifier: str
    """Idempotency key: the usage event id. The provider deduplicates on it."""
    timestamp: int


class ProviderWebhook(BaseModel):
    """A verified webhook event, in provider-neutral form."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    event_id: str
    event_type: str
    created: int
    data: JsonObject


class BillingProvider(Protocol):
    name: str

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession: ...

    def create_portal(self, customer_id: str, return_url: str) -> PortalSession: ...

    def report_meter_event(self, request: MeterEventRequest) -> str | None:
        """Deliver one meter event; returns the provider's id when it gives one."""
        ...

    def verify_webhook(self, payload: bytes, signature_header: str | None) -> ProviderWebhook:
        """Verify the signature and parse the event, or raise ``BillingError``."""
        ...
