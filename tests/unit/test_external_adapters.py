"""External tools (the A2A TCK, a Promptfoo pack): normalization, the process boundary, the worker."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from suncly.adapters.external import (
    A2A_TCK_VERSION,
    PROMPTFOO_VERSION,
    A2ATckRunner,
    PromptfooRunner,
    ToolProcess,
    normalize_promptfoo_results,
    normalize_tck_report,
)
from suncly.adapters.external.a2a_tck import (
    A2A_TCK_COMMIT,
    A2A_TCK_PYPROJECT_VERSION,
    PIN_FILE,
)
from suncly.core.attestations_app import AttestationWorkflow
from suncly.domain.jobs import JobKind
from suncly.domain.models import DecisionOutcome
from suncly.domain.policy import ExternalToolSummary, TestCategory
from suncly.domain.tenancy import DeploymentMode, Role
from suncly.ports.external_tools import ExternalCheck, ExternalToolResult
from tests.fakes import StaticFetcher, card_text
from tests.hosted import build_world
from tests.unit.test_worker_and_jobs import low_risk_policy

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "external"
CARD_URL = "https://agent.example.test/.well-known/agent-card.json"


def process() -> ToolProcess:
    return ToolProcess(dict(os.environ), DeploymentMode.LOCAL)


def tck_checkout(
    tmp_path: Path, version: str = A2A_TCK_PYPROJECT_VERSION, commit: str = A2A_TCK_COMMIT
) -> Path:
    """What the worker image leaves behind: the tag's files and a pin file in place of .git."""
    checkout = tmp_path / "a2a-tck"
    checkout.mkdir(parents=True)
    (checkout / "pyproject.toml").write_text(
        f'[project]\nname = "a2a-tck"\nversion = "{version}"\n'
    )
    (checkout / PIN_FILE).write_text(commit + "\n")
    return checkout


# -- normalization --------------------------------------------------------------------------


def test_tck_requirements_become_protocol_checks_and_only_pass_counts_as_pass() -> None:
    document = json.loads((FIXTURES / "compatibility.json").read_text())
    result = normalize_tck_report(document, "https://sandbox.example.test/rpc")
    by_id = {c.id: c for c in result.checks}
    assert (
        result.tool == "a2a-tck"
        and result.tool_version == A2A_TCK_VERSION
        and result.failure is None
    )
    assert {c.category for c in result.checks} == {TestCategory.PROTOCOL}
    assert by_id["A2A-CARD-001"].passed is True and by_id["A2A-CARD-001"].level == "must"
    assert (
        by_id["A2A-TASK-003"].passed is False
        and "TaskNotFoundError" in by_id["A2A-TASK-003"].detail
    )
    assert by_id["A2A-STREAM-001"].passed is None and by_id["A2A-STREAM-001"].level == "should"
    assert by_id["A2A-PUSH-001"].passed is None, "NOT TESTED is undecided, never a pass"
    assert result.counts() == {"passed": 2, "failed": 1, "undecided": 2}
    assert normalize_tck_report({"summary": {}}, "x").failure


def test_promptfoo_rows_become_checks_in_their_categories() -> None:
    document = json.loads((FIXTURES / "promptfoo-results.json").read_text())
    result = normalize_promptfoo_results(document, "https://sandbox.example.test/rpc")
    by_id = {c.id: c for c in result.checks}
    assert (
        result.tool == "promptfoo"
        and result.tool_version == PROMPTFOO_VERSION
        and result.failure is None
    )
    assert by_id["r-1"].passed is True and by_id["r-1"].category is TestCategory.SEMANTIC
    assert by_id["r-2"].passed is False and by_id["r-2"].category is TestCategory.SECURITY
    assert by_id["r-2"].level == "promptfoo:redteam:prompt-injection"
    assert by_id["r-3"].passed is None and "No API key" in by_id["r-3"].detail, (
        "a model-graded row is undecided"
    )
    assert by_id["r-4"].passed is True and by_id["r-4"].category is TestCategory.OPERATIONAL
    assert result.counts() == {"passed": 2, "failed": 1, "undecided": 1}
    assert normalize_promptfoo_results({"results": {"version": 9, "results": []}}, "x").failure
    assert normalize_promptfoo_results({}, "x").failure


