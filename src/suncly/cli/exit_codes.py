"""Exit codes of the ``suncly`` command (documented in docs/API.md).

Exit code 0 never means the agent was approved. It means the attestation ran
to the end, was decided and signed, and the card did not change.
"""

from __future__ import annotations

from suncly.domain.errors import RefusedError, SunclyError, VerificationFailedError

OK = 0
"""The attestation completed: decided (``flag``) and signed. Not an approval."""
INTERNAL_ERROR = 1
"""Suncly itself failed. Run with --debug for the traceback."""
USAGE = 2
"""Wrong arguments (click's own code)."""
REFUSED = 3
"""Nothing ran: no sandbox declaration, no approval, card unusable, contract unusable."""
FAILED = 4
"""The attestation ended failed: the budget stopped it, or the card could not be re-fetched."""
INVALIDATED = 5
"""The attestation ended invalidated: the card changed while it ran."""
VERIFICATION_FAILED = 6
"""``suncly verify`` found a mismatch, or ``suncly doctor`` found a problem."""

OUTCOME_CODES = {
    "completed": OK,
    "failed": FAILED,
    "invalidated": INVALIDATED,
    "draft_exported": OK,
}


def code_for(error: SunclyError) -> int:
    if isinstance(error, RefusedError):
        return REFUSED
    if isinstance(error, VerificationFailedError):
        return VERIFICATION_FAILED
    return INTERNAL_ERROR
