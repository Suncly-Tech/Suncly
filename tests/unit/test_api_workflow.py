"""The HTTP API on local fakes: authentication, tenancy, roles, the workflow, the envelope."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from suncly.adapters.api.app import create_app
from suncly.adapters.auth import issue_local_token
from suncly.adapters.stripe_billing import FAKE_WEBHOOK_SECRET, sign_webhook_payload, webhook_event
from suncly.domain.models import RiskLevel
from suncly.domain.policy import RiskThresholds
from tests.fakes import FakeClock, StaticFetcher, card_text, passing_executor
from tests.hosted import LOCAL_SECRET, HostedWorld, build_world

pytestmark = pytest.mark.api

CARD_URL = "https://agent.example.test/.well-known/agent-card.json"


@pytest.fixture
def world(tmp_path: Path) -> HostedWorld:
    clock = FakeClock()
    executor = passing_executor(clock)
    return build_world(
        tmp_path,
        fetcher=StaticFetcher({CARD_URL: card_text()}, clock),
        executor_factory=lambda registration: executor,
        clock=clock,
    )


@pytest.fixture
def client(world: HostedWorld) -> TestClient:
    return TestClient(create_app(world.services), raise_server_exceptions=False)


def auth(world: HostedWorld, subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {world.token(subject)}"}


def envelope(response: Any) -> dict[str, Any]:
    body = response.json()
    assert set(body) == {"error"}, body
    error = body["error"]
    assert set(error) == {"code", "message", "detail", "next_step", "request_id"}, error
    assert error["code"] and error["message"] and error["request_id"]
    assert response.headers["X-Request-Id"] == error["request_id"]
    return error  # type: ignore[no-any-return]


def create_org(
    client: TestClient, world: HostedWorld, subject: str, slug: str, subscribed: bool = True
) -> str:
    response = client.post(
        "/v1/organizations", json={"slug": slug, "name": slug.title()}, headers=auth(world, subject)
    )
    assert response.status_code == 201, response.text
    assert response.json()["role"] == "administrator"
    org_id = str(response.json()["id"])
    if subscribed:
        world.subscribe(world.services.app_store.get_organization(UUID(org_id)))  # type: ignore[arg-type]
    return org_id


def register(
    client: TestClient, world: HostedWorld, subject: str, org: str, **overrides: Any
) -> dict[str, Any]:
    body = {
        "name": "Sandbox agent",
        "card_url": CARD_URL,
        "risk_level": "low",
        "owner": "team",
        "sandbox_declared": True,
        "credential": {"provider": "none"},
    }
    body.update(overrides)
    response = client.post(
        f"/v1/organizations/{org}/agents", json=body, headers=auth(world, subject)
    )
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


def approved_contract(
    client: TestClient, world: HostedWorld, subject: str, org: str, registration_id: str
) -> str:
    drafted = client.post(
        f"/v1/organizations/{org}/agents/{registration_id}/contracts/draft",
        json={"source": "deterministic"},
        headers=auth(world, subject),
    )
    assert drafted.status_code == 201, drafted.text
    contract_id = drafted.json()["contract"]["id"]
    assert drafted.json()["contract"]["status"] == "draft" and drafted.json()["test_cases"]
    approved = client.post(
        f"/v1/organizations/{org}/contracts/{contract_id}/approve", headers=auth(world, subject)
    )
    assert approved.status_code == 200 and approved.json()["contract"]["status"] == "approved"
    assert approved.json()["contract"]["approved_by"] == f"{subject}@example.test"
    return str(contract_id)


def start(
    client: TestClient,
    world: HostedWorld,
    subject: str,
    org: str,
    registration_id: str,
    contract_id: str,
    **extra: Any,
) -> Any:
    return client.post(
        f"/v1/organizations/{org}/attestations",
        json={"registration_id": registration_id, "contract_id": contract_id, "runs": 2, **extra},
        headers=auth(world, subject),
    )


# -- authentication and the envelope -------------------------------------------------------


def test_requests_without_a_valid_bearer_token_get_401_in_the_envelope(
    client: TestClient, world: HostedWorld
) -> None:
    assert client.get("/v1/health").status_code == 200
    missing = client.get("/v1/me")
    assert missing.status_code == 401 and "bearer" in envelope(missing)["message"].lower()
    garbage = client.get("/v1/me", headers={"Authorization": "Bearer not.a.token"})
    assert garbage.status_code == 401 and envelope(garbage)
    expired = issue_local_token(LOCAL_SECRET, "alice", ttl_seconds=-5)
    gone = client.get("/v1/me", headers={"Authorization": f"Bearer {expired}"})
    assert gone.status_code == 401 and "expired" in envelope(gone)["message"].lower()
    wrong_scheme = client.get("/v1/me", headers={"Authorization": f"Basic {world.token('alice')}"})
    assert wrong_scheme.status_code == 401
    own = client.get("/v1/me", headers={**auth(world, "alice"), "X-Request-Id": "req-123"})
    assert own.status_code == 200 and own.headers["X-Request-Id"] == "req-123"
    assert own.json()["principal"]["subject"] == "alice" and own.json()["organizations"] == []


def test_validation_errors_use_the_same_envelope(client: TestClient, world: HostedWorld) -> None:
    response = client.post(
        "/v1/organizations", json={"slug": "Not Valid!", "name": ""}, headers=auth(world, "alice")
    )
    assert response.status_code == 422
    error = envelope(response)
    assert "slug" in error["detail"]


# -- tenancy and roles ----------------------------------------------------------------------


def test_organizations_are_invisible_to_non_members(client: TestClient, world: HostedWorld) -> None:
    acme = create_org(client, world, "alice", "acme")
    assert (
        client.get("/v1/me", headers=auth(world, "alice")).json()["organizations"][0]["slug"]
        == "acme"
    )
    assert (
        client.post(
            "/v1/organizations", json={"slug": "acme", "name": "Again"}, headers=auth(world, "bob")
        ).status_code
        == 409
    )
    for path in (
        f"/v1/organizations/{acme}",
        f"/v1/organizations/{acme}/agents",
        f"/v1/organizations/{acme}/attestations",
        f"/v1/organizations/{acme}/usage",
        f"/v1/organizations/{acme}/policies",
        f"/v1/organizations/{uuid4()}",
    ):
        response = client.get(path, headers=auth(world, "bob"))
        assert response.status_code == 404, path
        assert (
            "not a member" in envelope(response)["message"]
            or "does not exist" in envelope(response)["message"]
        )
    assert client.get(f"/v1/organizations/{acme}", headers=auth(world, "alice")).status_code == 200


def test_roles_gate_every_write(client: TestClient, world: HostedWorld) -> None:
    acme = create_org(client, world, "alice", "acme")
    added = client.post(
        f"/v1/organizations/{acme}/members",
        json={"subject": "bob", "role": "viewer"},
        headers=auth(world, "alice"),
    )
    assert added.status_code == 201 and added.json()["role"] == "viewer"
    assert (
        client.post(
            f"/v1/organizations/{acme}/members",
            json={"subject": "carol", "role": "reviewer"},
            headers=auth(world, "alice"),
        ).status_code
        == 201
    )
    assert client.get(f"/v1/organizations/{acme}/agents", headers=auth(world, "bob")).json() == {
        "agents": []
    }
    forbidden = client.post(
        f"/v1/organizations/{acme}/agents",
        json={
            "name": "x",
            "card_url": CARD_URL,
            "sandbox_declared": True,
            "credential": {"provider": "none"},
        },
        headers=auth(world, "bob"),
    )
    assert forbidden.status_code == 403 and "role" in envelope(forbidden)["message"]
    assert (
        client.post(
            f"/v1/organizations/{acme}/members",
            json={"subject": "dave", "role": "viewer"},
            headers=auth(world, "bob"),
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/organizations/{acme}/members",
            json={"subject": "dave", "role": "viewer"},
            headers=auth(world, "carol"),
        ).status_code
        == 403
    )
    registration = register(client, world, "carol", acme)
    assert (
        registration["organization_id"] == acme
        and registration["created_by"] == "carol@example.test"
    )
    policy = {
        "configuration": {"policy_version": "v1", "thresholds": {"low": {"min_pass_ratio": 0.9}}}
    }
    assert (
        client.post(
            f"/v1/organizations/{acme}/policies", json=policy, headers=auth(world, "carol")
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/v1/organizations/{acme}/policies", json=policy, headers=auth(world, "alice")
        ).status_code
        == 201
    )
    assert (
        client.put(
            f"/v1/organizations/{acme}/spending-limit",
            json={"period_limit_minor": 500},
            headers=auth(world, "carol"),
        ).status_code
        == 403
    )
    members = client.get(f"/v1/organizations/{acme}/members", headers=auth(world, "bob")).json()[
        "members"
    ]
    assert {m["subject"] for m in members} == {"alice", "bob", "carol"}


def test_bodies_cannot_name_the_organization_or_the_reviewer(
    client: TestClient, world: HostedWorld
) -> None:
    acme = create_org(client, world, "alice", "acme")
    other = create_org(client, world, "mallory", "other")
    smuggled = client.post(
        f"/v1/organizations/{acme}/agents",
        json={
            "name": "x",
            "card_url": CARD_URL,
            "sandbox_declared": True,
            "credential": {"provider": "none"},
            "organization_id": other,
        },
        headers=auth(world, "alice"),
    )
    assert smuggled.status_code == 422 and "organization_id" in envelope(smuggled)["detail"]
    registration = register(client, world, "alice", acme)
    contract = approved_contract(client, world, "alice", acme, registration["id"])
    started = start(client, world, "alice", acme, registration["id"], contract)
    assert started.status_code == 202
    attestation_id = started.json()["attestation"]["id"]
    assert world.worker().run_once()
    forged = client.post(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/decisions",
        json={
            "outcome": "approve",
            "rationale": "the sandbox behaved as the contract says it should",
            "decided_by": "mallory",
        },
        headers=auth(world, "alice"),
    )
    assert forged.status_code == 422 and "decided_by" in envelope(forged)["detail"]
    # Mallory is an administrator elsewhere; Acme's attestation does not exist for them.
    for path in (
        f"/v1/organizations/{acme}/attestations/{attestation_id}",
        f"/v1/organizations/{acme}/attestations/{attestation_id}/evidence",
        f"/v1/organizations/{other}/attestations/{attestation_id}",
        f"/v1/organizations/{other}/attestations/{attestation_id}/evidence",
        f"/v1/organizations/{other}/contracts/{contract}",
        f"/v1/organizations/{other}/agents/{registration['id']}",
    ):
        assert client.get(path, headers=auth(world, "mallory")).status_code == 404, path
    cross = start(client, world, "mallory", other, registration["id"], contract)
    assert cross.status_code == 404
    assert (
        client.post(
            f"/v1/organizations/{other}/contracts/{contract}/approve",
            headers=auth(world, "mallory"),
        ).status_code
        == 404
    )


# -- the workflow ----------------------------------------------------------------------------


def test_the_workflow_from_registration_to_a_resolved_decision(
    client: TestClient, world: HostedWorld
) -> None:
    acme = create_org(client, world, "alice", "acme")
    client.post(
        f"/v1/organizations/{acme}/members",
        json={"subject": "bob", "role": "viewer"},
        headers=auth(world, "alice"),
    )
    client.post(
        f"/v1/organizations/{acme}/members",
        json={"subject": "carol", "role": "reviewer"},
        headers=auth(world, "alice"),
    )
    registration = register(client, world, "carol", acme)
    contract = approved_contract(client, world, "carol", acme, registration["id"])
    listed = client.get(
        f"/v1/organizations/{acme}/agents/{registration['id']}/contracts",
        headers=auth(world, "bob"),
    ).json()
    assert [c["id"] for c in listed["contracts"]] == [contract]

    started = start(client, world, "carol", acme, registration["id"], contract)
    assert started.status_code == 202, started.text
    body = started.json()
    attestation_id = body["attestation"]["id"]
    assert body["attestation"]["status"] == "queued" and body["job"]["status"] == "queued"
    assert (
        body["progress"]["phase"] == "queued" and body["meta"]["created_by"] == "carol@example.test"
    )
    assert (
        client.post(
            f"/v1/organizations/{acme}/attestations",
            json={"registration_id": registration["id"], "contract_id": contract},
            headers=auth(world, "bob"),
        ).status_code
        == 403
    )

    assert world.worker().run_once()
    fetched = client.get(
        f"/v1/organizations/{acme}/attestations/{attestation_id}", headers=auth(world, "bob")
    ).json()
    assert (
        fetched["attestation"]["status"] == "completed" and fetched["job"]["status"] == "succeeded"
    )
    assert fetched["progress"]["phase"] == "finished" and fetched["progress"]["recorded_runs"] > 0
    assert fetched["meta"]["payload_version"] == 2 and fetched["meta"]["issued_at"]
    by_registration = client.get(
        f"/v1/organizations/{acme}/attestations",
        params={"registration_id": registration["id"]},
        headers=auth(world, "bob"),
    ).json()
    assert [a["attestation"]["id"] for a in by_registration["attestations"]] == [attestation_id]

    evidence = client.get(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/evidence",
        headers=auth(world, "bob"),
    ).json()
    result = evidence["result"]
    assert result["attestation"]["status"] == "completed"
    assert (
        result["decisions"][-1]["outcome"] == "flag"
        and result["decisions"][-1]["policy_version"] == "unconfigured"
    )
    assert result["signature_payload"]["payload_version"] == 2 and evidence["transcripts"]
    assert (
        "flag" in evidence["summary"]["decision_line"].lower()
        or "review" in evidence["summary"]["decision_line"].lower()
    )
    verification = client.get(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/verification",
        headers=auth(world, "bob"),
    ).json()
    assert (
        verification["cryptographic"]["ok"]
        and verification["issuer_trust"]["ok"]
        and verification["freshness"]["ok"]
    )
    assert verification["policy"]["ok"] is False, "a flagged attestation is not policy-approved"
    keys = client.get("/v1/keys").json()
    assert keys["issuer"] == world.services.app_config.issuer
    assert result["attestation"]["signing_key_id"] in {k["key_id"] for k in keys["keys"]}

    resolution = {
        "outcome": "approve",
        "rationale": "Reviewed the transcripts: every answer matches the sandbox fixtures.",
    }
    assert (
        client.post(
            f"/v1/organizations/{acme}/attestations/{attestation_id}/decisions",
            json=resolution,
            headers=auth(world, "bob"),
        ).status_code
        == 403
    )
    too_short = client.post(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/decisions",
        json={"outcome": "approve", "rationale": "ok"},
        headers=auth(world, "carol"),
    )
    assert too_short.status_code == 422
    flagged_again = client.post(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/decisions",
        json={**resolution, "outcome": "flag"},
        headers=auth(world, "carol"),
    )
    assert flagged_again.status_code == 422
    resolved = client.post(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/decisions",
        json=resolution,
        headers=auth(world, "carol"),
    )
    assert resolved.status_code == 201, resolved.text
    assert resolved.json()["decision"]["outcome"] == "approve"
    assert resolved.json()["decision"]["decided_by"] == "carol@example.test"
    assert resolved.json()["note"]["reviewer_subject"] == "carol"
    again = client.post(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/decisions",
        json=resolution,
        headers=auth(world, "carol"),
    )
    assert again.status_code == 409 and "not waiting" in envelope(again)["message"]
    after = client.get(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/evidence",
        headers=auth(world, "carol"),
    ).json()["result"]
    assert [d["outcome"] for d in after["decisions"]] == ["flag", "approve"]
    assert after["decision_notes"][0]["rationale"].startswith("Reviewed the transcripts")
    verified_after = client.get(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/verification",
        headers=auth(world, "bob"),
    ).json()
    assert verified_after["cryptographic"]["ok"], "a human decision never invalidates the signature"
    assert verified_after["policy"]["ok"] is True


def test_a_customer_policy_approves_automatically_and_the_gate_reads_it(
    client: TestClient, world: HostedWorld
) -> None:
    acme = create_org(client, world, "alice", "acme")
    policy = {
        "configuration": {
            "policy_version": "acme-2026-10",
            "thresholds": {
                "low": RiskThresholds(min_pass_ratio=0.5).model_dump(),
                "high": RiskThresholds(min_pass_ratio=1.0, require_human_signoff=True).model_dump(),
            },
        }
    }
    created = client.post(
        f"/v1/organizations/{acme}/policies", json=policy, headers=auth(world, "alice")
    )
    assert created.status_code == 201 and created.json()["content_hash"].startswith("sha256:")
    assert (
        client.post(
            f"/v1/organizations/{acme}/policies",
            json={
                "configuration": {
                    "policy_version": "x",
                    "thresholds": {},
                    "high_risk_requires_human": False,
                }
            },
            headers=auth(world, "alice"),
        ).status_code
        == 422
    )
    registration = register(client, world, "alice", acme)
    contract = approved_contract(client, world, "alice", acme, registration["id"])
    started = start(client, world, "alice", acme, registration["id"], contract, trigger="ci")
    assert started.status_code == 202 and started.json()["attestation"]["trigger"] == "ci"
    attestation_id = started.json()["attestation"]["id"]
    assert world.worker().run_once()
    evidence = client.get(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/evidence",
        headers=auth(world, "alice"),
    ).json()
    decision = evidence["result"]["decisions"][-1]
    assert decision["outcome"] == "approve" and decision["policy_version"] == "acme-2026-10"
    verification = client.get(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/verification",
        headers=auth(world, "alice"),
    ).json()
    assert verification["policy"]["ok"] and verification["issuer_trust"]["ok"]
    high = register(client, world, "alice", acme, risk_level=RiskLevel.HIGH.value)
    high_contract = approved_contract(client, world, "alice", acme, high["id"])
    high_started = start(client, world, "alice", acme, high["id"], high_contract)
    assert world.worker().run_once()
    high_evidence = client.get(
        f"/v1/organizations/{acme}/attestations/{high_started.json()['attestation']['id']}/evidence",
        headers=auth(world, "alice"),
    ).json()
    assert high_evidence["result"]["decisions"][-1]["outcome"] == "flag"


def test_starting_is_refused_for_drafts_undeclared_sandboxes_and_over_the_limit(
    client: TestClient, world: HostedWorld
) -> None:
    acme = create_org(client, world, "alice", "acme")
    registration = register(client, world, "alice", acme)
    drafted = client.post(
        f"/v1/organizations/{acme}/agents/{registration['id']}/contracts/draft",
        json={},
        headers=auth(world, "alice"),
    ).json()
    draft_id = drafted["contract"]["id"]
    not_approved = start(client, world, "alice", acme, registration["id"], draft_id)
    assert not_approved.status_code == 409 and "not approved" in envelope(not_approved)["message"]
    rejected = client.post(
        f"/v1/organizations/{acme}/contracts/{draft_id}/reject", headers=auth(world, "alice")
    )
    assert rejected.status_code == 200 and rejected.json()["contract"]["status"] == "rejected"
    assert start(client, world, "alice", acme, registration["id"], draft_id).status_code == 409
    production_like = register(client, world, "alice", acme, sandbox_declared=False)
    contract = approved_contract(client, world, "alice", acme, production_like["id"])
    refused = start(client, world, "alice", acme, production_like["id"], contract)
    assert refused.status_code == 409 and "sandbox" in envelope(refused)["message"].lower()
    assert (
        client.put(
            f"/v1/organizations/{acme}/spending-limit",
            json={"period_limit_minor": 1},
            headers=auth(world, "alice"),
        ).status_code
        == 200
    )
    contract = approved_contract(client, world, "alice", acme, registration["id"])
    capped = start(client, world, "alice", acme, registration["id"], contract)
    assert capped.status_code == 402 and "limit" in envelope(capped)["message"].lower()
    usage = client.get(f"/v1/organizations/{acme}/usage", headers=auth(world, "alice")).json()
    assert usage["entitlement"]["can_start_attestations"] is True
    assert usage["reservations"] == [] and usage["events"] == []
    bad_card = client.post(
        f"/v1/organizations/{acme}/agents",
        json={
            "name": "x",
            "card_url": "http://169.254.169.254/card",
            "sandbox_declared": True,
            "credential": {"provider": "none"},
        },
        headers=auth(world, "alice"),
    )
    assert bad_card.status_code == 422


def test_cancelling_through_the_api_releases_the_reservation(
    client: TestClient, world: HostedWorld
) -> None:
    acme = create_org(client, world, "alice", "acme")
    registration = register(client, world, "alice", acme)
    contract = approved_contract(client, world, "alice", acme, registration["id"])
    attestation_id = start(client, world, "alice", acme, registration["id"], contract).json()[
        "attestation"
    ]["id"]
    usage = client.get(f"/v1/organizations/{acme}/usage", headers=auth(world, "alice")).json()
    assert usage["reservations"][-1]["state"] == "held"
    cancelled = client.post(
        f"/v1/organizations/{acme}/attestations/{attestation_id}/cancel",
        headers=auth(world, "alice"),
    )
    assert cancelled.status_code == 200 and cancelled.json()["attestation"]["status"] == "cancelled"
    assert cancelled.json()["job"]["status"] == "cancelled"
    usage = client.get(f"/v1/organizations/{acme}/usage", headers=auth(world, "alice")).json()
    assert usage["reservations"][-1]["state"] == "released"
    assert (
        client.post(
            f"/v1/organizations/{acme}/attestations/{attestation_id}/cancel",
            headers=auth(world, "alice"),
        ).status_code
        == 409
    )
    assert world.worker().run_once() is False
    archived = client.delete(
        f"/v1/organizations/{acme}/agents/{registration['id']}", headers=auth(world, "alice")
    )
    assert archived.status_code == 200 and archived.json()["archived_at"]
    assert start(client, world, "alice", acme, registration["id"], contract).status_code == 409


# -- billing in test mode and schedules -----------------------------------------------------


def test_billing_routes_use_the_test_catalog_and_verified_webhooks(
    client: TestClient, world: HostedWorld
) -> None:
    acme = create_org(client, world, "alice", "acme", subscribed=False)
    plans = client.get("/v1/billing/plans").json()
    assert {p["id"] for p in plans["plans"]} == {"pilot", "team"} and "No live" in plans["note"]
    checkout = client.post(
        f"/v1/organizations/{acme}/billing/checkout",
        json={"plan_id": "team"},
        headers=auth(world, "alice"),
    )
    assert checkout.status_code == 200 and checkout.json()["url"].startswith("http")
    assert (
        client.post(
            f"/v1/organizations/{acme}/billing/checkout",
            json={"plan_id": "enterprise"},
            headers=auth(world, "alice"),
        ).status_code
        == 404
    )
    no_portal = client.post(
        f"/v1/organizations/{acme}/billing/portal", headers=auth(world, "alice")
    )
    assert no_portal.status_code == 409, "no customer yet: nothing to open a portal for"
    before = client.get(
        f"/v1/organizations/{acme}/subscription", headers=auth(world, "alice")
    ).json()
    assert (
        before["subscription"] is None and before["entitlement"]["can_start_attestations"] is False
    )
    world.subscribe(world.services.app_store.get_organization(UUID(acme)))  # type: ignore[arg-type]
    portal = client.post(f"/v1/organizations/{acme}/billing/portal", headers=auth(world, "alice"))
    assert portal.status_code == 200 and portal.json()["url"]
    subscription = client.get(
        f"/v1/organizations/{acme}/subscription", headers=auth(world, "alice")
    ).json()
    assert (
        subscription["subscription"]["plan_id"] == "pilot"
        and subscription["entitlement"]["can_start_attestations"]
    )
    payload = webhook_event(
        "evt_api_1",
        "customer.subscription.updated",
        1_700_000_000,
        {
            "id": "sub_acme",
            "customer": "cus_acme",
            "status": "past_due",
            "metadata": {"organization_id": acme},
            "items": {"data": [{"price": {"id": "price_team"}}]},
        },
    )
    unsigned = client.post(
        "/v1/webhooks/stripe", content=payload, headers={"Content-Type": "application/json"}
    )
    assert unsigned.status_code in (400, 401, 403, 422, 502), unsigned.text
    envelope(unsigned)
    signature = sign_webhook_payload(payload, FAKE_WEBHOOK_SECRET, int(time.time()))
    signed = client.post(
        "/v1/webhooks/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    assert signed.status_code == 200, signed.text
    replay = client.post(
        "/v1/webhooks/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
    )
    assert replay.status_code == 200 and "duplicate" in replay.json()["result"].lower()
    reconciliation = client.get(
        f"/v1/organizations/{acme}/billing/reconciliation", headers=auth(world, "alice")
    )
    assert reconciliation.status_code == 200
    schedule = client.post(
        f"/v1/organizations/{acme}/schedules",
        json={
            "registration_id": register(client, world, "alice", acme)["id"],
            "interval_hours": 24,
            "runs": 2,
            "budget_limit": "20",
        },
        headers=auth(world, "alice"),
    )
    assert schedule.status_code == 201 and schedule.json()["interval_hours"] == 24
    assert (
        len(
            client.get(f"/v1/organizations/{acme}/schedules", headers=auth(world, "alice")).json()[
                "schedules"
            ]
        )
        == 1
    )


def test_the_openapi_document_describes_every_route(client: TestClient) -> None:
    document = client.get("/openapi.json").json()
    paths = set(document["paths"])
    for expected in (
        "/v1/organizations",
        "/v1/organizations/{organization_id}/agents",
        "/v1/organizations/{organization_id}/agents/{registration_id}/contracts/draft",
        "/v1/organizations/{organization_id}/attestations",
        "/v1/organizations/{organization_id}/attestations/{attestation_id}/evidence",
        "/v1/organizations/{organization_id}/attestations/{attestation_id}/verification",
        "/v1/organizations/{organization_id}/attestations/{attestation_id}/decisions",
        "/v1/organizations/{organization_id}/policies",
        "/v1/organizations/{organization_id}/usage",
        "/v1/webhooks/stripe",
        "/v1/keys",
    ):
        assert expected in paths, expected
    assert "error" in document["info"]["description"].lower()
