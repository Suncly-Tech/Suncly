"""Attestation signatures (schema §7, §11).

The payload is the canonicalized JSON (RFC 8785) of: the attestation id, the
``card_hash``, the contract id and version, the per-test-case aggregated
results, the hash of every run's evidence document, the decision outcome and
``policy_version``. It is signed with the deployment's Ed25519 key, identified
by ``signing_key_id``. Encoding and key identification are proposals (OQ-A8).
For an attestation without a decision the decision fields are ``null``
(OQ-F7, the documents' proposal).
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

from suncly.domain.canonical import canonical_json
from suncly.domain.errors import SigningError
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import Attestation, Contract, Decision, JsonObject
from suncly.ports.signer import Signer

PAYLOAD_VERSION = 1
SIGNATURE_PREFIX = "ed25519:"
KEY_ID_PREFIX = "ed25519-"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    padding = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + padding)


def key_id_for(public_key: bytes) -> str:
    """``signing_key_id``: a fingerprint of the public key (OQ-A8, proposal)."""
    return KEY_ID_PREFIX + hashlib.sha256(public_key).hexdigest()[:16]


def build_payload(
    *,
    attestation: Attestation,
    card_hash: str,
    contract: Contract,
    results: Sequence[TestCaseResult],
    transcript_hashes: Mapping[str, str],
    decision: Decision | None,
) -> JsonObject:
    """The signed payload of schema §11, as a JSON object.

    Results are ordered by test case id and transcript hashes by run id, so the
    payload is the same whichever order a store returns records in.
    """
    return {
        "payload_version": PAYLOAD_VERSION,
        "attestation_id": str(attestation.id),
        "card_hash": card_hash,
        "contract": {"id": str(contract.id), "version": contract.version},
        "results": [
            result.to_payload()
            for result in sorted(results, key=lambda result: str(result.test_case_id))
        ],
        "transcript_hashes": dict(sorted(transcript_hashes.items())),
        "decision": None
        if decision is None
        else {"outcome": decision.outcome.value, "policy_version": decision.policy_version},
    }


def payload_bytes(payload: JsonObject) -> bytes:
    return canonical_json(payload)


def sign_payload(signer: Signer, payload: JsonObject) -> tuple[str, str]:
    """Sign and return ``(signature, signing_key_id)`` in their stored encodings."""
    try:
        raw = signer.sign(payload_bytes(payload))
    except Exception as exc:  # whatever the key adapter raises, nothing is reported as approved
        raise SigningError(
            "The attestation could not be signed.",
            f"The signer reported: {exc}.",
            "Check the deployment key with `suncly doctor`, or create one with `suncly keys init`.",
        ) from exc
    return SIGNATURE_PREFIX + b64url(raw), signer.key_id


def verify_payload(public_key: bytes, payload: JsonObject, signature: str) -> bool:
    """True when ``signature`` is a valid Ed25519 signature of ``payload`` under ``public_key``."""
    if not signature.startswith(SIGNATURE_PREFIX):
        return False
    try:
        raw = b64url_decode(signature[len(SIGNATURE_PREFIX) :])
        ed25519.Ed25519PublicKey.from_public_bytes(public_key).verify(raw, payload_bytes(payload))
    except (InvalidSignature, ValueError):
        return False
    return True


def replace_fields(attestation: Attestation, **changes: object) -> Attestation:
    """A copy of an attestation with the given fields changed, re-validated."""
    data = attestation.model_dump()
    data.update(changes)
    return Attestation.model_validate(data)


def with_signature(attestation: Attestation, signature: str, signing_key_id: str) -> Attestation:
    """The attestation record carrying the signature; status unchanged."""
    return replace_fields(attestation, signature=signature, signing_key_id=signing_key_id)