# -- the process boundary and the runners ---------------------------------------------------


def test_the_tool_process_gets_the_minimal_environment_and_a_deadline(tmp_path: Path) -> None:
    script = tmp_path / "env.py"
    script.write_text("import os, json, sys; print(json.dumps(dict(os.environ)))")
    tool = ToolProcess(
        {**os.environ, "ANTHROPIC_API_KEY": "sk-ant-secret", "DATABASE_URL": "pg://x"},
        DeploymentMode.PUBLIC,
        {"SUNCLY_AGENT_AUTHORIZATION": "Bearer t"},
    )
    result = tool.run([sys.executable, str(script)], tmp_path, 30.0)
    assert result.ran and result.returncode == 0
    env = json.loads(result.stdout)
    assert "ANTHROPIC_API_KEY" not in env and "DATABASE_URL" not in env
    assert env["SUNCLY_NETWORK_MODE"] == "public"
    assert env["SUNCLY_AGENT_AUTHORIZATION"] == "[REDACTED]", "a tool's output never shows it"
    sleeper = tmp_path / "sleep.py"
    sleeper.write_text("import time; time.sleep(5)")
    slow = tool.run([sys.executable, str(sleeper)], tmp_path, 0.5)
    assert slow.timed_out and not slow.ran
    missing = tool.run(["/no/such/binary"], tmp_path, 1.0)
    assert missing.failed_to_start and not missing.ran


def test_the_tck_runner_pins_its_version_and_keeps_the_report(tmp_path: Path) -> None:
    checkout = tck_checkout(tmp_path)
    runner = A2ATckRunner(
        process(), checkout, command=[sys.executable, str(FIXTURES / "fake_tck.py")]
    )
    result = runner.run("http://127.0.0.1:9999/rpc", str(tmp_path / "work"), 60.0)
    assert result.failure is None and result.counts()["failed"] == 1
    kinds = {a.kind: a for a in result.artifacts}
    assert json.loads(kinds["report"].content) == json.loads(
        (FIXTURES / "compatibility.json").read_text()
    )
    assert kinds["junit"].content == b"<testsuite/>" and b"66.7%" in kinds["stdout"].content

    wrong = A2ATckRunner(
        process(),
        tck_checkout(tmp_path / "other", "0.3.0.beta5"),
        command=[sys.executable, str(FIXTURES / "fake_tck.py")],
    )
    assert "pinned to tag" in (
        wrong.run("http://127.0.0.1:9999/rpc", str(tmp_path / "w2"), 60.0).failure or ""
    )
    moved = A2ATckRunner(
        process(),
        tck_checkout(tmp_path / "moved", commit="0" * 40),
        command=[sys.executable, str(FIXTURES / "fake_tck.py")],
    )
    assert "is at commit 0000" in (
        moved.run("http://127.0.0.1:9999/rpc", str(tmp_path / "w4"), 60.0).failure or ""
    )
    assert "no TCK checkout" in (
        A2ATckRunner(process(), tmp_path / "missing")
        .run("http://x/rpc", str(tmp_path / "w3"), 60.0)
        .failure
        or ""
    )


def test_a_misbehaving_tck_is_a_tool_failure_with_its_output_kept(tmp_path: Path) -> None:
    """The fake's mode travels through the tool process's explicit extras: the worker's own
    environment (where a test would set a variable) never reaches the tool."""
    checkout = tck_checkout(tmp_path)
    command = [sys.executable, str(FIXTURES / "fake_tck.py")]

    def runner(mode: str) -> A2ATckRunner:
        tool = ToolProcess(dict(os.environ), DeploymentMode.LOCAL, {"FAKE_TCK_MODE": mode})
        return A2ATckRunner(tool, checkout, command=command)

    crashed = runner("crash").run("http://x:1/rpc", str(tmp_path / "w1"), 60.0)
    assert crashed.failure and "wrote no report" in crashed.failure and crashed.checks == []
    assert any(a.kind == "stderr" and b"unreachable" in a.content for a in crashed.artifacts)
    garbage = runner("garbage").run("http://x:1/rpc", str(tmp_path / "w2"), 60.0)
    assert garbage.failure and "not JSON" in garbage.failure
    hung = runner("hang").run("http://x:1/rpc", str(tmp_path / "w3"), 1.0)
    assert hung.failure and "did not finish" in hung.failure


