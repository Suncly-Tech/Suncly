"""The Markdown report."""

from __future__ import annotations

import json

from suncly.adapters.report.view import ReportView


def _table(headers: list[str], rows: list[list[str]]) -> str:
    def cell(value: str) -> str:
        return value.replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(cell(v) for v in row) + " |" for row in rows)
    return "\n".join(lines)


def _kv(values: dict[str, str]) -> str:
    return _table(["Field", "Value"], [[k, v] for k, v in values.items()])


def render_markdown(view: ReportView) -> str:
    parts: list[str] = [f"# {view.title}", ""]
    parts += [f"**{view.decision_line}**", ""]
    if view.decision_detail:
        parts += [view.decision_detail, ""]
    parts += [f"Attestation status: **{view.status}**. Generated {view.generated_at}.", ""]
    for note in view.notes:
        parts += [f"> {note}", ""]

    parts += ["## Results per test case", ""]
    parts += [
        _table(
            ["Skill", "Kind", "Input", "pass", "fail", "inconclusive"],
            [
                [
                    r.skill_id,
                    r.kind,
                    r.input_preview,
                    str(r.pass_count),
                    str(r.fail_count),
                    str(r.inconclusive_count),
                ]
                for r in view.verdict_rows
            ],
        ),
        "",
        (
            f"Totals across test cases: pass {view.pass_total}, fail {view.fail_total}, "
            f"inconclusive {view.inconclusive_total}. These are counts, not a score."
        ),
        "",
    ]

    parts += ["## What was NOT tested", ""]
    parts += [f"- **{category}:** {detail}" for category, detail in view.not_tested]
    if view.not_executed:
        parts += ["", "Runs never executed:", ""]
        parts += [f"- {line}" for line in view.not_executed]
    parts += [""]

    parts += ["## Attestation", "", _kv(view.attestation), ""]
    parts += ["## Agent Card", "", _kv(view.card), ""]
    parts += ["## Card re-check at the end", "", _kv(view.recheck), ""]
    parts += ["## Contract", "", _kv(view.contract), ""]
    parts += ["### Test cases and criteria", ""]
    for row in view.verdict_rows:
        parts += [
            f"- **{row.skill_id}** ({row.kind}), test case `{row.test_case_id}`",
            f"  - input: {row.input_preview}",
            f"  - criteria: `{json.dumps(row.criteria, sort_keys=True)}`",
        ]
    parts += [""]

    parts += ["## Signature", "", _kv(view.signature), ""]

    parts += ["## Runs", ""]
    parts += [
        _table(
            ["Skill", "Attempt", "Verdict", "Latency (ms)", "Outcome", "Summary", "Transcript"],
            [
                [
                    r.skill_id,
                    str(r.attempt),
                    r.verdict,
                    str(r.latency_ms) if r.latency_ms is not None else "-",
                    r.outcome,
                    r.summary,
                    r.transcript_file,
                ]
                for r in view.runs
            ],
        ),
        "",
    ]

    parts += ["## Proposals in effect", ""]
    parts += [f"- {p}" for p in view.proposals]
    parts += ["", "Open questions are listed in the docs; none is decided by this report.", ""]
    return "\n".join(parts)
