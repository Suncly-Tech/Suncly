"""The ``suncly`` command. It parses, prompts, prints and calls the core library (schema §6)."""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import Path
from typing import Any

import click

from suncly import __version__
from suncly.adapters.config_loader import load_config
from suncly.adapters.report.view import build_view
from suncly.adapters.report.writer import read_report_folder
from suncly.cli import exit_codes
from suncly.cli.output import Console, ProgressPrinter, print_summary
from suncly.cli.wiring import build_services
from suncly.core.attestation import (
    AttestationService,
    AttestOutcome,
    AttestRequest,
    DraftPresentation,
)
from suncly.core.config import Config
from suncly.core.verify import verify_result
from suncly.domain.contract_file import parse_contract_file
from suncly.domain.errors import ConfigError, RefusedError, SunclyError, VerificationFailedError
from suncly.domain.models import RiskLevel

PathOption = click.Path(path_type=Path)
ExistingFile = click.Path(exists=True, dir_okay=False, path_type=Path)
NewFile = click.Path(dir_okay=False, path_type=Path)
Folder = click.Path(file_okay=False, path_type=Path)
ExistingFolder = click.Path(exists=True, file_okay=False, path_type=Path)


def _fail(console: Console, error: SunclyError, debug: bool) -> None:
    if debug:
        raise error
    for sentence in (error.what, error.why, error.next_step):
        if sentence:
            styled = console.style(sentence, fg="red") if sentence is error.what else sentence
            click.echo(styled, err=True)
    sys.exit(exit_codes.code_for(error))


def handles_errors[**P, R](command: Callable[P, R]) -> Callable[P, R]:
    """Print Suncly errors as three sentences and exit with the documented code."""

    @wraps(command)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        debug = bool(kwargs.get("debug"))
        console = Console(stream=sys.stderr)
        try:
            return command(*args, **kwargs)
        except SunclyError as error:
            _fail(console, error, debug)
        except click.Abort:
            click.echo("Aborted.", err=True)
            sys.exit(exit_codes.REFUSED)
        except click.ClickException:
            raise
        except Exception as error:
            if debug:
                raise
            click.echo(console.style("Suncly hit an internal error.", fg="red"), err=True)
            click.echo(f"{type(error).__name__}: {error}", err=True)
            click.echo("Run the same command with --debug to see the traceback.", err=True)
            sys.exit(exit_codes.INTERNAL_ERROR)
        raise AssertionError("unreachable")

    return wrapper


def _config(ctx: click.Context) -> Config:
    config: Config = ctx.obj["config"]
    return config


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="suncly")
@click.option(
    "--home", type=PathOption, default=None, help="Suncly state folder (default ~/.suncly)."
)
@click.pass_context
def main(ctx: click.Context, home: Path | None) -> None:
    """Attestation for A2A agents: prove that an agent does what its Agent Card claims."""
    ctx.ensure_object(dict)
    try:
        ctx.obj["config"] = load_config(os.environ, home)
    except ConfigError as error:
        _fail(Console(stream=sys.stderr), error, debug=False)


