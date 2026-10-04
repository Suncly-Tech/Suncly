"""The real command, as a user runs it: exit codes, refusals, --json, verify and demo."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from suncly.cli import exit_codes
from suncly.mock_agents import behaviours
from suncly.mock_agents.server import MockAgentServer

pytestmark = pytest.mark.e2e


def suncly(
    *args: str, home: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "NO_COLOR": "1", **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "suncly.cli.main", "--home", str(home), *args],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        env=environment,
        timeout=240,
        check=False,
    )


def test_attest_without_sandbox_declaration_is_refused(tmp_path: Path) -> None:
    with MockAgentServer(behaviours.Honest()) as server:
        result = suncly("attest", server.card_url, "--approve-as", "me", home=tmp_path / "home")
    assert result.returncode == exit_codes.REFUSED
    assert "Nothing ran" in result.stderr and "--sandbox" in result.stderr
    assert "Traceback" not in result.stderr


def test_attest_without_approval_is_refused_when_not_interactive(tmp_path: Path) -> None:
    with MockAgentServer(behaviours.Honest()) as server:
        result = suncly("attest", server.card_url, "--sandbox", home=tmp_path / "home")
    assert result.returncode == exit_codes.REFUSED
    assert "not approved" in result.stderr
    assert "--approve-as" in result.stderr


def test_attest_from_a_url_alone_completes_and_verifies(tmp_path: Path) -> None:
    home = tmp_path / "home"
    reports = tmp_path / "reports"
    with MockAgentServer(behaviours.Honest()) as server:
        result = suncly(
            "attest",
            server.card_url,
            "--sandbox",
            "--approve-as",
            "alice",
            "--runs",
            "1",
            "--reports-dir",
            str(reports),
            "--json",
            home=home,
        )
    assert result.returncode == exit_codes.OK, result.stderr
    payload = json.loads(result.stdout)
    assert payload["kind"] == "completed"
    assert payload["decision"]["outcome"] == "flag"
    assert payload["attestation"]["status"] == "completed"
    assert payload["attestation"]["signature"].startswith("ed25519:")
    assert payload["exit_code_meaning"] == "0 means completed and signed, not approved"
    report_dir = Path(payload["report_dir"])
    assert (report_dir / "report.html").exists()

    verified = suncly("verify", str(report_dir), home=home)
    assert verified.returncode == exit_codes.OK, verified.stdout
    assert "Verification passed." in verified.stdout

    tampered = report_dir / "result.json"
    document = json.loads(tampered.read_text(encoding="utf-8"))
    document["decisions"][0]["outcome"] = "approve"
    tampered.write_text(json.dumps(document), encoding="utf-8")
    failed = suncly("verify", str(report_dir), home=home)
    assert failed.returncode == exit_codes.VERIFICATION_FAILED
    assert "FAIL decision" in failed.stdout


def test_human_readable_output_shows_counts_decision_and_exit_code_meaning(tmp_path: Path) -> None:
    with MockAgentServer(behaviours.Lying()) as server:
        result = suncly(
            "attest",
            server.card_url,
            "--sandbox",
            "--approve-as",
            "bob",
            "--runs",
            "1",
            "--reports-dir",
            str(tmp_path / "reports"),
            home=tmp_path / "home",
        )
    assert result.returncode == exit_codes.OK
    assert "pass  fail  inconclusive" in result.stdout
    assert (
        "Decision: flag. No policy is configured, so a human must review this result."
        in result.stdout
    )
    assert "What was NOT tested" in result.stdout
    assert "does not mean the agent was approved" in result.stdout
    assert "score" not in result.stdout.lower().replace("not a score", "")


def test_card_changer_exits_with_the_invalidated_code(tmp_path: Path) -> None:
    with MockAgentServer(behaviours.CardChanger()) as server:
        result = suncly(
            "attest",
            server.card_url,
            "--sandbox",
            "--approve-as",
            "bob",
            "--runs",
            "1",
            "--reports-dir",
            str(tmp_path / "reports"),
            home=tmp_path / "home",
        )
    assert result.returncode == exit_codes.INVALIDATED
    assert "No decision: the attestation ended invalidated." in result.stdout


def test_export_and_import_a_contract_file(tmp_path: Path) -> None:
    home = tmp_path / "home"
    draft = tmp_path / "contract.json"
    with MockAgentServer(behaviours.Honest()) as server:
        exported = suncly(
            "attest", server.card_url, "--sandbox", "--export-draft", str(draft), home=home
        )
        assert exported.returncode == exit_codes.OK, exported.stderr
        document = json.loads(draft.read_text(encoding="utf-8"))
        assert document["suncly_contract_file"] == 1
        assert len(document["test_cases"]) == 3
        slow = {
            **document["test_cases"][2],
            "criteria": {**document["test_cases"][2]["criteria"], "latency_limit_ms": 1},
        }
        document["test_cases"] = [document["test_cases"][0], slow]
        draft.write_text(json.dumps(document), encoding="utf-8")
        imported = suncly(
            "attest",
            server.card_url,
            "--sandbox",
            "--contract",
            str(draft),
            "--approve-as",
            "carol",
            "--runs",
            "1",
            "--reports-dir",
            str(tmp_path / "reports"),
            "--json",
            home=home,
        )
    assert imported.returncode == exit_codes.OK, imported.stderr
    payload = json.loads(imported.stdout)
    assert len(payload["results"]) == 2
    assert sum(r["fail_count"] for r in payload["results"]) == 1, "the 1 ms latency limit fails"


def test_demo_runs_both_agents_and_both_end_flagged(tmp_path: Path) -> None:
    result = suncly(
        "demo",
        "--runs",
        "1",
        "--reports-dir",
        str(tmp_path / "reports"),
        "--json",
        home=tmp_path / "home",
    )
    assert result.returncode == exit_codes.OK, result.stderr
    payload = json.loads(result.stdout)
    honest, lying = payload["agents"]["honest"], payload["agents"]["lying"]
    assert all(r["fail_count"] == 0 and r["pass_count"] == 1 for r in honest["results"])
    assert all(r["pass_count"] == 0 and r["fail_count"] == 1 for r in lying["results"])
    assert honest["decision"]["outcome"] == "flag" and lying["decision"]["outcome"] == "flag"


def test_keys_init_and_doctor(tmp_path: Path) -> None:
    home = tmp_path / "home"
    created = suncly("keys", "init", home=home)
    assert created.returncode == 0 and "Created deployment key ed25519-" in created.stdout
    again = suncly("keys", "init", home=home)
    assert again.returncode == 0 and "exists" in again.stdout
    for path in (home / "keys").iterdir():
        assert "PRIVATE" not in created.stdout and path.suffix in {".pem", ".pub", ""}
    with MockAgentServer(behaviours.Honest()) as server:
        doctor = suncly("doctor", server.card_url, home=home)
    assert doctor.returncode == 0, doctor.stdout
    assert "card reachable" in doctor.stdout and "All checks passed." in doctor.stdout


def test_internal_errors_are_one_message_without_a_traceback(tmp_path: Path) -> None:
    result = suncly("verify", str(tmp_path), home=tmp_path / "home")
    assert result.returncode == exit_codes.VERIFICATION_FAILED
    assert "cannot be read" in result.stderr
    assert "Traceback" not in result.stderr
