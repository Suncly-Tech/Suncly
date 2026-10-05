"""Versioned pricing configuration: the price table and the plan catalog.

The values below are the **test** price table. They exist so the ledger,
reservations and Stripe test-mode reporting can be exercised end to end.
They are not commercial prices; a real price table is a founder decision and
arrives as a new version, never by editing an old one (every ledger line
names the version that priced it).
"""

from __future__ import annotations

from suncly.domain.billing import Plan
from suncly.domain.ledger import PriceLine, PriceTable, UsageOperation

#: The Anthropic list prices (USD per million tokens, 2026-09-25) converted to EUR micro-units
#: at parity for the test table. Provider cost and customer price are kept separate so the
#: margin view works; the customer price here equals the provider cost (no markup in test).
_ANTHROPIC_MODELS = {
    "claude-opus-5-5": (4_000_000, 20_000_000),
    "claude-sonnet-5-5": (2_000_000, 10_000_000),
    "claude-haiku-4-5": (1_000_000, 5_000_000),
}


def _model_lines() -> list[PriceLine]:
    lines: list[PriceLine] = []
    for model, (input_per_million, output_per_million) in _ANTHROPIC_MODELS.items():
        per_input = input_per_million // 1_000_000
        per_output = output_per_million // 1_000_000
        for operation in (UsageOperation.DRAFT, UsageOperation.JUDGE):
            lines.append(
                PriceLine(
                    provider="anthropic",
                    operation=operation,
                    model=model,
                    unit="input_token",
                    provider_cost_micro=per_input,
                    price_micro=per_input,
                )
            )
            lines.append(
                PriceLine(
                    provider="anthropic",
                    operation=operation,
                    model=model,
                    unit="output_token",
                    provider_cost_micro=per_output,
                    price_micro=per_output,
                )
            )
    return lines


TEST_PRICE_TABLE = PriceTable(
    version="2026-10-test",
    currency="EUR",
    lines=[
        # One Runner attempt against the sandbox: Suncly's execution cost, 2 cents in test.
        PriceLine(
            provider="suncly-runner",
            operation=UsageOperation.AGENT_CALL,
            unit="call",
            provider_cost_micro=0,
            price_micro=20_000,
        ),
        PriceLine(
            provider="suncly-runner",
            operation=UsageOperation.PROBE,
            unit="call",
            provider_cost_micro=0,
            price_micro=20_000,
        ),
        PriceLine(
            provider="suncly-runner",
            operation=UsageOperation.EXTERNAL_TOOL,
            unit="call",
            provider_cost_micro=0,
            price_micro=500_000,
        ),
        # The offline fake provider is free and never leaves the process.
        PriceLine(
            provider="fake",
            operation=UsageOperation.DRAFT,
            unit="input_token",
            provider_cost_micro=0,
            price_micro=0,
        ),
        PriceLine(
            provider="fake",
            operation=UsageOperation.DRAFT,
            unit="output_token",
            provider_cost_micro=0,
            price_micro=0,
        ),
        PriceLine(
            provider="fake",
            operation=UsageOperation.JUDGE,
            unit="input_token",
            provider_cost_micro=0,
            price_micro=0,
        ),
        PriceLine(
            provider="fake",
            operation=UsageOperation.JUDGE,
            unit="output_token",
            provider_cost_micro=0,
            price_micro=0,
        ),
        *_model_lines(),
    ],
)

#: Test plans. ``provider_price_id`` values are placeholders for Stripe **test-mode** price ids
#: supplied through the environment (STRIPE_PRICE_<PLAN>); no live product exists.
TEST_PLANS = {
    "pilot": Plan(
        id="pilot",
        name="Pilot (test)",
        currency="EUR",
        included_allowance_minor=2_000,
        provider_price_id=None,
        overage_meter_event_name="suncly_usage_eur_cents",
        overage_billed=True,
    ),
    "team": Plan(
        id="team",
        name="Team (test)",
        currency="EUR",
        included_allowance_minor=10_000,
        provider_price_id=None,
        overage_meter_event_name="suncly_usage_eur_cents",
        overage_billed=True,
    ),
}

PRICE_TABLES = {TEST_PRICE_TABLE.version: TEST_PRICE_TABLE}


def price_table(version: str) -> PriceTable:
    try:
        return PRICE_TABLES[version]
    except KeyError as exc:
        raise KeyError(f"unknown price table version {version!r}") from exc


def plan_catalog(version: str, price_ids: dict[str, str] | None = None) -> dict[str, Plan]:
    """The plans of a catalog version, with provider price ids from the environment."""
    if version != "2026-10-test":
        raise KeyError(f"unknown plan catalog version {version!r}")
    plans = dict(TEST_PLANS)
    for plan_id, price_id in (price_ids or {}).items():
        if plan_id in plans:
            plans[plan_id] = plans[plan_id].model_copy(update={"provider_price_id": price_id})
    return plans
