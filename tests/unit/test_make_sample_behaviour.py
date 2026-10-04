"""The fictional sample agent behind the website's sample data.

``frontend/scripts/make-sample.py`` defines the Harbor Returns Agent, a mock A2A
agent with a switchable behaviour. These tests pin down what each mode answers,
because the sample bundles on the website are generated from it.
"""

from __future__ import annotations

from typing import Any

import pytest

from suncly.domain import a2a
from suncly.mock_agents.behaviours import CallContext
from tests.frontend_scripts import load_make_sample

make_sample = load_make_sample()

CONTEXT = CallContext(call_number=1, headers={}, card_fetches=1)
SHIPPED = "Has order 48213 shipped yet?"
WHERE_IS = "Where is order 48213?"
START_RETURN = "Start a return for order 48213, item 2"
REFUND = "How much will I get back if I return order 48213?"


@pytest.fixture
def agent(monkeypatch: pytest.MonkeyPatch) -> Any:
    """The sample agent, without its answer delays."""
    monkeypatch.setattr(make_sample.time, "sleep", lambda _seconds: None)
    return make_sample.HarborReturns()


def ask(agent: Any, text: str) -> Any:
    params = {"message": {"messageId": "m", "role": a2a.ROLE_USER, "parts": [{"text": text}]}}
    return agent.send_message(params, CONTEXT)["task"]


def answer_text(task: Any) -> str:
    return str(task["artifacts"][0]["parts"][0]["text"])


def test_card_declares_four_skills_one_without_examples(agent: Any) -> None:
    card = agent.card("http://127.0.0.1:8701", CONTEXT)
    assert card["name"] == "Harbor Returns Agent"
    assert card["version"] == "2.3.1"
    assert card["capabilities"] == {"streaming": True}
    assert [skill["id"] for skill in card["skills"]] == [
        "order-status",
        "start-return",
        "refund-estimate",
        "cancel-order",
    ]
    assert "examples" not in card["skills"][3]
    assert card["supportedInterfaces"][0]["protocolBinding"] == a2a.BINDING_JSONRPC


def test_baseline_completes_every_declared_example(agent: Any) -> None:
    examples = [example for skill in agent.skills for example in skill.get("examples", [])]
    assert examples == [WHERE_IS, SHIPPED, START_RETURN, REFUND]
    for example in examples:
        task = ask(agent, example)
        assert task["status"]["state"] == a2a.TASK_STATE_COMPLETED, example
        assert task["artifacts"][0]["parts"][0]["mediaType"] == "text/plain"
        assert answer_text(task)
    assert answer_text(ask(agent, START_RETURN)).startswith("Return RMA-48213-2")
    assert "EUR 42.90" in answer_text(ask(agent, REFUND))


def test_regressed_mode_interrupts_returns_and_fails_every_third_shipping_query(
    agent: Any,
) -> None:
    agent.mode = "regressed"
    task = ask(agent, START_RETURN)
    assert task["status"]["state"] == a2a.TASK_STATE_INPUT_REQUIRED
    assert "pickup address" in task["status"]["message"]["parts"][0]["text"]
    assert "artifacts" not in task

    states = [ask(agent, SHIPPED)["status"]["state"] for _ in range(6)]
    assert states == [
        a2a.TASK_STATE_COMPLETED,
        a2a.TASK_STATE_COMPLETED,
        a2a.TASK_STATE_FAILED,
        a2a.TASK_STATE_COMPLETED,
        a2a.TASK_STATE_COMPLETED,
        a2a.TASK_STATE_FAILED,
    ]
    # Other inputs are not affected, and the baseline never fails, not even on a
    # call number that the regression would fail (the ninth call below).
    assert ask(agent, WHERE_IS)["status"]["state"] == a2a.TASK_STATE_COMPLETED
    agent.mode = "baseline"
    for _ in range(3):
        assert ask(agent, SHIPPED)["status"]["state"] == a2a.TASK_STATE_COMPLETED
    assert ask(agent, START_RETURN)["status"]["state"] == a2a.TASK_STATE_COMPLETED


def test_answer_delays_cycle_deterministically(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []
    monkeypatch.setattr(make_sample.time, "sleep", sleeps.append)
    first = make_sample.HarborReturns()
    for _ in range(8):
        ask(first, SHIPPED)
    second = make_sample.HarborReturns()
    for _ in range(8):
        ask(second, WHERE_IS)
    assert sleeps[:8] == sleeps[8:]
    assert sleeps[:6] == list(make_sample.DELAYS_S)
    assert all(0 < delay < 0.5 for delay in sleeps)


def test_credential_leak_check_catches_the_header_and_the_bare_token() -> None:
    header = make_sample.FAKE_CREDENTIAL
    token = header.split()[1]
    clean = {
        "run-1": '{"headers": {"authorization": "[REDACTED]"}, "text": "Order 48213 shipped."}'
    }
    assert make_sample.credential_leaked(clean) is False
    assert make_sample.credential_leaked({}) is False
    assert make_sample.credential_leaked({"run-1": f"Authorization: {header}"}) is True
    assert make_sample.credential_leaked({"run-1": f"token={token}"}) is True
    assert make_sample.credential_leaked({"run-1": "clean", "run-2": token}) is True
    assert make_sample.credential_leaked({"run-1": token}, credential="Bearer other-token") is False
