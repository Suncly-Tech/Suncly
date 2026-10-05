"""Stripe (test mode) and a fake behind the billing-provider port.

``StripeBillingProvider`` refuses any key that is not a test-mode key unless
the deployment explicitly allows live keys, so a misconfigured environment
can never create live products or charge anyone. Webhook signatures are
verified with the SDK's ``construct_event``; meter events carry the usage
event id as their idempotency ``identifier``.

``FakeBillingProvider`` records every call and verifies webhook signatures
with the same algorithm (through the SDK, offline), so the webhook tests
exercise real verification without a Stripe account.
"""

from __future__ import annotations

import json
from typing import Any, cast

from suncly.domain.errors import BillingError
from suncly.ports.billing_provider import (
    CheckoutRequest,
    CheckoutSession,
    MeterEventRequest,
    PortalSession,
    ProviderWebhook,
)

TEST_KEY_PREFIXES = ("sk_test_", "rk_test_")


def _webhook_from(event: Any) -> ProviderWebhook:
    data = event["data"] if isinstance(event, dict) else event.data
    data_dict = dict(data) if not isinstance(data, dict) else data
    obj: Any = data_dict.get("object")
    if obj is not None and hasattr(obj, "to_dict_recursive"):
        obj = obj.to_dict_recursive()
    elif obj is not None and hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    return ProviderWebhook(
        event_id=str(event["id"] if isinstance(event, dict) else event.id),
        event_type=str(event["type"] if isinstance(event, dict) else event.type),
        created=int(event["created"] if isinstance(event, dict) else event.created),
        data={"object": obj},
    )


def verify_with_sdk(payload: bytes, signature_header: str | None, secret: str) -> ProviderWebhook:
    import stripe

    try:
        event = stripe.Webhook.construct_event(payload, signature_header, secret)
    except stripe.SignatureVerificationError as exc:
        raise BillingError(
            "The webhook signature is invalid.", f"{exc}", "Check the webhook signing secret."
        ) from exc
    except ValueError as exc:
        raise BillingError("The webhook payload is not valid JSON.", f"{exc}") from exc
    return _webhook_from(event)


class StripeBillingProvider:
    name = "stripe"

    def __init__(self, secret_key: str, webhook_secret: str, allow_live: bool = False) -> None:
        if not secret_key.startswith(TEST_KEY_PREFIXES) and not allow_live:
            raise BillingError(
                "Only Stripe test-mode keys are accepted.",
                "The configured key is not a test key and live keys are not allowed.",
                "Use a key from the Stripe test dashboard (sk_test_...).",
            )
        if not webhook_secret:
            raise BillingError("A webhook signing secret is required.")
        import stripe

        self._stripe = stripe
        self._client = stripe.StripeClient(secret_key)
        self._webhook_secret = webhook_secret
        self.test_mode = secret_key.startswith(TEST_KEY_PREFIXES)

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        params: dict[str, Any] = {
            "mode": "subscription",
            "line_items": [{"price": request.provider_price_id, "quantity": 1}],
            "success_url": request.success_url,
            "cancel_url": request.cancel_url,
            "client_reference_id": request.organization_id,
            "metadata": {
                "suncly_organization_id": request.organization_id,
                "suncly_organization_slug": request.organization_slug,
                "suncly_plan_id": request.plan_id,
            },
            "subscription_data": {
                "metadata": {
                    "suncly_organization_id": request.organization_id,
                    "suncly_plan_id": request.plan_id,
                }
            },
        }
        if request.existing_customer_id:
            params["customer"] = request.existing_customer_id
        elif request.customer_email:
            params["customer_email"] = request.customer_email
        try:
            session = self._client.v1.checkout.sessions.create(cast(Any, params))
        except self._stripe.StripeError as exc:
            raise BillingError(
                "Stripe refused the checkout.", f"{exc.user_message or exc}"
            ) from exc
        return CheckoutSession(id=str(session.id), url=str(session.url))

    def create_portal(self, customer_id: str, return_url: str) -> PortalSession:
        try:
            session = self._client.v1.billing_portal.sessions.create(
                cast(Any, {"customer": customer_id, "return_url": return_url})
            )
        except self._stripe.StripeError as exc:
            raise BillingError(
                "Stripe refused the portal session.", f"{exc.user_message or exc}"
            ) from exc
        return PortalSession(url=str(session.url))

    def report_meter_event(self, request: MeterEventRequest) -> str | None:
        try:
            event = self._client.v1.billing.meter_events.create(
                cast(
                    Any,
                    {
                        "event_name": request.event_name,
                        "payload": {
                            "stripe_customer_id": request.customer_id,
                            "value": str(request.value),
                        },
                        "identifier": request.identifier,
                        "timestamp": request.timestamp,
                    },
                )
            )
        except self._stripe.StripeError as exc:
            raise BillingError(
                "Stripe refused the meter event.", f"{exc.user_message or exc}"
            ) from exc
        return str(getattr(event, "identifier", None) or request.identifier)

    def verify_webhook(self, payload: bytes, signature_header: str | None) -> ProviderWebhook:
        return verify_with_sdk(payload, signature_header, self._webhook_secret)


class FakeBillingProvider:
    """Records calls; verifies webhooks with the real signature algorithm and a test secret."""

    name = "stripe"

    def __init__(self, webhook_secret: str = "whsec_test_fake_secret") -> None:
        self.webhook_secret = webhook_secret
        self.checkouts: list[CheckoutRequest] = []
        self.portals: list[tuple[str, str]] = []
        self.meter_events: list[MeterEventRequest] = []
        self.fail_meter_events = False

    def create_checkout(self, request: CheckoutRequest) -> CheckoutSession:
        self.checkouts.append(request)
        return CheckoutSession(
            id=f"cs_test_{len(self.checkouts)}",
            url=f"https://checkout.stripe.com/c/pay/cs_test_{len(self.checkouts)}",
        )

    def create_portal(self, customer_id: str, return_url: str) -> PortalSession:
        self.portals.append((customer_id, return_url))
        return PortalSession(url=f"https://billing.stripe.com/p/session/test_{customer_id}")

    def report_meter_event(self, request: MeterEventRequest) -> str | None:
        if self.fail_meter_events:
            raise BillingError("The fake provider is set to fail.")
        self.meter_events.append(request)
        return f"mtr_{request.identifier}"

    def verify_webhook(self, payload: bytes, signature_header: str | None) -> ProviderWebhook:
        return verify_with_sdk(payload, signature_header, self.webhook_secret)


def sign_webhook_payload(payload: bytes, secret: str, timestamp: int) -> str:
    """The ``Stripe-Signature`` header value for ``payload``, as Stripe computes it."""
    import hashlib
    import hmac

    signed = f"{timestamp}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def webhook_event(event_id: str, event_type: str, created: int, obj: dict[str, Any]) -> bytes:
    """A minimal Stripe-shaped event payload for tests."""
    return json.dumps(
        {
            "id": event_id,
            "object": "event",
            "type": event_type,
            "created": created,
            "api_version": "2026-09-30.endive",
            "data": {"object": obj},
        }
    ).encode("utf-8")