def test_the_promptfoo_runner_checks_the_installed_version_and_runs_the_pack(
    tmp_path: Path,
) -> None:
    pack = tmp_path / "pack.yaml"
    pack.write_text("description: test pack\n")
    command = [sys.executable, str(FIXTURES / "fake_promptfoo.py")]
    runner = PromptfooRunner(process(), pack, command=command)
    result = runner.run("https://sandbox.example.test/rpc", str(tmp_path / "work"), 60.0)
    assert result.failure is None and result.counts() == {"passed": 2, "failed": 1, "undecided": 1}
    assert [a.kind for a in result.artifacts] == ["results"]
    stale_tool = ToolProcess(
        dict(os.environ), DeploymentMode.LOCAL, {"FAKE_PROMPTFOO_VERSION": "0.99.0"}
    )
    stale = PromptfooRunner(stale_tool, pack, command=command)
    assert "pinned to" in (stale.run("https://x/rpc", str(tmp_path / "w2"), 60.0).failure or "")
    silent_tool = ToolProcess(
        dict(os.environ), DeploymentMode.LOCAL, {"FAKE_PROMPTFOO_MODE": "no-output"}
    )
    silent = PromptfooRunner(silent_tool, pack, command=command)
    assert "wrote no results" in (
        silent.run("https://x/rpc", str(tmp_path / "w3"), 60.0).failure or ""
    )
    assert "not installed" in (
        PromptfooRunner(process(), pack, command=["/no/such/promptfoo"])
        .run("https://x/rpc", str(tmp_path / "w4"), 60.0)
        .failure
        or ""
    )


# -- the worker -----------------------------------------------------------------------------


class _ScriptedTool:
    tool = "a2a-tck"
    tool_version = A2A_TCK_VERSION

    def __init__(self, result: ExternalToolResult, calls: list[str]) -> None:
        self._result = result
        self._calls = calls

    def run(self, target_url: str, work_dir: str, timeout_s: float) -> ExternalToolResult:
        self._calls.append(target_url)
        return self._result


