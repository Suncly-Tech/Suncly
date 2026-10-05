"""The hosted workflow end to end: a real API server, a real worker process, Postgres, a
mock sandbox agent, the Stripe-shaped webhook in test mode, and the CI gate on the
exported evidence. Needs DATABASE_URL; skipped otherwise."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from suncly.adapters.auth import issue_local_token
from suncly.adapters.stripe_billing import FAKE_WEBHOOK_SECRET, sign_webhook_payload, webhook_event
from suncly.cli import exit_codes
from suncly.mock_agents import behaviours
from suncly.mock_agents.server import MockAgentServer

pytestmark = pytest.mark.e2e

SECRET = "live-test-secret-with-enough-length"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def backend(migrated_database: str, tmp_path: Path) -> Iterator[tuple[str, Path]]:
    """`suncly api serve` and `suncly worker run` as separate processes on the test database."""
    home = tmp_path / "home"
    port = free_port()
    env = {
        **os.environ,
        "DATABASE_URL": migrated_database,
        "SUNCLY_HOME": str(home),
        "SUNCLY_ENVIRONMENT": "test",
        "SUNCLY_NETWORK_MODE": "local",
        "SUNCLY_LOCAL_AUTH_ENABLED": "1",
        "SUNCLY_LOCAL_AUTH_SECRET": SECRET,
        "SUNCLY_BILLING_PROVIDER": "fake",
        "SUNCLY_ISSUER": "suncly-live-test",
        "SUNCLY_WORKER_POLL_S": "0.2",
        "SUNCLY_WORKER_HEARTBEAT_S": "1",
        "SUNCLY_RUN_TIMEOUT_S": "20",
        "NO_COLOR": "1",
    }
    env.pop("SUNCLY_MODEL_PROVIDER", None)
    base = [sys.executable, "-m", "suncly.cli.main", "--home", str(home)]
    api = subprocess.Popen(
        [*base, "api", "serve", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    worker = subprocess.Popen(
        [*base, "worker", "run", "--worker-id", "live-worker"],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            try:
                if httpx.get(f"{url}/v1/health", timeout=2).status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            if api.poll() is not None:
                raise RuntimeError(
                    f"the API exited early: {api.stderr.read() if api.stderr else ''}"
                )
            time.sleep(0.2)
        else:
            raise RuntimeError("the API did not come up")
        yield url, home
    finally:
        for process in (worker, api):
            process.terminate()
        for process in (worker, api):
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()


def test_the_full_hosted_workflow_against_a_local_backend(
    backend: tuple[str, Path], tmp_path: Path
) -> None:
    url, home = backend
    token = issue_local_token(SECRET, "live-reviewer", "reviewer@example.test", "Live Reviewer")
    client = httpx.Client(base_url=url, headers={"Authorization": f"Bearer {token}"}, timeout=30)

    # -- sign in, create the organization, entitle it through a verified test-mode webhook ---
    me = client.get("/v1/me").json()
    assert me["principal"]["subject"] == "live-reviewer" and me["organizations"] == []
    organization = client.post("/v1/organizations", json={"slug": "live-acme", "name": "Live Acme"})
    assert organization.status_code == 201, organization.text
    org = organization.json()["id"]
    payload = webhook_event(
        "evt_live_checkout",
        "checkout.session.completed",
        int(time.time()),
        {
            "id": "cs_live",
            "customer": "cus_live",
            "subscription": "sub_live",
            "metadata": {"suncly_organization_id": org, "suncly_plan_id": "pilot"},
        },
    )
    signature = sign_webhook_payload(payload, FAKE_WEBHOOK_SECRET, int(time.time()))
    hook = httpx.post(
        f"{url}/v1/webhooks/stripe",
        content=payload,
        headers={"Content-Type": "application/json", "Stripe-Signature": signature},
        timeout=30,
    )
    assert hook.status_code == 200 and "checkout applied" in hook.json()["result"], hook.text
    entitlement = client.get(f"/v1/organizations/{org}/subscription").json()["entitlement"]
    assert entitlement["can_start_attestations"] and entitlement["plan_id"] == "pilot"
    policy = {
        "configuration": {
            "policy_version": "live-1",
            "thresholds": {
                "low": {"min_pass_ratio": 0.9},
                "high": {"min_pass_ratio": 1.0, "require_human_signoff": True},
            },
        }
    }
    assert client.post(f"/v1/organizations/{org}/policies", json=policy).status_code == 201

    with MockAgentServer(behaviours.Honest()) as agent:
        # -- register, draft, approve, start -------------------------------------------------
        registration = client.post(
            f"/v1/organizations/{org}/agents",
            json={
                "name": "Honest sandbox",
                "card_url": agent.card_url,
                "risk_level": "low",
                "sandbox_declared": True,
                "credential": {"provider": "none"},
            },
        )
        assert registration.status_code == 201, registration.text
        reg = registration.json()["id"]
        drafted = client.post(
            f"/v1/organizations/{org}/agents/{reg}/contracts/draft",
            json={"source": "deterministic"},
        )
        assert drafted.status_code == 201, drafted.text
        contract = drafted.json()["contract"]["id"]
        assert drafted.json()["test_cases"], "the honest agent's card declares examples"
        approved = client.post(f"/v1/organizations/{org}/contracts/{contract}/approve")
        assert (
            approved.status_code == 200
            and approved.json()["contract"]["approved_by"] == "reviewer@example.test"
        )
        started = client.post(
            f"/v1/organizations/{org}/attestations",
            json={"registration_id": reg, "contract_id": contract, "runs": 2, "trigger": "ci"},
        )
        assert started.status_code == 202, started.text
        attestation = started.json()["attestation"]["id"]

        # -- the worker process runs it against the mock agent ---------------------------------
        deadline = time.monotonic() + 150
        item = started.json()
        while time.monotonic() < deadline:
            item = client.get(f"/v1/organizations/{org}/attestations/{attestation}").json()
            if item["attestation"]["status"] in ("completed", "failed", "cancelled", "invalidated"):
                break
            time.sleep(1)
        assert item["attestation"]["status"] == "completed", json.dumps(item, indent=2)[:3000]
        assert item["job"]["status"] == "succeeded" and item["progress"]["phase"] == "finished"
        assert agent.calls >= 2, "the Runner really called the sandbox"
        assert item["meta"]["payload_version"] == 2 and item["meta"]["policy_version"] == "live-1"

    # -- evidence, verification, the automatic decision ---------------------------------------
    evidence = client.get(f"/v1/organizations/{org}/attestations/{attestation}/evidence").json()
    result = evidence["result"]
    assert (
        result["decisions"][-1]["outcome"] == "approve"
        and result["decisions"][-1]["decided_by"] == "policy"
    )
    assert len(result["runs"]) == len(evidence["transcripts"]) == 2 * len(result["test_cases"])
    for transcript in evidence["transcripts"].values():
        assert "Authorization" not in transcript or "REDACTED" in transcript
    verification = client.get(
        f"/v1/organizations/{org}/attestations/{attestation}/verification"
    ).json()
    assert verification["cryptographic"]["ok"] and verification["issuer_trust"]["ok"]
    assert verification["freshness"]["ok"] and verification["policy"]["ok"]
    usage = client.get(f"/v1/organizations/{org}/usage").json()
    assert usage["reservations"][-1]["state"] == "settled"
    assert sum(e["billable_minor"] for e in usage["events"]) > 0
    assert (
        client.post(
            f"/v1/organizations/{org}/attestations/{attestation}/decisions",
            json={
                "outcome": "block",
                "rationale": "Only a flagged attestation is resolved by a person.",
            },
        ).status_code
        == 409
    )

    # -- the CI gate on the exported report folder, with the deployment's trusted keys ---------
    folder = tmp_path / "report"
    (folder / "transcripts").mkdir(parents=True)
    (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
    for run_id, text in evidence["transcripts"].items():
        (folder / "transcripts" / f"{run_id}.json").write_text(text, encoding="utf-8")
    keys = tmp_path / "keys.json"
    keys.write_text(json.dumps(client.get("/v1/keys").json()), encoding="utf-8")
    gate = subprocess.run(
        [
            sys.executable,
            "-m",
            "suncly.cli.main",
            "--home",
            str(home),
            "gate",
            str(folder),
            "--trusted-keys",
            str(keys),
            "--issuer",
            "suncly-live-test",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "NO_COLOR": "1"},
        check=False,
    )
    assert gate.returncode == exit_codes.OK, gate.stdout + gate.stderr
    verdict = json.loads(gate.stdout)
    assert (
        verdict["approved"]
        and verdict["execution"]["ok"]
        and verdict["verification"]["accepted"]
        and verdict["policy"]["ok"]
    )
    wrong_issuer = subprocess.run(
        [
            sys.executable,
            "-m",
            "suncly.cli.main",
            "--home",
            str(home),
            "gate",
            str(folder),
            "--trusted-keys",
            str(keys),
            "--issuer",
            "someone-else",
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "NO_COLOR": "1"},
        check=False,
    )
    assert wrong_issuer.returncode == 11, wrong_issuer.stdout + wrong_issuer.stderr

    # -- a stranger sees nothing ---------------------------------------------------------------
    stranger = httpx.Client(
        base_url=url,
        headers={"Authorization": f"Bearer {issue_local_token(SECRET, 'stranger')}"},
        timeout=30,
    )
    assert stranger.get(f"/v1/organizations/{org}/attestations/{attestation}").status_code == 404
    assert (
        stranger.get(f"/v1/organizations/{org}/attestations/{attestation}/evidence").status_code
        == 404
    )
