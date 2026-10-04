"""Suncly's error model: what happened, why, and what to do next.

Every user-facing error carries up to three sentences. The CLI prints them as
they are; nothing else is shown unless ``--debug`` is given.
"""

from __future__ import annotations


class SunclyError(Exception):
    """Base error. ``what`` is required; ``why`` and ``next_step`` are optional sentences."""

    def __init__(self, what: str, why: str = "", next_step: str = "") -> None:
        self.what = what
        self.why = why
        self.next_step = next_step
        super().__init__(" ".join(part for part in (what, why, next_step) if part))


class RefusedError(SunclyError):
    """Suncly refused to start or continue. Nothing ran against the agent."""


class CardError(RefusedError):
    """The Agent Card could not be fetched, parsed or attested."""


class CardNotParsableError(CardError):
    """The card is not usable JSON (OQ-A11: creates no records, fails visibly)."""


class CardFetchError(CardError):
    """The card could not be fetched from its URL."""


class CardNotAttestableError(CardError):
    """The card can be parsed but there is nothing to attest, for example no skills."""


class SandboxDeclarationMissingError(RefusedError):
    """DR-006: the user has not declared the endpoint a sandbox or dry-run endpoint."""


class ContractError(RefusedError):
    """A contract or contract file is unusable."""


class ApprovalRequiredError(RefusedError):
    """No approved contract exists and no approval was given; nothing runs (schema §2)."""


class StoreError(SunclyError):
    """The evidence store refused an operation, usually an append-only or key rule."""


class TranscriptExistsError(StoreError):
    """A transcript with this key was written before; evidence is never overwritten (DR-002)."""


class SigningError(SunclyError):
    """Signing or key handling failed. The attestation is not reported as approved."""


class VerificationFailedError(SunclyError):
    """``suncly verify`` found a mismatch."""


class ConfigError(SunclyError):
    """A configuration value is invalid."""


class RunnerError(SunclyError):
    """The Runner could not execute a run."""


class TargetHostRefusedError(RunnerError):
    """The Runner refused a request to a host other than the target (schema §2)."""
