"""The CI gate (schema §2: CI adapter), as three separate answers.

A pipeline asks three different questions, and a signed report answers none
of them by itself:

1. **execution**: did the attestation run to the end (``completed``)?
2. **verification**: do the signature, the hashes and the counts hold, and is
   the issuer trusted and the attestation fresh?
3. **policy**: does the latest recorded decision approve, under the policy in
   force?

``suncly gate`` exits 0 only when all three are yes. ``suncly attest`` keeps
its exit codes: 0 there means completed and signed, never approved
(docs/API.md).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from suncly.core.integrity import LayeredVerification, TrustContext, verify_layers
from suncly.domain.models import JsonObject

#: Exit codes of ``suncly gate``.
GATE_APPROVED = 0
GATE_EXECUTION_FAILED = 10
GATE_VERIFICATION_FAILED = 11
GATE_NOT_APPROVED = 12
GATE_UNREADABLE = 13


@dataclass(frozen=True)
class GateResult:
    execution_ok: bool
    execution_detail: str
    verification_ok: bool
    verification: LayeredVerification | None
    policy_ok: bool
    policy_detail: str
    exit_code: int

    @property
    def approved(self) -> bool:
        return self.exit_code == GATE_APPROVED

    def to_json(self) -> JsonObject:
        return {
            "approved": self.approved,
            "exit_code": self.exit_code,
            "execution": {"ok": self.execution_ok, "detail": self.execution_detail},
            "verification": self.verification.to_json()
            if self.verification is not None
            else {"ok": False, "detail": "not run"},
            "policy": {"ok": self.policy_ok, "detail": self.policy_detail},
        }


def evaluate_gate(
    result: JsonObject,
    transcript_files: Mapping[str, bytes],
    trust: TrustContext,
    public_key: bytes | None = None,
    require_trusted_issuer: bool = True,
) -> GateResult:
    attestation: Any = result.get("attestation") if isinstance(result, dict) else None
    if not isinstance(attestation, dict):
        return GateResult(
            False, "no attestation in the result document", False, None, False, "", GATE_UNREADABLE
        )
    status = str(attestation.get("status"))
    execution_ok = status == "completed"
    execution_detail = f"attestation status {status}"
    verification = verify_layers(result, transcript_files, trust, public_key)
    verification_ok = verification.cryptographically_valid and verification.fresh
    if require_trusted_issuer:
        verification_ok = verification_ok and verification.issuer_trusted
    decisions = result.get("decisions") if isinstance(result.get("decisions"), list) else []
    latest = decisions[-1] if decisions else None
    latest_outcome = latest.get("outcome") if isinstance(latest, dict) else None
    policy_ok = verification.policy_acceptable and latest_outcome == "approve"
    if latest is None:
        policy_detail = "no decision was recorded; no decision is never an approval"
    elif latest_outcome == "approve":
        policy_detail = (
            f"latest decision approve by {latest.get('decided_by')}"
            if verification.policy_acceptable
            else "approved, but the bound policy is not the policy in force"
        )
    else:
        policy_detail = f"latest decision {latest_outcome} by {latest.get('decided_by')}"
    if not execution_ok:
        code = GATE_EXECUTION_FAILED
    elif not verification_ok:
        code = GATE_VERIFICATION_FAILED
    elif not policy_ok:
        code = GATE_NOT_APPROVED
    else:
        code = GATE_APPROVED
    return GateResult(
        execution_ok,
        execution_detail,
        verification_ok,
        verification,
        policy_ok,
        policy_detail,
        code,
    )
