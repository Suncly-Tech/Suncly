"""Generate the website's sample evaluation from real Suncly runs.

The sample agent, "Harbor Returns Agent", is fictional and runs as a local mock
A2A server on this machine. Everything else is the real code path: the real
contract approval record, real Runner processes, real Layer 1 judgements, the
real flag-only Policy engine, real Ed25519 signatures and the real report
folder. The bundles written here are what `suncly attest` writes to a report
folder, plus the transcript files' exact bytes, so `suncly verify` and the
in-browser verifier agree.

Three attestations of the same agent are produced:

1. ``baseline``: the agent behaves; refund-estimate stays inconclusive because
   its criteria include a model check and Layer 2 does not exist yet.
2. ``regression``: the card is unchanged, the behaviour is not. start-return
   stops at TASK_STATE_INPUT_REQUIRED on every run and the second order-status
   example fails every third call.
3. ``budget-stop``: the same regressed agent with a budget of 7 attempts, so
   the attestation ends ``failed`` with runs never executed and no decision.

Usage, from the repository root with the package installed::

    .venv/bin/python frontend/scripts/make-sample.py

Output: ``frontend/lib/sample/harbor-*.json``. Each file holds ``result``
(result.json as written), ``transcripts`` (file name stem -> exact file text)
and ``report_md``. Nothing in the output is a real customer, endpoint or
credential; the Authorization header below is a made-up value that exists only
to show the Runner's redaction at work.

``main()`` takes the output folder, the Suncly home, the repetitions per test
case and the budget of the third attestation as parameters, so that
``tests/e2e/test_make_sample.py`` can run it into a temporary folder with fewer
runs. The defaults are what the website ships.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
import uuid
from collections import Counter
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any, ClassVar

from suncly.adapters.config_loader import load_config
from suncly.cli.output import Console, ProgressPrinter
from suncly.cli.wiring import build_services
from suncly.core.attestation import AttestationService, AttestRequest
from suncly.domain import a2a
from suncly.domain.contract_file import parse_contract_file
from suncly.domain.models import RiskLevel
from suncly.mock_agents.behaviours import (
    Behaviour,
    CallContext,
    base_card,
    completed_task,
    failed_task,
)
from suncly.mock_agents.server import MockAgentServer

JsonObject = dict[str, Any]

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "frontend" / "lib" / "sample"

#: A made-up credential. It never reaches the agent in the clear in any transcript,
#: because the Runner redacts it before the transcript leaves the Runner (DR-003).
FAKE_CREDENTIAL = "Bearer hc-sandbox-7f3a9c1e-sample-token-not-real"
OWNER = "Harbor Commerce platform team (fictional)"

#: The agent answers after one of these delays, in turn, so the sample latencies vary
#: without a pseudo-random generator and are the same on every regeneration.
DELAYS_S: tuple[float, ...] = (0.09, 0.31, 0.17, 0.42, 0.24, 0.12)

ORDER_STATUS: JsonObject = {
    "id": "order-status",
    "name": "Order status",
    "description": "Tells a customer where an order is and when it will arrive.",
    "tags": ["orders", "read-only"],
    "examples": ["Where is order 48213?", "Has order 48213 shipped yet?"],
}
START_RETURN: JsonObject = {
    "id": "start-return",
    "name": "Start a return",
    "description": (
        "Opens a return for one or more items of a delivered order and emails a prepaid label."
    ),
    "tags": ["returns", "writes"],
    "examples": ["Start a return for order 48213, item 2"],
}
REFUND_ESTIMATE: JsonObject = {
    "id": "refund-estimate",
    "name": "Refund estimate",
    "description": "Estimates the refund for a return, including restocking fees.",
    "tags": ["returns", "read-only"],
    "examples": ["How much will I get back if I return order 48213?"],
}
CANCEL_ORDER: JsonObject = {
    "id": "cancel-order",
    "name": "Cancel an order",
    "description": "Cancels an order that has not shipped yet. Declares no examples.",
    "tags": ["orders", "writes"],
}


def _text_of(params: JsonObject) -> str:
    message = params.get("message") or {}
    for part in message.get("parts") or []:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            return str(part["text"])
    return ""


def _text(answer: str) -> list[JsonObject]:
    return [{"text": answer, "mediaType": "text/plain"}]


def credential_leaked(transcripts: Mapping[str, str], credential: str = FAKE_CREDENTIAL) -> bool:
    """True if the credential, or its token part alone, appears in any transcript text."""
    needles = {credential, credential.split()[1]}
    return any(needle in text for text in transcripts.values() for needle in needles)


def input_required_task(question: str) -> JsonObject:
    return {
        "id": uuid.uuid4().hex,
        "contextId": uuid.uuid4().hex,
        "status": {
            "state": a2a.TASK_STATE_INPUT_REQUIRED,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": {
                "messageId": uuid.uuid4().hex,
                "role": a2a.ROLE_AGENT,
                "parts": [{"text": question}],
            },
        },
    }


class HarborReturns(Behaviour):
    """A fictional returns agent with a switchable behaviour and an unchanged card."""

    name = "harbor-returns"
    description = (
        "Looks up orders, starts returns and estimates refunds for Harbor Commerce customers."
    )
    skills: ClassVar[list[JsonObject]] = [ORDER_STATUS, START_RETURN, REFUND_ESTIMATE, CANCEL_ORDER]

    def __init__(self) -> None:
        self.mode = "baseline"
        self._per_input: Counter[str] = Counter()
        self._calls = 0
        self._lock = threading.Lock()

    def card(self, base_url: str, context: CallContext) -> JsonObject:
        card = base_card(
            base_url, "Harbor Returns Agent", self.description, self.skills, version="2.3.1"
        )
        card["capabilities"] = {"streaming": True}
        card["provider"] = {
            "organization": "Harbor Commerce (fictional)",
            "url": "https://harbor.example",
        }
        return card

    def send_message(self, params: JsonObject, context: CallContext) -> JsonObject:
        text = _text_of(params)
        lowered = text.lower()
        with self._lock:
            self._per_input[text] += 1
            calls_for_input = self._per_input[text]
            self._calls += 1
            delay = DELAYS_S[(self._calls - 1) % len(DELAYS_S)]
        time.sleep(delay)

        if lowered.startswith("start a return"):
            if self.mode == "regressed":
                return {
                    "task": input_required_task("Which pickup address should the return label use?")
                }
            return {
                "task": completed_task(
                    _text(
                        "Return RMA-48213-2 is open for order 48213, item 2. A prepaid label "
                        "was emailed to the customer; the refund is issued when the parcel "
                        "scans at the carrier."
                    )
                )
            }
        if "shipped" in lowered:
            if self.mode == "regressed" and calls_for_input % 3 == 0:
                return {"task": failed_task("order-service: upstream timeout after 8000 ms")}
            return {
                "task": completed_task(
                    _text(
                        "Yes. Order 48213 shipped on 2 October and is with the carrier "
                        "(tracking HC-2210-5581)."
                    )
                )
            }
        if lowered.startswith("where is"):
            return {
                "task": completed_task(
                    _text(
                        "Order 48213 is in transit and is expected on Tuesday 7 October. "
                        "Tracking: HC-2210-5581."
                    )
                )
            }
        if lowered.startswith("how much"):
            return {
                "task": completed_task(
                    _text(
                        "If you return order 48213 in full you would receive EUR 42.90, the "
                        "order total of EUR 47.90 minus a EUR 5.00 restocking fee, to the "
                        "original payment method within 5 to 7 business days."
                    )
                )
            }
        return {
            "task": completed_task(
                _text("I can help with order status, returns and refund estimates.")
            )
        }


def main(
    out_dir: Path = OUT_DIR,
    *,
    home: Path | None = None,
    runs: int = 5,
    budget_stop: Decimal = Decimal(7),
    pause_s: float = 1.5,
) -> int:
    """Write the contract and the three bundles to ``out_dir``; 0 on success."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if home is None:
        home = Path(tempfile.mkdtemp(prefix="suncly-sample-home-"))
    reports = home / "reports"
    env = {
        **os.environ,
        "SUNCLY_HOME": str(home),
        "SUNCLY_REPORTS_DIR": str(reports),
        "SUNCLY_LATENCY_LIMIT_MS": "2000",
    }
    # Only the Runner process reads this; it is redacted from every transcript.
    os.environ["SUNCLY_AGENT_AUTHORIZATION"] = FAKE_CREDENTIAL
    config = load_config(env, home)
    behaviour = HarborReturns()
    console = Console()

    with MockAgentServer(behaviour) as server:
        console.heading(f"Sample agent at {server.card_url}")

        # 1. Export the drafted contract and add the criteria a reviewer would add.
        services = build_services(config)
        try:
            # The agent record (owner, risk level) is created on first sight of the card URL,
            # so the draft export carries the same values as the runs below.
            exported = AttestationService(services).attest(
                AttestRequest(
                    card_url=server.card_url,
                    sandbox_declared=True,
                    runs=runs,
                    owner=OWNER,
                    risk_level=RiskLevel.MEDIUM,
                    export_draft=True,
                )
            )
        finally:
            services.store.close()
        assert exported.exported_contract_file is not None
        draft = json.loads(exported.exported_contract_file)
        for test_case in draft["test_cases"]:
            test_case["criteria"]["required_fields"] = ["/artifacts/0/parts/0/text"]
            if test_case["skill_id"] == "refund-estimate":
                # A check Layer 1 cannot decide. The sample runs without a judge model, so
                # every run of this test case is inconclusive, and the report says so.
                test_case["criteria"]["model_checks"] = [
                    {
                        "name": "refund_arithmetic",
                        "criterion": "the amount equals the order total minus the restocking fee",
                        "expected": "yes_no",
                        "pass_rule": "yes",
                    }
                ]
        contract_file = parse_contract_file(json.dumps(draft))
        (out_dir / "harbor-contract.json").write_text(
            json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )

        def request(budget: Decimal | None) -> AttestRequest:
            return AttestRequest(
                card_url=server.card_url,
                sandbox_declared=True,
                runs=runs,
                budget_limit=budget,
                owner=OWNER,
                risk_level=RiskLevel.MEDIUM,
                approve_as="m.lind@harbor.example",
                contract_file=contract_file,
            )

        plan = (
            ("1-baseline", "baseline", None),
            ("2-regression", "regressed", None),
            ("3-budget-stop", "regressed", budget_stop),
        )
        for label, mode, budget in plan:
            behaviour.mode = mode
            console.heading(f"=== attestation {label} (behaviour: {mode}) ===")
            services = build_services(config, ProgressPrinter(console))
            try:
                outcome = AttestationService(services).attest(request(budget))
            finally:
                services.store.close()
            assert outcome.report_dir is not None
            folder = outcome.report_dir
            result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
            transcripts = {
                path.stem: path.read_text(encoding="utf-8")
                for path in sorted((folder / "transcripts").glob("*.json"))
            }
            bundle = {
                "sample": {
                    "label": label,
                    "behaviour": mode,
                    "generated_by": "frontend/scripts/make-sample.py",
                    "note": (
                        "Synthetic sample. Produced by the real Suncly code path against a "
                        "fictional local mock agent. Not a customer evaluation."
                    ),
                },
                "result": result,
                "transcripts": transcripts,
                "report_md": (folder / "report.md").read_text(encoding="utf-8"),
            }
            target = out_dir / f"harbor-{label}.json"
            target.write_text(
                json.dumps(bundle, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
            )
            console.line(f"wrote {target} ({target.stat().st_size} bytes)")
            if credential_leaked(transcripts):
                console.line("ERROR: the fake credential leaked into a transcript", fg="red")
                return 1
            time.sleep(pause_s)
    console.line(f"\nSample bundles written to {out_dir}. Suncly home used: {home}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
