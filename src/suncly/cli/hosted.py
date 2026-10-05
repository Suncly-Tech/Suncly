"""Commands of the hosted product: the API server, the worker, the dispatcher tick,
the CI gate, local tokens and key management. Thin: parse, wire, call, print."""

from __future__ import annotations

import json
import os
import sys
import threading
import uuid
from pathlib import Path
from typing import Any

import click

from suncly.adapters.app_config_loader import load_app_config
from suncly.adapters.app_wiring import build_app_services
from suncly.adapters.report.writer import read_report_folder
from suncly.cli import exit_codes
from suncly.cli.main import _config, handles_errors, main
from suncly.cli.output import Console
from suncly.core import integrity
from suncly.core.ci_gate import evaluate_gate
from suncly.core.jobs import JobHandler, WorkerLoop
from suncly.core.reevaluation import ReevaluationJobHandler, housekeeping_tick
from suncly.core.worker import AttestationJobHandler
from suncly.domain.errors import RefusedError
from suncly.ports.app_store import SigningKeyRecord

ExistingFolder = click.Path(exists=True, file_okay=False, path_type=Path)
ExistingFile = click.Path(exists=True, dir_okay=False, path_type=Path)


def _emit(payload: dict[str, Any]) -> None:
    click.echo(json.dumps(payload, indent=2, default=str))


@main.group()
def api() -> None:
    """The hosted HTTP API."""


@api.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", type=int, default=8000, show_default=True)
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def api_serve(ctx: click.Context, host: str, port: int, debug: bool) -> None:
    """Serve the API (uvicorn). Configuration comes from SUNCLY_* variables."""
    import uvicorn

    from suncly.adapters.api.app import create_app

    config = _config(ctx)
    app_config = load_app_config(os.environ)
    services = build_app_services(config, app_config, os.environ)
    uvicorn.run(create_app(services), host=host, port=port, log_level="info")


@api.command("openapi")
@click.option("--out", type=click.Path(dir_okay=False, path_type=Path), default=None)
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def api_openapi(ctx: click.Context, out: Path | None, debug: bool) -> None:
    """Print (or write) the OpenAPI document without starting a server."""
    from suncly.adapters.api.app import create_app

    config = _config(ctx)
    env = {**os.environ}
    env.setdefault("SUNCLY_LOCAL_AUTH_ENABLED", "1")
    env.setdefault("SUNCLY_LOCAL_AUTH_SECRET", "openapi-generation-only-secret")
    env.setdefault("SUNCLY_ENVIRONMENT", "test")
    app_config = load_app_config(env)
    services = build_app_services(config, app_config, env)
    document = create_app(services).openapi()
    text = json.dumps(document, indent=2)
    if out is None:
        click.echo(text)
    else:
        out.write_text(text + "\n", encoding="utf-8")
        click.echo(f"OpenAPI document written to {out}")


@main.group()
def worker() -> None:
    """The durable job worker and the dispatcher tick."""


def _handlers(services: Any) -> list[JobHandler]:
    return [AttestationJobHandler(services), ReevaluationJobHandler(services)]


@worker.command("run")
@click.option("--once", is_flag=True, help="Claim and run at most one job, then exit.")
@click.option("--worker-id", default=None, help="Identifier recorded on leases.")
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def worker_run(ctx: click.Context, once: bool, worker_id: str | None, debug: bool) -> None:
    """Run attestation jobs from the queue inside the trusted Runner boundary."""
    config = _config(ctx)
    app_config = load_app_config(os.environ)
    services = build_app_services(config, app_config, os.environ, worker=True)
    identity = (
        worker_id
        or f"{os.uname().nodename if hasattr(os, 'uname') else 'worker'}-{uuid.uuid4().hex[:8]}"
    )
    loop = WorkerLoop(
        services.app_store,
        services.clock,
        app_config.worker,
        _handlers(services),
        identity,
        on_log=lambda line: click.echo(line, err=True),
    )
    try:
        if once:
            ran = loop.run_once()
            click.echo("ran one job" if ran else "no job was claimable")
            return
        stop = threading.Event()
        loop.run_forever(stop)
    finally:
        services.close()


@worker.command("tick")
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def worker_tick(ctx: click.Context, debug: bool) -> None:
    """One housekeeping pass: recover leases, enqueue due re-evaluations, relay the outbox."""
    config = _config(ctx)
    app_config = load_app_config(os.environ)
    services = build_app_services(config, app_config, os.environ)
    try:
        _emit(housekeeping_tick(services))
    finally:
        services.close()


