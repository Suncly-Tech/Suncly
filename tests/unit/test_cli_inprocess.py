"""The suncly command in-process with click's runner, against bundled mock agents."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from click.testing import CliRunner, Result

from suncly.cli import exit_codes
from suncly.cli.main import main
from suncly.mock_agents import behaviours
from suncly.mock_agents.server import MockAgentServer

pytestmark = pytest.mark.e2e


@pytest.fixture
def honest() -> Iterator[MockAgentServer]:
    with MockAgentServer(behaviours.Honest()) as server:
        yield server


def invoke(tmp_path: Path, *args: str, input: str | None = None) -> Result:
    runner = CliRunner(env={"NO_COLOR": "1"})
    return runner.invoke(
        main,
        ["--home", str(tmp_path / "home"), *args],
        input=input,
        catch_exceptions=False,
    )


def attest_args(server: MockAgentServer, tmp_path: Path, *extra: str) -> list[str]:
    return [
        "attest",
        server.card_url,
        "--sandbox",
        "--runs",
        "1",
        "--reports-dir",
        str(tmp_path / "reports"),
        *extra,
    ]


def test_interactive_approval_records_the_approver_and_runs(
    honest: MockAgentServer, tmp_path: Path
) -> None:
    result = invoke(tmp_path, *attest_args(honest, tmp_path), input="y\nalice\n")
    assert result.exit_code == exit_codes.OK, result.output
    assert "Draft contract version 1" in result.output
    assert "Contract version 1 approved by alice." in result.output
    assert (
        "Decision: flag. No policy is configured, so a human must review this result."
        in result.output
    )
    assert "pass  fail  inconclusive" in result.output
    assert "What was NOT tested" in result.output
    assert "does not mean the agent was approved" in result.output


def test_declining_the_prompt_runs_nothing(honest: MockAgentServer, tmp_path: Path) -> None:
    result = invoke(tmp_path, *attest_args(honest, tmp_path), input="n\n")
    assert result.exit_code == exit_codes.REFUSED
    assert "Nothing ran: the contract is not approved." in result.output
    assert honest.calls == 0


def test_a_closed_stdin_at_the_prompt_runs_nothing(honest: MockAgentServer, tmp_path: Path) -> None:
    result = invoke(tmp_path, *attest_args(honest, tmp_path), input="")
    assert result.exit_code == exit_codes.REFUSED
    assert "--approve-as" in result.output
    assert honest.calls == 0


def test_json_output_then_verify_then_tamper(honest: MockAgentServer, tmp_path: Path) -> None:
    result = invoke(tmp_path, *attest_args(honest, tmp_path, "--approve-as", "bob", "--json"))
    assert result.exit_code == exit_codes.OK, result.output
    payload = json.loads(result.stdout)
    assert payload["kind"] == "completed" and payload["decision"]["outcome"] == "flag"
    assert payload["results"] and all(r["pass_count"] == 1 for r in payload["results"])
    report_dir = Path(payload["report_dir"])

    verified = invoke(tmp_path, "verify", str(report_dir))
    assert verified.exit_code == exit_codes.OK and "Verification passed." in verified.output
    as_json = invoke(tmp_path, "verify", str(report_dir), "--json")
    assert json.loads(as_json.stdout)["ok"] is True

    transcript = next((report_dir / "transcripts").glob("*.json"))
    transcript.chmod(0o644)
    transcript.write_bytes(transcript.read_bytes() + b" ")
    failed = invoke(tmp_path, "verify", str(report_dir))
    assert failed.exit_code == exit_codes.VERIFICATION_FAILED
    assert "FAIL transcript hashes" in failed.output and "Verification FAILED." in failed.output

    wrong_key = invoke(tmp_path, "verify", str(report_dir), "--public-key", "AAAA")
    assert wrong_key.exit_code == exit_codes.VERIFICATION_FAILED


def test_export_then_import_a_contract_file(honest: MockAgentServer, tmp_path: Path) -> None:
    draft = tmp_path / "draft.json"
    exported = invoke(tmp_path, *attest_args(honest, tmp_path, "--export-draft", str(draft)))
    assert exported.exit_code == exit_codes.OK and "Draft contract written" in exported.output
    document = json.loads(draft.read_text(encoding="utf-8"))
    document["test_cases"] = document["test_cases"][:1]
    document["skills_without_test_case"] = ["count-words"]
    draft.write_text(json.dumps(document), encoding="utf-8")
    imported = invoke(
        tmp_path,
        *attest_args(honest, tmp_path, "--contract", str(draft), "--approve-as", "carol", "--json"),
    )
    assert imported.exit_code == exit_codes.OK, imported.output
    payload = json.loads(imported.stdout)
    assert len(payload["results"]) == 1
    assert any("count-words" in item["detail"] for item in payload["not_tested"])

    document["card_hash"] = "sha256:wrong"
    draft.write_text(json.dumps(document), encoding="utf-8")
    refused = invoke(
        tmp_path, *attest_args(honest, tmp_path, "--contract", str(draft), "--approve-as", "carol")
    )
    assert refused.exit_code == exit_codes.REFUSED and "different card" in refused.output


def test_demo_in_process(tmp_path: Path) -> None:
    result = invoke(tmp_path, "demo", "--runs", "1", "--reports-dir", str(tmp_path / "reports"))
    assert result.exit_code == exit_codes.OK, result.output
    assert result.output.count("Decision: flag.") == 2
    assert "Demo finished" in result.output


def test_keys_init_and_doctor_in_process(honest: MockAgentServer, tmp_path: Path) -> None:
    created = invoke(tmp_path, "keys", "init")
    assert created.exit_code == 0 and "Created deployment key ed25519-" in created.output
    again = invoke(tmp_path, "keys", "init")
    assert "exists" in again.output
    renewed = invoke(tmp_path, "keys", "init", "--new")
    assert "Created deployment key" in renewed.output
    doctor = invoke(tmp_path, "doctor", honest.card_url)
    assert (
        doctor.exit_code == 0
        and "card reachable" in doctor.output
        and "All checks passed." in doctor.output
    )
    bad = invoke(tmp_path, "doctor", "http://agent.example.com/card")
    assert bad.exit_code == exit_codes.VERIFICATION_FAILED and "FAIL card" in bad.output


def test_refusals_print_three_sentences_without_a_traceback(
    honest: MockAgentServer, tmp_path: Path
) -> None:
    result = invoke(tmp_path, "attest", honest.card_url, "--approve-as", "x")
    assert result.exit_code == exit_codes.REFUSED
    assert "Nothing ran: the endpoint is not declared a sandbox" in result.output
    assert "--sandbox" in result.output and "Traceback" not in result.output
    unreachable = invoke(
        tmp_path, "attest", "http://127.0.0.1:9/card", "--sandbox", "--approve-as", "x"
    )
    assert (
        unreachable.exit_code == exit_codes.REFUSED and "could not be fetched" in unreachable.output
    )


def test_debug_flag_reraises(honest: MockAgentServer, tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--home",
            str(tmp_path / "home"),
            "attest",
            honest.card_url,
            "--approve-as",
            "x",
            "--debug",
        ],
    )
    assert result.exit_code != 0 and result.exception is not None
    assert "SandboxDeclarationMissingError" in repr(result.exception)
