"""The scoped executor: a minimal child environment, credentials on stdin, nothing leaks."""

from __future__ import annotations

import json
import os
from uuid import UUID

import pytest

from suncly.adapters.scoped_executor import (
    INHERITED_FOR_START,
    ScopedSubprocessRunExecutor,
    minimal_environment,
)
from suncly.adapters.secrets import EnvironmentSecrets, NoSecrets, SecretManagerSecrets
from suncly.domain.errors import RunnerError
from suncly.domain.tenancy import CredentialReference, DeploymentMode
from suncly.mock_agents import behaviours
from suncly.mock_agents.server import MockAgentServer
from suncly.ports.run_executor import RunJob
from suncly.runner.process import RunEnvelope

TOKEN = "sekrit-agent-token-value-9f8e7d"


def job(target_url: str, sandbox: bool = True) -> RunJob:
    return RunJob(
        attestation_id=UUID(int=1),
        test_case_id=UUID(int=2),
        attempt=1,
        message_id="m-1",
        input={"text": "What is the capital of France?"},
        target_url=target_url,
        protocol_binding="JSONRPC",
        protocol_version="1.0",
        timeout_s=10.0,
        poll_interval_s=0.05,
        sandbox_declared=sandbox,
    )


def test_the_child_environment_holds_only_what_python_needs_plus_the_network_mode() -> None:
    base = {
        "PATH": "/usr/bin",
        "PYTHONPATH": "/src",
        "HOME": "/home/worker",
        "ANTHROPIC_API_KEY": "sk-ant-not-for-the-agent",
        "DATABASE_URL": "postgresql://worker@db/suncly",
        "SUNCLY_AGENT_AUTHORIZATION": "Bearer parent-credential",
        "STRIPE_SECRET_KEY": "sk_test_x",
        "SUNCLY_NETWORK_MODE": "local",
    }
    env = minimal_environment(base, DeploymentMode.PUBLIC)
    assert env == {
        "PATH": "/usr/bin",
        "PYTHONPATH": "/src",
        "SUNCLY_NETWORK_MODE": "public",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    assert "HOME" not in env and "ANTHROPIC_API_KEY" not in env
    assert set(INHERITED_FOR_START) >= {"PATH", "PYTHONPATH"}


def test_secret_resolvers_only_resolve_their_own_references() -> None:
    env = EnvironmentSecrets({"AGENT_TOKEN": f" {TOKEN} "})
    assert env.resolve(CredentialReference(provider="env", ref="AGENT_TOKEN")) == TOKEN
    assert env.resolve(CredentialReference(provider="none")) is None
    with pytest.raises(RunnerError, match="empty"):
        env.resolve(CredentialReference(provider="env", ref="MISSING"))
    with pytest.raises(RunnerError, match="not configured"):
        env.resolve(CredentialReference(provider="secret-manager", ref="projects/p/secrets/s"))
    assert NoSecrets().resolve(CredentialReference(provider="none")) is None
    with pytest.raises(RunnerError):
        NoSecrets().resolve(CredentialReference(provider="env", ref="AGENT_TOKEN"))
    manager = SecretManagerSecrets(
        accessor=lambda name: {"projects/p/secrets/s/versions/latest": TOKEN}[name]
    )
    assert (
        manager.resolve(
            CredentialReference(
                provider="secret-manager", ref="projects/p/secrets/s/versions/latest"
            )
        )
        == TOKEN
    )
    with pytest.raises(RunnerError):
        manager.resolve(CredentialReference(provider="env", ref="AGENT_TOKEN"))
    with pytest.raises(ValueError, match="looks like a credential"):
        CredentialReference(provider="env", ref="Bearer abc")


def test_the_credential_reaches_the_agent_on_stdin_and_never_the_transcript() -> None:
    with MockAgentServer(behaviours.Leaky()) as server:
        executor = ScopedSubprocessRunExecutor(
            EnvironmentSecrets({"AGENT_TOKEN": TOKEN}),
            CredentialReference(provider="env", ref="AGENT_TOKEN"),
            DeploymentMode.LOCAL,
            {**os.environ, "AGENT_TOKEN": TOKEN},
        )
        result = executor.execute(job(server.base_url + "/rpc"))
    assert result.transcript is not None, result.error
    text = result.transcript.model_dump_json()
    assert TOKEN not in text, "the credential must be redacted from the transcript"
    assert "you sent: " in text and "REDACTED" in text, "the agent did receive a credential"
    envelope = RunEnvelope(job=job("http://127.0.0.1:1/rpc"), authorization=TOKEN)
    assert json.loads(envelope.model_dump_json())["authorization"] == TOKEN


def test_an_unavailable_credential_is_a_crashed_run_not_an_exception() -> None:
    executor = ScopedSubprocessRunExecutor(
        EnvironmentSecrets({}),
        CredentialReference(provider="env", ref="AGENT_TOKEN"),
        DeploymentMode.LOCAL,
        dict(os.environ),
    )
    result = executor.execute(job("http://127.0.0.1:1/rpc"))
    assert result.crashed and "credential unavailable" in (result.error or "")


def test_the_runner_in_public_mode_refuses_a_loopback_target_even_when_the_job_names_it() -> None:
    with MockAgentServer(behaviours.Honest()) as server:
        executor = ScopedSubprocessRunExecutor(
            NoSecrets(),
            CredentialReference(provider="none"),
            DeploymentMode.PUBLIC,
            dict(os.environ),
        )
        result = executor.execute(job(server.base_url + "/rpc"))
    assert result.crashed and result.transcript is None
    assert "https" in (result.error or "") or "loopback" in (result.error or "")


def test_an_undeclared_sandbox_never_runs() -> None:
    executor = ScopedSubprocessRunExecutor(
        NoSecrets(), CredentialReference(provider="none"), DeploymentMode.LOCAL, dict(os.environ)
    )
    result = executor.execute(job("http://127.0.0.1:1/rpc", sandbox=False))
    assert result.crashed and "DR-006" in (result.error or "")