@main.command()
@click.argument("report_folder", type=ExistingFolder)
@click.option(
    "--trusted-keys",
    "trusted_keys_path",
    type=ExistingFile,
    default=None,
    help="JSON from GET /v1/keys (or `suncly keys export`). Without it, the key in the report "
    "is used and issuer trust is reported as not established.",
)
@click.option("--issuer", default=None, help="The issuer the attestation must come from.")
@click.option(
    "--policy-hash", default=None, help="The content hash of the policy in force (optional)."
)
@click.option("--json", "as_json", is_flag=True)
@click.option("--debug", is_flag=True)
@handles_errors
def gate(
    report_folder: Path,
    trusted_keys_path: Path | None,
    issuer: str | None,
    policy_hash: str | None,
    as_json: bool,
    debug: bool,
) -> None:
    """CI gate: exit 0 only when execution, verification and policy approval all hold.

    Exit codes: 0 approved; 10 execution did not complete; 11 verification failed;
    12 not approved by policy; 13 unreadable report.
    """
    from datetime import UTC, datetime

    from suncly.core.signing import b64url_decode

    try:
        result, transcripts = read_report_folder(report_folder)
    except (OSError, ValueError) as exc:
        raise RefusedError("The report folder cannot be read.", f"{exc}") from exc
    trusted: dict[str, SigningKeyRecord] = {}
    if trusted_keys_path is not None:
        loaded = json.loads(trusted_keys_path.read_text(encoding="utf-8"))
        for entry in loaded.get("keys", []):
            trusted[entry["key_id"]] = SigningKeyRecord(
                key_id=entry["key_id"],
                issuer=entry["issuer"],
                public_key=b64url_decode(entry["public_key"]),
                created_at=datetime.fromisoformat(entry["created_at"]),
                revoked_at=datetime.fromisoformat(entry["revoked_at"])
                if entry.get("revoked_at")
                else None,
                revocation_reason=entry.get("revocation_reason"),
            )
    trust = integrity.TrustContext(
        now=datetime.now(UTC),
        trusted_keys=trusted,
        expected_issuer=issuer,
        current_policy_hash=policy_hash,
    )
    outcome = evaluate_gate(result, transcripts, trust, require_trusted_issuer=bool(trusted))
    if as_json:
        _emit(outcome.to_json())
    else:
        console = Console()
        for name, ok, detail in (
            ("execution", outcome.execution_ok, outcome.execution_detail),
            ("verification", outcome.verification_ok, "signature, hashes, issuer, freshness"),
            ("policy", outcome.policy_ok, outcome.policy_detail),
        ):
            mark = console.style("ok  ", fg="green") if ok else console.style("FAIL", fg="red")
            console.line(f"{mark} {name}: {detail}")
        console.line()
        console.line(
            "Gate: approved."
            if outcome.approved
            else f"Gate: not approved (exit {outcome.exit_code}).",
            bold=True,
        )
    sys.exit(outcome.exit_code)


@main.group()
def auth() -> None:
    """Local development tokens (never available in production)."""


@auth.command("local-token")
@click.option("--subject", required=True, help="Stable subject identifier, e.g. a user id.")
@click.option("--email", default=None)
@click.option("--name", default=None)
@click.option("--ttl", type=int, default=3600, show_default=True, help="Seconds until expiry.")
@click.option("--debug", is_flag=True)
@handles_errors
def auth_local_token(
    subject: str, email: str | None, name: str | None, ttl: int, debug: bool
) -> None:
    """Print a token the local verifier accepts (needs SUNCLY_LOCAL_AUTH_SECRET)."""
    from suncly.adapters.auth import issue_local_token

    app_config = load_app_config(os.environ)
    secret = os.environ.get(app_config.auth.local_auth_secret_env, "")
    if app_config.is_production or not secret:
        raise RefusedError(
            "Local tokens are not available.",
            "Local authentication is off, or the environment is production.",
            "Set SUNCLY_LOCAL_AUTH_ENABLED=1 and SUNCLY_LOCAL_AUTH_SECRET outside production.",
        )
    click.echo(issue_local_token(secret, subject, email, name, ttl))


@main.group("trust")
def trust_group() -> None:
    """The trusted signing-key registry of this deployment."""