def test_the_worker_runs_requested_tools_once_stores_artifacts_and_flags_failures(
    tmp_path: Path,
) -> None:
    world = build_world(tmp_path, fetcher=StaticFetcher({CARD_URL: card_text()}))
    s = world.services
    calls: list[str] = []
    document = json.loads((FIXTURES / "compatibility.json").read_text())
    tck = normalize_tck_report(document, "https://agent.example.com/rpc").model_copy(
        update={
            "artifacts": [
                __import__(
                    "suncly.ports.external_tools", fromlist=["ExternalArtifactData"]
                ).ExternalArtifactData(
                    kind="report",
                    filename="compatibility.json",
                    content=json.dumps(document).encode(),
                )
            ]
        }
    )
    s.external_tools = {"a2a-tck": lambda registration: _ScriptedTool(tck, calls)}
    acme = world.organization("acme", {"rev": Role.REVIEWER})
    low_risk_policy(acme.id, world)
    from suncly.core.attestations_app import StartAttestationRequest
    from suncly.core.contracts_app import ContractWorkflow, DraftSource
    from suncly.core.registry import AgentRegistry, RegisterAgentRequest
    from suncly.domain.models import RiskLevel
    from suncly.domain.tenancy import CredentialReference

    ctx = world.context("rev", acme.id, "agents:write")
    registration = AgentRegistry(s).register(
        ctx,
        RegisterAgentRequest(
            name="a",
            card_url=CARD_URL,
            risk_level=RiskLevel.LOW,
            owner="t",
            sandbox_declared=True,
            credential=CredentialReference(provider="none"),
        ),
    )
    detail = ContractWorkflow(s).draft(ctx, registration.id, DraftSource(kind="deterministic"))
    detail = ContractWorkflow(s).approve(ctx, detail.contract.id)
    view = AttestationWorkflow(s).start(
        ctx,
        StartAttestationRequest(
            registration_id=registration.id,
            contract_id=detail.contract.id,
            runs=1,
            external_tools=("a2a-tck", "promptfoo", "a2a-tck"),
        ),
    )
    assert view.job is not None and view.job.payload["external_tools"] == [
        "a2a-tck",
        "promptfoo",
        "a2a-tck",
    ]
    assert world.worker().run_once()
    assert calls == ["https://agent.example.com/rpc"], (
        "the tool ran once for the deduplicated request"
    )

    job = s.app_store.find_job(JobKind.ATTESTATION, view.attestation.id)
    assert job is not None
    external = {r["tool"]: r for r in job.progress["external_results"]}
    assert external["a2a-tck"]["counts"] == {"passed": 2, "failed": 1, "undecided": 2}
    assert external["promptfoo"]["failure"] and external["promptfoo"]["checks"] == []
    stored = external["a2a-tck"]["artifacts"][0]
    assert stored["storage_ref"] == f"{view.attestation.id}/external/a2a-tck/compatibility.json"
    assert s.transcripts.get(stored["storage_ref"]) == json.dumps(document).encode()
    artifacts = s.app_store.list_external_artifacts(view.attestation.id)
    assert [a.sha256 for a in artifacts] == [stored["sha256"]] and artifacts[
        0
    ].tool_version == A2A_TCK_VERSION

    decision = s.store.list_decisions(view.attestation.id)[-1]
    assert decision.outcome is DecisionOutcome.FLAG, "a failed MUST requirement never approves"
    evaluation = job.progress["policy_evaluation"]
    assert any("a2a-tck" in r and "1 failed" in r for r in evaluation["reasons"])
    assert any("promptfoo" in r and "could not run" in r for r in evaluation["reasons"])
    assert [e["tool"] for e in evaluation["external"]] == ["a2a-tck", "promptfoo"]
    payload = json.loads(s.transcripts.get(f"{view.attestation.id}/signature-payload.json"))
    assert payload["artifact_hashes"] == {stored["storage_ref"]: stored["sha256"]}
    bundle = AttestationWorkflow(s).evidence(
        world.context("rev", acme.id, "evidence:read"), view.attestation.id
    )
    assert [r["tool"] for r in bundle.external_results] == ["a2a-tck", "promptfoo"]


def test_passing_external_checks_do_not_block_an_approval() -> None:
    from datetime import UTC, datetime

    from suncly.domain.models import RiskLevel
    from suncly.domain.policy import PolicyConfiguration, RiskThresholds, evaluate_policy
    from tests.unit.test_policy import result

    policy = PolicyConfiguration.model_validate(
        {"policy_version": "v", "thresholds": {RiskLevel.LOW: RiskThresholds(min_pass_ratio=0.5)}}
    )
    clean = ExternalToolSummary(
        tool="a2a-tck", tool_version=A2A_TCK_VERSION, passed=5, failed=0, undecided=2
    )
    ok = evaluate_policy(
        policy=policy,
        risk_level=RiskLevel.LOW,
        results=[result(p=10)],
        categories={},
        baseline=None,
        baseline_at=None,
        now=datetime.now(UTC),
        external=[clean],
    )
    assert ok.outcome is DecisionOutcome.APPROVE and ok.external == [clean]
    broken = ExternalToolSummary(
        tool="promptfoo",
        tool_version=PROMPTFOO_VERSION,
        passed=0,
        failed=0,
        undecided=0,
        failure="not installed",
    )
    flagged = evaluate_policy(
        policy=policy,
        risk_level=RiskLevel.LOW,
        results=[result(p=10)],
        categories={},
        baseline=None,
        baseline_at=None,
        now=datetime.now(UTC),
        external=[broken],
    )
    assert flagged.outcome is DecisionOutcome.FLAG and flagged.requires_human
    assert ExternalCheck(id="x", category=TestCategory.PROTOCOL, passed=None).passed is None
