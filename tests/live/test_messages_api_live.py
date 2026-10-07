"""One real question to the Anthropic Messages API through the judge subprocess.

Runs only when the operator sets the model key variable and the pinned model id
in the environment; CI sets neither, so the test is skipped there. It goes
through the real subprocess adapter, so the from-scratch environment, the
endpoint restriction and the redaction are exercised on the real network. It
spends one request on the configured model.
"""

from __future__ import annotations

import os

import pytest

from suncly.adapters.judge_subprocess import SubprocessModelJudge
from suncly.core import rubric
from suncly.core.config import env_var_for
from suncly.core.judge import interpret_answer
from suncly.domain.criteria import ModelCheck
from suncly.judge.key import JUDGE_KEY_ENV_VAR
from suncly.ports.model_judge import ModelRequest

pytestmark = pytest.mark.live

#: The Messages API endpoint (docs/IMPLEMENTATION_NOTES.md, section 4).
MESSAGES_API = "https://api.anthropic.com/v1/messages"

MODEL_ENV_VAR = env_var_for("judge_model")
ENDPOINT_ENV_VAR = env_var_for("judge_endpoint")

POLITE = ModelCheck(
    name="polite",
    criterion="the answer is polite and answers the customer's question",
    expected="yes_no",
    pass_rule="yes",
)


@pytest.mark.skipif(
    not (os.environ.get(JUDGE_KEY_ENV_VAR) and os.environ.get(MODEL_ENV_VAR)),
    reason=f"set {JUDGE_KEY_ENV_VAR} and {MODEL_ENV_VAR} to ask the real Messages API once",
)
def test_the_pinned_model_answers_one_question_in_shape() -> None:
    model = os.environ[MODEL_ENV_VAR]
    endpoint = os.environ.get(ENDPOINT_ENV_VAR) or MESSAGES_API
    judge = SubprocessModelJudge(endpoint, os.environ)
    prompt = rubric.build_prompt(
        POLITE,
        "Where is my order?",
        "Hello! Your order 1234 shipped yesterday and arrives tomorrow. "
        "Is there anything else I can help you with?",
    )
    response = judge.ask(ModelRequest(model=model, prompt=prompt, timeout_s=60.0))
    assert response.error is None, response.error
    assert response.model == model, "the answer must come from the pinned model (DR-004)"
    passed, answer, rationale = interpret_answer(POLITE, response, model)
    assert passed is True, rationale
    assert answer == "yes" and rationale