@trust_group.command("list")
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def trust_list(ctx: click.Context, debug: bool) -> None:
    """Export the registry as the JSON `suncly gate --trusted-keys` reads."""
    from suncly.core.signing import b64url

    config = _config(ctx)
    app_config = load_app_config(os.environ)
    services = build_app_services(config, app_config, os.environ)
    try:
        keys = services.app_store.list_signing_keys()
    finally:
        services.close()
    _emit(
        {
            "issuer": app_config.issuer,
            "keys": [
                {
                    "key_id": k.key_id,
                    "issuer": k.issuer,
                    "public_key": b64url(k.public_key),
                    "created_at": k.created_at.isoformat(),
                    "revoked_at": k.revoked_at.isoformat() if k.revoked_at else None,
                    "revocation_reason": k.revocation_reason,
                }
                for k in keys
            ],
        }
    )


@trust_group.command("revoke")
@click.argument("key_id")
@click.option("--reason", required=True)
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def trust_revoke(ctx: click.Context, key_id: str, reason: str, debug: bool) -> None:
    """Revoke a key: attestations issued after the revocation are no longer trusted."""
    config = _config(ctx)
    app_config = load_app_config(os.environ)
    services = build_app_services(config, app_config, os.environ)
    try:
        record = services.app_store.revoke_signing_key(key_id, services.clock.now(), reason)
    finally:
        services.close()
    if record is None:
        raise RefusedError("Unknown key id.", f"{key_id} is not registered.")
    click.echo(f"Key {key_id} revoked at {record.revoked_at}: {record.revocation_reason}")


@trust_group.command("rotate")
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def trust_rotate(ctx: click.Context, debug: bool) -> None:
    """Create a new signing key, register it, and make it current. The old key stays valid
    for attestations it issued; revoke it separately if it was compromised."""
    config = _config(ctx)
    app_config = load_app_config(os.environ)
    services = build_app_services(config, app_config, os.environ)
    try:
        signer = services.keys.create()
        services.app_store.add_signing_key(
            SigningKeyRecord(
                key_id=signer.key_id,
                issuer=app_config.issuer,
                public_key=signer.public_key,
                created_at=services.clock.now(),
            )
        )
    finally:
        services.close()
    click.echo(f"New current key {signer.key_id} registered for issuer {app_config.issuer}.")
    sys.exit(exit_codes.OK)


@main.group("judge")
def judge_group() -> None:
    """The model judge: calibration against the human-labelled dataset."""


@judge_group.command("calibrate")
@click.argument("dataset", type=ExistingFile)
@click.option(
    "--provider",
    type=click.Choice(["fake", "configured"]),
    default="fake",
    show_default=True,
    help="`fake` is the offline heuristic judge; `configured` uses SUNCLY_MODEL_* and the "
    "provider's API key (paid usage, never run in CI).",
)
@click.option("--repeats", type=int, default=1, show_default=True)
@click.option(
    "--max-false-approval-rate",
    type=float,
    default=None,
    help="Exit non-zero when the false approval rate is above this (reported otherwise).",
)
@click.option("--json", "as_json", is_flag=True)
@click.option("--debug", is_flag=True)
@handles_errors
def judge_calibrate(
    dataset: Path,
    provider: str,
    repeats: int,
    max_false_approval_rate: float | None,
    as_json: bool,
    debug: bool,
) -> None:
    """Run the judge over the labelled dataset and report false approvals and rejections."""
    from suncly.adapters.app_wiring import build_model_client
    from suncly.adapters.fake_model import HeuristicJudgeClient
    from suncly.core.model_calibration import calibrate_judge, summarize_for_humans
    from suncly.core.model_judge import ModelJudge
    from suncly.ports.model import ModelConfig

    if provider == "fake":
        config = ModelConfig(provider="fake", model="heuristic/1")
        client: Any = HeuristicJudgeClient()
    else:
        app_config = load_app_config(os.environ)
        if app_config.model is None:
            raise RefusedError(
                "No model provider is configured.",
                "SUNCLY_MODEL_PROVIDER and SUNCLY_MODEL are not set.",
            )
        config = app_config.model
        client = build_model_client(app_config, os.environ)
        if client is None:
            raise RefusedError("The configured provider has no client.", "Check the API key.")
    report = calibrate_judge(dataset, lambda: ModelJudge(client, config), repeats=repeats)
    summary = report.to_json()
    if as_json:
        _emit(summary)
    else:
        for line in summarize_for_humans(report):
            click.echo(line)
    if (
        max_false_approval_rate is not None
        and float(str(summary["false_approval_rate"])) > max_false_approval_rate
    ):
        sys.exit(exit_codes.REFUSED)