def _parse_budget(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        budget = Decimal(value)
    except InvalidOperation as exc:
        raise click.BadParameter("must be a number of attempts, for example 40") from exc
    if budget < 0:
        raise click.BadParameter("cannot be negative")
    return budget


def interactive_approval(console: Console) -> Callable[[DraftPresentation], str | None]:
    def prompt(draft: DraftPresentation) -> str | None:
        console.heading(
            f"Draft contract version {draft.contract_version} for '{draft.card_name}' "
            f"({draft.source})"
        )
        console.line(f"card_hash {draft.card_hash}")
        console.line()
        console.table(
            ["#", "Skill", "Kind", "Input", "Criteria"],
            [
                [
                    str(i + 1),
                    tc.skill_id or "-",
                    tc.kind.value,
                    str(tc.input.get("text") or tc.input.get("parts"))[:60],
                    json.dumps(tc.criteria, sort_keys=True),
                ]
                for i, tc in enumerate(draft.test_cases)
            ],
        )
        for skill in draft.not_testable:
            console.line(
                f"Not testable: skill '{skill.skill_id}': {skill.reason}. "
                "It will be listed under what was NOT tested.",
                fg="yellow",
            )
        console.line()
        try:
            if not click.confirm(
                "Approve this contract and run it against the sandbox?", default=False
            ):
                return None
            approver: str = click.prompt("Your identifier, recorded as approved_by", type=str)
        except click.Abort:
            console.line()
            console.line(
                "No approval was given. To approve without a prompt, re-run with "
                "--approve-as <identifier>.",
                fg="yellow",
            )
            return None
        return approver.strip() or None

    return prompt


def _emit_json(payload: dict[str, Any]) -> None:
    click.echo(json.dumps(payload, indent=2, default=str))


def _outcome_json(outcome: AttestOutcome, exit_code: int) -> dict[str, Any]:
    bundle = outcome.bundle
    attestation = outcome.attestation
    return {
        "exit_code": exit_code,
        "exit_code_meaning": "0 means completed and signed, not approved",
        "kind": outcome.kind,
        "attestation": attestation.model_dump(mode="json") if attestation else None,
        "decision": outcome.decision.model_dump(mode="json") if outcome.decision else None,
        "results": [r.model_dump(mode="json") for r in bundle.results] if bundle else [],
        "not_tested": [i.model_dump(mode="json") for i in bundle.not_tested] if bundle else [],
        "report_dir": str(outcome.report_dir) if outcome.report_dir else None,
        "exported_contract_file": outcome.exported_contract_file,
    }


@main.command()
@click.argument("card_url")
@click.option(
    "--sandbox",
    "sandbox_declared",
    is_flag=True,
    help="Declare the endpoint a sandbox or dry-run endpoint (required to run anything).",
)
@click.option("--runs", type=click.IntRange(min=1), default=None, help="Repetitions per test case.")
@click.option("--budget", default=None, help="Budget in attempts (default: 2 x planned runs).")
@click.option(
    "--approve-as",
    "approve_as",
    default=None,
    help="Approve the drafted contract as this identifier.",
)
@click.option(
    "--contract",
    "contract_path",
    type=ExistingFile,
    default=None,
    help="Use a hand-written contract file.",
)
@click.option(
    "--export-draft",
    "export_path",
    type=NewFile,
    default=None,
    help="Write the draft to this file and stop.",
)
@click.option("--owner", default=None, help="agent.owner recorded on first sight of this agent.")
@click.option(
    "--risk-level",
    type=click.Choice([r.value for r in RiskLevel]),
    default=None,
    help="agent.risk_level recorded on first sight (default high).",
)
@click.option("--reports-dir", type=Folder, default=None, help="Report folders go here.")
@click.option("--json", "as_json", is_flag=True, help="Print a machine-readable result.")
@click.option("--debug", is_flag=True, help="Show tracebacks.")
@click.pass_context
@handles_errors
def attest(
    ctx: click.Context,
    card_url: str,
    sandbox_declared: bool,
    runs: int | None,
    budget: str | None,
    approve_as: str | None,
    contract_path: Path | None,
    export_path: Path | None,
    owner: str | None,
    risk_level: str | None,
    reports_dir: Path | None,
    as_json: bool,
    debug: bool,
) -> None:
    """Attest the agent whose Agent Card is at CARD_URL."""
    config = _config(ctx).with_overrides(runs=runs, reports_dir=reports_dir)
    console = Console(stream=sys.stderr if as_json else sys.stdout)
    progress = ProgressPrinter(console, quiet=as_json)
    # Every argument is validated before any resource (a store connection) is opened.
    contract_file = (
        parse_contract_file(contract_path.read_text(encoding="utf-8")) if contract_path else None
    )
    request = AttestRequest(
        card_url=card_url,
        sandbox_declared=sandbox_declared,
        runs=config.runs,
        budget_limit=_parse_budget(budget) if budget is not None else config.budget_limit,
        owner=owner or "unspecified",
        risk_level=RiskLevel(risk_level) if risk_level else RiskLevel.HIGH,
        approve_as=approve_as,
        approval_prompt=None if as_json else interactive_approval(console),
        contract_file=contract_file,
        export_draft=export_path is not None,
    )
    services = build_services(config, progress)
    try:
        outcome = AttestationService(services).attest(request)
    finally:
        services.store.close()
    if outcome.kind == "draft_exported":
        assert export_path is not None and outcome.exported_contract_file is not None
        export_path.write_text(outcome.exported_contract_file, encoding="utf-8")
        if as_json:
            _emit_json(_outcome_json(outcome, exit_codes.OK))
        else:
            console.line(f"Draft contract written to {export_path}. Edit it, then run:")
            console.line(
                f'  suncly attest "{card_url}" --sandbox --contract "{export_path}" '
                "--approve-as <your identifier>"
            )
        return
    code = exit_codes.OUTCOME_CODES[outcome.kind]
    if as_json:
        _emit_json(_outcome_json(outcome, code))
    else:
        assert outcome.bundle is not None and outcome.report_dir is not None
        print_summary(console, build_view(outcome.bundle), str(outcome.report_dir))
    sys.exit(code)


@main.command()
@click.option("--runs", type=click.IntRange(min=1), default=3, show_default=True)
@click.option("--reports-dir", type=Folder, default=None)
@click.option("--json", "as_json", is_flag=True)
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def demo(
    ctx: click.Context, runs: int, reports_dir: Path | None, as_json: bool, debug: bool
) -> None:
    """Start two bundled mock agents, honest and lying, and attest both."""
    from suncly.mock_agents.behaviours import Honest, Lying
    from suncly.mock_agents.server import MockAgentServer

    config = _config(ctx).with_overrides(runs=runs, reports_dir=reports_dir)
    console = Console(stream=sys.stderr if as_json else sys.stdout)
    progress = ProgressPrinter(console, quiet=as_json)
    outcomes: dict[str, dict[str, Any]] = {}
    exit_code = exit_codes.OK
    for behaviour in (Honest(), Lying()):
        with MockAgentServer(behaviour) as server:
            if not as_json:
                console.heading(f"=== {behaviour.name} mock agent at {server.card_url} ===")
                console.line(
                    "Bundled mock agents run on this machine and are sandboxes by construction."
                )
            services = build_services(config, progress)
            try:
                outcome = AttestationService(services).attest(
                    AttestRequest(
                        card_url=server.card_url,
                        sandbox_declared=True,
                        runs=config.runs,
                        budget_limit=config.budget_limit,
                        approve_as="suncly-demo",
                        owner="suncly-demo",
                    )
                )
            finally:
                services.store.close()
        code = exit_codes.OUTCOME_CODES[outcome.kind]
        exit_code = max(exit_code, code)
        outcomes[behaviour.name] = _outcome_json(outcome, code)
        if not as_json:
            assert outcome.bundle is not None and outcome.report_dir is not None
            print_summary(console, build_view(outcome.bundle), str(outcome.report_dir))
    if as_json:
        _emit_json({"exit_code": exit_code, "agents": outcomes})
    else:
        console.heading("Demo finished")
        console.line(
            "The honest agent's runs pass Layer 1; the lying agent's runs fail the declared "
            "output modes."
        )
        console.line(
            "Both decisions are 'flag': without a configured policy, a human reviews every result."
        )
    sys.exit(exit_code)


@main.command()
@click.argument("report_folder", type=ExistingFolder)
@click.option(
    "--public-key",
    "public_key_b64",
    default=None,
    help="Base64url public key obtained out of band; overrides the one in the report.",
)
@click.option("--json", "as_json", is_flag=True)
@click.option("--debug", is_flag=True)
@handles_errors
def verify(report_folder: Path, public_key_b64: str | None, as_json: bool, debug: bool) -> None:
    """Verify the signature, card hash, decision and transcripts of a report folder."""
    from suncly.core.signing import b64url_decode

    try:
        result, transcripts = read_report_folder(report_folder)
    except (OSError, ValueError) as exc:
        raise VerificationFailedError(
            "The report folder cannot be read.",
            f"{exc}",
            "Point suncly verify at a folder produced by suncly attest, with a result.json.",
        ) from exc
    public_key = b64url_decode(public_key_b64) if public_key_b64 else None
    verification = verify_result(result, transcripts, public_key)
    console = Console()
    if as_json:
        _emit_json(verification.to_json())
    else:
        for check in verification.checks:
            mark = (
                console.style("ok  ", fg="green") if check.ok else console.style("FAIL", fg="red")
            )
            console.line(f"{mark} {check.name}: {check.detail}")
        console.line()
        console.line(
            "Verification passed." if verification.ok else "Verification FAILED.", bold=True
        )
    sys.exit(exit_codes.OK if verification.ok else exit_codes.VERIFICATION_FAILED)


@main.group()
def keys() -> None:
    """Deployment signing keys."""


@keys.command("init")
@click.option("--new", "force_new", is_flag=True, help="Create another key and make it current.")
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def keys_init(ctx: click.Context, force_new: bool, debug: bool) -> None:
    """Create the local Ed25519 deployment key (the private key stays in SUNCLY_HOME/keys)."""
    from suncly.adapters.file_keys import FileSigningKeys

    config = _config(ctx)
    store = FileSigningKeys(config.keys_dir)
    current = store.current()
    if current is not None and not force_new:
        click.echo(
            f"A deployment key exists: {current.key_id} (in {config.keys_dir}). "
            "Use --new to create another."
        )
        return
    signer = store.create()
    click.echo(
        f"Created deployment key {signer.key_id} in {config.keys_dir}. "
        "The private key is never printed."
    )


@main.group()
def db() -> None:
    """Postgres evidence store (used when DATABASE_URL is set)."""


def _require_database_url(config: Config) -> str:
    if not config.database_url:
        raise RefusedError(
            "DATABASE_URL is not set.",
            "The Postgres store is used only when DATABASE_URL points at a database.",
            "Set DATABASE_URL (see .env.example) and run again.",
        )
    return config.database_url


@db.command("migrate")
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def db_migrate(ctx: click.Context, debug: bool) -> None:
    """Apply db/migrations/0001_initial_schema.sql to an empty database."""
    from suncly.adapters.postgres.migrate import apply_migration

    outcome = apply_migration(_require_database_url(_config(ctx)))
    click.echo(f"Migration 0001_initial_schema.sql: {outcome}.")


@db.command("check")
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def db_check(ctx: click.Context, debug: bool) -> None:
    """Check that the seven tables, eight enums and the triggers exist."""
    from suncly.adapters.postgres.migrate import check_schema

    problems = check_schema(_require_database_url(_config(ctx)))
    if problems:
        for problem in problems:
            click.echo(f"- {problem}")
        raise VerificationFailedError(
            "The database schema is incomplete.",
            f"{len(problems)} problem(s) found.",
            "Run `suncly db migrate` on an empty database.",
        )
    click.echo("Schema check passed: 7 tables, 8 enums and all triggers are present.")


@main.command()
@click.argument("card_url", required=False)
@click.option("--debug", is_flag=True)
@click.pass_context
@handles_errors
def doctor(ctx: click.Context, card_url: str | None, debug: bool) -> None:
    """Check Python, the deployment key, the store configuration and, optionally, a card URL."""
    from suncly.adapters.file_keys import FileSigningKeys
    from suncly.adapters.httpx_card_fetcher import HttpxCardFetcher
    from suncly.domain.card import parse_agent_card
    from suncly.domain.errors import CardError

    config = _config(ctx)
    console = Console()
    problems = 0

    def report(ok: bool, text: str) -> None:
        nonlocal problems
        problems += 0 if ok else 1
        mark = console.style("ok  ", fg="green") if ok else console.style("FAIL", fg="red")
        console.line(f"{mark} {text}")

    report(sys.version_info >= (3, 12), f"Python {sys.version.split()[0]} (3.12 or newer required)")
    key = FileSigningKeys(config.keys_dir).current()
    key_text = key.key_id if key else "none yet; `suncly keys init` or the first attest creates one"
    report(key is not None, f"deployment key: {key_text}")
    if config.uses_postgres:
        from suncly.adapters.postgres.migrate import check_schema

        try:
            schema_problems = check_schema(config.database_url or "")
        except Exception as exc:
            report(False, f"Postgres store: cannot connect ({type(exc).__name__})")
        else:
            detail = "schema complete" if not schema_problems else "; ".join(schema_problems)
            report(not schema_problems, f"Postgres store: {detail}")
    else:
        report(True, f"file store at {config.store_dir} (set DATABASE_URL to use Postgres)")
    report(True, f"reports go to {config.reports_dir.resolve()}")
    if card_url:
        try:
            fetched = HttpxCardFetcher(config.card_timeout_s, config.card_max_bytes).fetch(card_url)
            parsed = parse_agent_card(fetched.raw_json)
        except CardError as error:
            report(False, f"card: {error.what} {error.why}")
        else:
            report(
                True,
                f"card reachable: '{parsed.card.name}', {len(parsed.card.skills)} skill(s), "
                f"card_hash {parsed.card_hash}",
            )
    if problems:
        raise VerificationFailedError(
            f"{problems} check(s) failed.", "", "Fix the failed checks above and run again."
        )
    console.line("All checks passed.")


if __name__ == "__main__":  # pragma: no cover - exercised as a subprocess
    main()
