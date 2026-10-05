"""Adapters for external evaluation tools, each pinned to one version (ports/external_tools.py).

| Tool | Version | Licence | Invocation |
|---|---|---|---|
| A2A TCK | ``1.0.0.alpha2`` (tag, ``29063fe9``) | Apache-2.0 | ``run_tck.py --sut-host <url>`` |
| Promptfoo | ``0.123.1`` (npm) | MIT | ``promptfoo eval -c <pack> -o <results.json>`` |

The tools are not vendored and not installed by Suncly's own package: the
worker image installs them at these exact versions (``deploy/Dockerfile``),
and each adapter refuses to run when the installed version differs. Their
output files are kept byte for byte as artifacts; the normalized checks are
what the evidence and the policy read.
"""

from suncly.adapters.external.a2a_tck import A2A_TCK_VERSION, A2ATckRunner, normalize_tck_report
from suncly.adapters.external.process import ToolProcess, ToolProcessResult
from suncly.adapters.external.promptfoo import (
    PROMPTFOO_VERSION,
    PromptfooRunner,
    normalize_promptfoo_results,
)

__all__ = [
    "A2A_TCK_VERSION",
    "PROMPTFOO_VERSION",
    "A2ATckRunner",
    "PromptfooRunner",
    "ToolProcess",
    "ToolProcessResult",
    "normalize_promptfoo_results",
    "normalize_tck_report",
]
