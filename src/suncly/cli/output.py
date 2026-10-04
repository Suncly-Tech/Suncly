"""Terminal output: colour when the terminal supports it, plain text otherwise."""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence
from typing import Any, TextIO

import click

from suncly.adapters.report.view import ReportView


def wants_colour(stream: TextIO, env: dict[str, str] | None = None) -> bool:
    environment = os.environ if env is None else env
    if environment.get("NO_COLOR"):
        return False
    if environment.get("TERM") == "dumb":
        return False
    return bool(getattr(stream, "isatty", lambda: False)())


class Console:
    """Prints to a stream; plain text when colour is unwanted or the stream is not a terminal."""

    def __init__(self, stream: TextIO | None = None, colour: bool | None = None) -> None:
        self.stream = stream or sys.stdout
        self.colour = wants_colour(self.stream) if colour is None else colour

    def style(self, text: str, **kwargs: Any) -> str:
        return click.style(text, **kwargs) if self.colour else text

    def line(self, text: str = "", **kwargs: Any) -> None:
        click.echo(self.style(text, **kwargs) if kwargs else text, file=self.stream)

    def heading(self, text: str) -> None:
        self.line()
        self.line(text, bold=True)

    def table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        numeric: frozenset[int] = frozenset(),
    ) -> None:
        widths = [len(h) for h in headers]
        for row in rows:
            for index, cell in enumerate(row):
                widths[index] = max(widths[index], len(cell))

        def fmt(cells: Sequence[str]) -> str:
            return "  ".join(
                (cell.rjust(widths[i]) if i in numeric else cell.ljust(widths[i]))
                for i, cell in enumerate(cells)
            ).rstrip()

        self.line(fmt(headers), bold=True)
        self.line(fmt(["-" * w for w in widths]))
        for row in rows:
            self.line(fmt(row))

    def verdict(self, verdict: str) -> str:
        colours = {"pass": "green", "fail": "red", "inconclusive": "yellow"}
        return self.style(verdict, fg=colours.get(verdict))


class ProgressPrinter:
    """A ``ProgressListener`` that narrates an attestation on the console."""

    def __init__(self, console: Console, quiet: bool = False) -> None:
        self.console = console
        self.quiet = quiet

    def on_event(self, event: str, **d: Any) -> None:
        if self.quiet:
            return
        c = self.console
        if event == "key_created":
            c.line(
                f"Created a deployment signing key ({d['key_id']}). "
                "The private key stays in your Suncly home folder."
            )
        elif event == "card_fetched":
            c.line(
                f"Fetched the Agent Card of '{d['name']}': {d['skills']} skill(s), "
                f"card_hash {d['card_hash']}"
            )
            c.line(f"Target endpoint: {d['target_url']}")
        elif event == "contract_reused":
            c.line(f"Using contract version {d['version']}, approved by {d['approved_by']}.")
        elif event == "contract_approved":
            c.line(f"Contract version {d['version']} approved by {d['approved_by']}.")
        elif event == "plan":
            c.line(
                f"Attestation {d['attestation_id']}: {d['test_cases']} test case(s) x "
                f"{d['runs']} run(s) = {d['planned_runs']} planned run(s); "
                f"budget {d['budget_limit']} attempt(s)."
            )
            c.line()
        elif event == "run_recorded":
            latency = f"{d['latency_ms']} ms" if d.get("latency_ms") is not None else "no response"
            skill = d.get("skill_id") or "-"
            preview = d.get("input_preview") or ""
            verdict = c.verdict(d["verdict"])
            c.line(
                f"  {skill:<14} {preview:<25} run {d['attempt']:>3}  {verdict:<22} "
                f"{latency:>10}  {d['summary']}"
            )
        elif event == "run_retry":
            c.line(f"  attempt {d['attempt']:>3}  retry {d['retry']}: {d['error']}", fg="yellow")
        elif event == "run_withheld":
            c.line(
                f"  attempt {d['attempt']}: transcript withheld (redaction failed); "
                "run not recorded",
                fg="yellow",
            )
        elif event == "budget_stop":
            c.line(
                f"Budget reached: cost_total {d['cost_total']} of {d['budget_limit']}. "
                "No more runs start.",
                fg="yellow",
            )
        elif event == "card_recheck":
            detail = f" ({d['detail']})" if d.get("detail") else ""
            c.line(f"Card re-check: {d['outcome']}{detail}")
        elif event == "attestation_status" and d["status"] in ("failed", "invalidated"):
            c.line(f"Attestation status: {d['status']}", fg="yellow")


def print_summary(console: Console, view: ReportView, report_dir: str) -> None:
    c = console
    c.heading(f"Results for {view.agent_name}")
    c.table(
        ["Skill", "Input", "pass", "fail", "inconclusive"],
        [
            [
                r.skill_id,
                r.input_preview,
                str(r.pass_count),
                str(r.fail_count),
                str(r.inconclusive_count),
            ]
            for r in view.verdict_rows
        ],
        numeric=frozenset({2, 3, 4}),
    )
    c.line()
    c.line(view.decision_line, bold=True)
    if view.decision_detail:
        c.line(view.decision_detail)
    c.line()
    c.line(
        f"Attestation {view.attestation['id']}: status {view.status}, "
        f"cost {view.attestation['cost_total']} of budget {view.attestation['budget_limit']}."
    )
    if view.not_executed:
        c.line(f"{len(view.not_executed)} planned run(s) were never executed.", fg="yellow")
    c.line(
        f"Signed with key {view.signature['signing_key_id']}. "
        f'Verify with: suncly verify "{report_dir}"'
    )
    c.heading("What was NOT tested")
    for category, detail in view.not_tested:
        c.line(f"  - {category}: {detail}")
    c.line()
    c.line(f"Report: {report_dir}")
    if view.status == "completed":
        c.line(
            "Exit code 0 means the attestation completed and was signed. "
            "It does not mean the agent was approved."
        )
