"""CI adapter (schema §2): see ``suncly.core.ci_gate``; this module re-exports it."""

from suncly.core.ci_gate import GateResult, evaluate_gate

__all__ = ["GateResult", "evaluate_gate"]
