"""Architecture rules, enforced by tests: layering, credential isolation, exact names."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from pydantic import BaseModel

from suncly.domain.models import (
    AttestationStatus,
    AttestationTrigger,
    ContractStatus,
    DecisionOutcome,
    JudgeLayer,
    RiskLevel,
    RunVerdict,
    TestCaseKind,
)
from suncly.runner.credentials import CREDENTIAL_ENV_VAR

REPO = Path(__file__).resolve().parents[2]
SRC = REPO / "src" / "suncly"

THIRD_PARTY_PURE = {"pydantic", "rfc8785", "jsonschema", "cryptography"}
STDLIB_MARKER = object()

#: Which internal layers each layer may import. Keys and values are top-level subpackages.
ALLOWED = {
    "domain": set(),
    "ports": {"domain"},
    "core": {"domain", "ports"},
    "runner": {"domain", "ports", "runner"},
    "adapters": {"domain", "ports", "core", "runner", "adapters"},
    "mock_agents": {"domain", "mock_agents"},
    "cli": {"domain", "ports", "core", "adapters", "cli", "mock_agents"},
}
#: Modules that may perform I/O inside the runner package; the rest is pure protocol logic.
RUNNER_IO_MODULES = {"http_transport", "process", "credentials"}


def modules() -> list[tuple[str, Path]]:
    found = []
    for path in sorted(SRC.rglob("*.py")):
        relative = path.relative_to(SRC).with_suffix("")
        parts = list(relative.parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        found.append((".".join(parts), path))
    return found


def imports_of(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
    return names


def layer_of(module: str) -> str:
    return module.split(".")[0] if module else ""


@pytest.mark.parametrize(("module", "path"), modules(), ids=[m for m, _ in modules()])
def test_imports_point_inward_only(module: str, path: Path) -> None:
    """Domain and core never import an adapter; ports import only the domain."""
    layer = layer_of(module)
    if layer not in ALLOWED:
        pytest.skip("top-level module")
    for imported in imports_of(path):
        if not imported.startswith("suncly."):
            continue
        target = layer_of(imported[len("suncly.") :])
        assert target in ALLOWED[layer] or target == layer, (
            f"{module} imports {imported}: layer {layer!r} may only import {sorted(ALLOWED[layer])}"
        )


def test_domain_and_ports_import_no_io_libraries() -> None:
    forbidden = {"httpx", "psycopg", "subprocess", "socket", "click"}
    for module, path in modules():
        if layer_of(module) in {"domain", "ports"}:
            for imported in imports_of(path):
                assert imported.split(".")[0] not in forbidden, f"{module} imports {imported}"


def test_core_does_no_io() -> None:
    forbidden = {"httpx", "psycopg", "subprocess", "socket", "click", "os", "sys"}
    for module, path in modules():
        if layer_of(module) == "core":
            for imported in imports_of(path):
                assert imported.split(".")[0] not in forbidden, f"{module} imports {imported}"


def test_runner_protocol_logic_is_pure() -> None:
    for module, path in modules():
        if layer_of(module) == "runner" and module.split(".")[-1] not in RUNNER_IO_MODULES:
            for imported in imports_of(path):
                assert imported.split(".")[0] not in {"httpx", "os", "sys", "subprocess"}, (
                    f"{module} imports {imported}"
                )


def test_only_the_runner_reads_the_credential() -> None:
    """DR-003: the credential variable is named in exactly one source module."""
    offenders = []
    for module, path in modules():
        if (
            CREDENTIAL_ENV_VAR in path.read_text(encoding="utf-8")
            and module != "runner.credentials"
        ):
            offenders.append(module)
    assert offenders == [], f"modules naming {CREDENTIAL_ENV_VAR}: {offenders}"


def test_no_module_outside_the_runner_reads_the_environment_for_the_agent() -> None:
    """The parent processes never touch os.environ except the config loader and the CLI."""
    allowed = {"adapters.config_loader", "cli.main", "cli.output", "runner.process"}
    for module, path in modules():
        text = path.read_text(encoding="utf-8")
        if "os.environ" in text or "getenv(" in text:
            assert module in allowed, f"{module} reads the environment"


def test_no_code_path_constructs_an_approve_or_block_decision() -> None:
    """The MVP never writes approve or block: the names appear only in the enum and in checks."""
    pattern = re.compile(r"DecisionOutcome\.(APPROVE|BLOCK)\b")
    for module, path in modules():
        if module == "domain.models":
            continue
        assert not pattern.search(path.read_text(encoding="utf-8")), f"{module} names approve/block"


def test_enum_values_are_exactly_the_schemas() -> None:
    assert [v.value for v in RiskLevel] == ["low", "medium", "high"]
    assert [v.value for v in ContractStatus] == ["draft", "approved", "rejected", "superseded"]
    assert [v.value for v in TestCaseKind] == [
        "skill",
        "probe_undeclared",
        "probe_injection",
        "probe_failure",
    ]
    assert [v.value for v in AttestationTrigger] == ["ci", "schedule", "card_change", "manual"]
    assert [v.value for v in AttestationStatus] == [
        "queued",
        "running",
        "completed",
        "failed",
        "cancelled",
        "invalidated",
    ]
    assert [v.value for v in RunVerdict] == ["pass", "fail", "inconclusive"]
    assert [v.value for v in JudgeLayer] == ["deterministic", "model"]
    assert [v.value for v in DecisionOutcome] == ["approve", "flag", "block"]


def test_entity_fields_are_exactly_the_schemas() -> None:
    from suncly.domain import models

    expected: dict[type[BaseModel], list[str]] = {
        models.Agent: ["id", "name", "owner", "risk_level"],
        models.CardVersion: ["id", "agent_id", "card_hash", "raw_json", "fetched_at"],
        models.Contract: [
            "id",
            "card_version_id",
            "version",
            "status",
            "created_at",
            "approved_by",
            "approved_at",
        ],
        models.TestCase: ["id", "contract_id", "skill_id", "input", "criteria", "kind"],
        models.Attestation: [
            "id",
            "contract_id",
            "card_version_id",
            "trigger",
            "status",
            "started_at",
            "finished_at",
            "budget_limit",
            "cost_total",
            "signature",
            "signing_key_id",
        ],
        models.Run: [
            "id",
            "attestation_id",
            "test_case_id",
            "attempt",
            "verdict",
            "judge_layer",
            "rationale",
            "latency_ms",
            "cost",
            "transcript_ref",
            "started_at",
            "finished_at",
        ],
        models.Decision: [
            "id",
            "attestation_id",
            "outcome",
            "policy_version",
            "decided_by",
            "decided_at",
        ],
    }
    for model, fields in expected.items():
        assert list(model.model_fields) == fields, model.__name__


def test_placeholders_for_later_stages_hold_only_a_docstring() -> None:
    for relative in ("api.py", "adapters/ci.py", "adapters/registry.py"):
        tree = ast.parse((SRC / relative).read_text(encoding="utf-8"))
        assert len(tree.body) == 1 and isinstance(tree.body[0], ast.Expr), relative
        docstring = ast.get_docstring(tree) or ""
        assert re.search(r"stage [56]", docstring), relative


def test_packaged_migration_matches_the_db_folder() -> None:
    packaged = SRC / "adapters" / "postgres" / "migrations" / "0001_initial_schema.sql"
    source = REPO / "db" / "migrations" / "0001_initial_schema.sql"
    assert packaged.read_bytes() == source.read_bytes()


def test_db_folder_holds_exactly_the_migration_and_its_readme() -> None:
    files = sorted(
        p.relative_to(REPO / "db").as_posix() for p in (REPO / "db").rglob("*") if p.is_file()
    )
    assert files == ["README.md", "migrations/0001_initial_schema.sql"]
