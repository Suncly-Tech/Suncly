"""The self-contained HTML report: inline styles, no external assets, opens offline."""

from __future__ import annotations

import json
from html import escape

from suncly.adapters.report.view import ReportView

STYLE = """
:root { color-scheme: light dark; --ok: #1a7f37; --bad: #b42318; --mid: #9a6700;
        --line: #d0d7de; }
body { font: 15px/1.5 system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0 auto;
       max-width: 960px; padding: 24px 16px; }
h1 { font-size: 1.6rem; margin: 0 0 8px; } h2 { font-size: 1.2rem; margin: 32px 0 8px; }
.decision { border: 2px solid var(--mid); border-radius: 8px; padding: 12px 16px; margin: 16px 0; }
.decision strong { font-size: 1.1rem; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 0.95rem; }
th, td { border: 1px solid var(--line); padding: 6px 8px; text-align: left; vertical-align: top; }
th { background: rgba(127,127,127,0.12); }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.pass { color: var(--ok); font-weight: 600; } .fail { color: var(--bad); font-weight: 600; }
.inconclusive { color: var(--mid); font-weight: 600; }
code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.9em;
       word-break: break-all; }
.note { background: rgba(127,127,127,0.1); border-left: 4px solid var(--line);
        padding: 8px 12px; margin: 8px 0; }
details { margin: 6px 0; } summary { cursor: pointer; }
"""


def _kv(values: dict[str, str]) -> str:
    rows = "".join(
        f"<tr><th>{escape(k)}</th><td><code>{escape(v)}</code></td></tr>" for k, v in values.items()
    )
    return f"<table>{rows}</table>"


def _check_state(passed: object) -> str:
    if passed is True:
        return "passed"
    if passed is False:
        return "failed"
    return "undecided"


def render_html(view: ReportView) -> str:
    out: list[str] = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>{escape(view.title)}</title>",
        f"<style>{STYLE}</style></head><body>",
        f"<h1>{escape(view.title)}</h1>",
    ]
    detail = f"<div>{escape(view.decision_detail)}</div>" if view.decision_detail else ""
    out.append(f'<div class="decision"><strong>{escape(view.decision_line)}</strong>{detail}</div>')
    out.append(
        f"<p>Attestation status: <strong>{escape(view.status)}</strong>. "
        f"Generated {escape(view.generated_at)}.</p>"
    )
    out += [f'<div class="note">{escape(note)}</div>' for note in view.notes]

    out.append("<h2>Results per test case</h2>")
    out.append(
        "<table><tr><th>Skill</th><th>Kind</th><th>Input</th>"
        "<th>pass</th><th>fail</th><th>inconclusive</th></tr>"
    )
    for row in view.verdict_rows:
        out.append(
            f"<tr><td>{escape(row.skill_id)}</td><td>{escape(row.kind)}</td>"
            f"<td>{escape(row.input_preview)}</td>"
            f'<td class="num pass">{row.pass_count}</td>'
            f'<td class="num fail">{row.fail_count}</td>'
            f'<td class="num inconclusive">{row.inconclusive_count}</td></tr>'
        )
    out.append("</table>")
    out.append(
        f"<p>Totals across test cases: pass {view.pass_total}, fail {view.fail_total}, "
        f"inconclusive {view.inconclusive_total}. These are counts, not a score.</p>"
    )

    out += ["<h2>What was NOT tested</h2>", "<ul>"]
    out += [f"<li><strong>{escape(c)}:</strong> {escape(d)}</li>" for c, d in view.not_tested]
    out.append("</ul>")
    if view.not_executed:
        out.append("<p>Runs never executed:</p><ul>")
        out += [f"<li>{escape(line)}</li>" for line in view.not_executed]
        out.append("</ul>")

    out += ["<h2>Attestation</h2>", _kv(view.attestation)]
    out += ["<h2>Agent Card</h2>", _kv(view.card)]
    out += ["<h2>Card re-check at the end</h2>", _kv(view.recheck)]
    out += ["<h2>Contract</h2>", _kv(view.contract), "<h3>Test cases and criteria</h3><ul>"]
    for row in view.verdict_rows:
        criteria = escape(json.dumps(row.criteria, sort_keys=True))
        out.append(
            f"<li><strong>{escape(row.skill_id)}</strong> ({escape(row.kind)}), test case "
            f"<code>{escape(row.test_case_id)}</code><br>input: {escape(row.input_preview)}"
            f"<br>criteria: <code>{criteria}</code></li>"
        )
    out.append("</ul>")

    out += ["<h2>Signature</h2>", _kv(view.signature)]

    out.append("<h2>Runs</h2>")
    out.append(
        "<table><tr><th>Skill</th><th>Attempt</th><th>Verdict</th><th>Latency (ms)</th>"
        "<th>Outcome</th><th>Checks</th><th>Transcript</th></tr>"
    )
    for run in view.runs:
        checks = "".join(
            f"<li>{escape(str(c.get('name')))}: {_check_state(c.get('passed'))} "
            f"({escape(str(c.get('detail')))})</li>"
            for c in run.checks
        )
        latency = run.latency_ms if run.latency_ms is not None else "-"
        out.append(
            f'<tr><td>{escape(run.skill_id)}</td><td class="num">{run.attempt}</td>'
            f'<td class="{escape(run.verdict)}">{escape(run.verdict)}</td>'
            f'<td class="num">{latency}</td><td>{escape(run.outcome)}</td>'
            f"<td><details><summary>{escape(run.summary)}</summary><ul>{checks}</ul>"
            f"</details></td><td><code>{escape(run.transcript_file)}</code></td></tr>"
        )
    out.append("</table>")

    out.append("<h2>Proposals in effect</h2><ul>")
    out += [f"<li>{escape(p)}</li>" for p in view.proposals]
    out.append("</ul><p>Open questions are listed in the docs; none is decided by this report.</p>")
    out.append("</body></html>")
    return "\n".join(out)
