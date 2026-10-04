"""The CLI in-process with click's runner: argument handling, colour fallback, exit codes."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from click.testing import CliRunner

from suncly.cli import exit_codes
from suncly.cli.main import main
from suncly.cli.output import Console, wants_colour
from suncly.domain.errors import ConfigError, RefusedError, SigningError, VerificationFailedError


def test_exit_codes_are_distinct_and_mapped() -> None:
    codes = {
        exit_codes.OK,
        exit_codes.INTERNAL_ERROR,
        exit_codes.USAGE,
        exit_codes.REFUSED,
        exit_codes.FAILED,
        exit_codes.INVALIDATED,
        exit_codes.VERIFICATION_FAILED,
    }
    assert len(codes) == 7
    assert exit_codes.code_for(RefusedError("x")) == exit_codes.REFUSED
    assert exit_codes.code_for(VerificationFailedError("x")) == exit_codes.VERIFICATION_FAILED
    assert exit_codes.code_for(SigningError("x")) == exit_codes.INTERNAL_ERROR
    assert exit_codes.code_for(ConfigError("x")) == exit_codes.INTERNAL_ERROR
    assert exit_codes.OUTCOME_CODES == {
        "completed": 0,
        "failed": 4,
        "invalidated": 5,
        "draft_exported": 0,
    }


def test_colour_is_off_for_pipes_no_color_and_dumb_terminals() -> None:
    stream = io.StringIO()
    assert not wants_colour(stream, {})

    class Tty(io.StringIO):
        def isatty(self) -> bool:
            return True

    assert wants_colour(Tty(), {})
    assert not wants_colour(Tty(), {"NO_COLOR": "1"})
    assert not wants_colour(Tty(), {"TERM": "dumb"})
    console = Console(stream, colour=False)
    console.table(["a", "bb"], [["1", "2"]], numeric=frozenset({1}))
    assert stream.getvalue() == "a  bb\n-  --\n1   2\n"
    assert console.style("x", fg="red") == "x"


def test_attest_requires_a_card_url_and_rejects_bad_budgets(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["--home", str(tmp_path), "attest"])
    assert result.exit_code == exit_codes.USAGE
    result = runner.invoke(
        main,
        [
            "--home",
            str(tmp_path),
            "attest",
            "https://x.example.com/c",
            "--sandbox",
            "--budget",
            "lots",
            "--approve-as",
            "me",
        ],
    )
    assert result.exit_code == exit_codes.USAGE and "number of attempts" in result.output


def test_invalid_arguments_never_open_a_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A rejected argument must not leave a store (or a database connection) behind."""
    from suncly.cli import main as cli_main

    def refuse_to_build(*args: object, **kwargs: object) -> None:
        raise AssertionError("build_services must not be called before the arguments are valid")

    monkeypatch.setattr(cli_main, "build_services", refuse_to_build)
    runner = CliRunner()
    bad_budget = runner.invoke(
        main,
        [
            "--home",
            str(tmp_path),
            "attest",
            "https://x.example.com/c",
            "--sandbox",
            "--budget",
            "lots",
        ],
    )
    assert bad_budget.exit_code == exit_codes.USAGE
    contract = tmp_path / "contract.json"
    contract.write_text("{not json", encoding="utf-8")
    bad_contract = runner.invoke(
        main,
        [
            "--home",
            str(tmp_path),
            "attest",
            "https://x.example.com/c",
            "--sandbox",
            "--contract",
            str(contract),
        ],
    )
    assert bad_contract.exit_code == exit_codes.REFUSED and "not valid JSON" in bad_contract.output


def test_a_bad_config_is_reported_in_three_sentences(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text("runs = 0\n", encoding="utf-8")
    result = CliRunner().invoke(main, ["--home", str(tmp_path), "doctor"])
    assert result.exit_code == exit_codes.INTERNAL_ERROR
    assert "at least 1" in result.output


def test_db_commands_refuse_without_database_url(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("DATABASE_URL", raising=False)
    result = CliRunner().invoke(main, ["--home", str(tmp_path), "db", "check"])
    assert result.exit_code == exit_codes.REFUSED and "DATABASE_URL is not set" in result.output


def test_version_flag() -> None:
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0 and "suncly" in result.output
