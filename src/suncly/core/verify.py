"""Verifying a produced attestation (``suncly verify``).

Works from the report folder alone: the result document, the transcript
files and the public key it carries. Every check explains its mismatch.
"""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from suncly.core import signing
from suncly.domain.canonical import sha256_hex
from suncly.domain.card import compute_card_hash
from suncly.domain.models import JsonObject


@dataclass(frozen=True)
class VerificationCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class VerificationResult:
    checks: list[VerificationCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def to_json(self) -> JsonObject:
        return {
            "ok": self.ok,
            "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in self.checks],
        }


def _get(document: Any, *path: str) -> Any:
    current = document
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def verify_result(
    result: JsonObject, transcript_files: Mapping[str, bytes], public_key: bytes | None = None
) -> VerificationResult:
    """Check a ``result.json`` document against its transcript files and signature.

    ``transcript_files`` maps run id to the bytes of the stored evidence document.
    ``public_key`` overrides the key embedded in the result, for verifiers who
    obtained the deployment's public key out of band.
    """
    checks: list[VerificationCheck] = []
    attestation = _get(result, "attestation") or {}
    signature = attestation.get("signature")
    signing_key_id = attestation.get("signing_key_id")
    payload = _get(result, "signature_payload")

    checks.append(
        VerificationCheck(
            "signature present",
            bool(signature) and bool(signing_key_id),
            f"signing_key_id {signing_key_id}"
            if signature
            else "the attestation carries no signature",
        )
    )
    embedded = _get(result, "signer_public_key")
    key_bytes: bytes | None = public_key
    if key_bytes is None and isinstance(embedded, str):
        try:
            key_bytes = signing.b64url_decode(embedded)
        except ValueError:
            key_bytes = None
    if key_bytes is None:
        checks.append(VerificationCheck("public key", False, "no public key is available"))
    else:
        fingerprint = signing.key_id_for(key_bytes)
        checks.append(
            VerificationCheck(
                "public key matches signing_key_id",
                fingerprint == signing_key_id,
                f"the key's fingerprint is {fingerprint}, the attestation names {signing_key_id}",
            )
        )
    if not isinstance(payload, dict):
        checks.append(VerificationCheck("signature payload present", False, "no signature_payload"))
        return VerificationResult(checks)

    if key_bytes is not None and isinstance(signature, str):
        valid = signing.verify_payload(key_bytes, payload, signature)
        checks.append(
            VerificationCheck(
                "signature valid",
                valid,
                "the signature matches the payload"
                if valid
                else "the signature does not match the "
                "payload: the payload, the signature or the key was altered",
            )
        )

    raw_json = _get(result, "card_version", "raw_json")
    recorded_hash = _get(result, "card_version", "card_hash")
    try:
        recomputed = compute_card_hash(json.loads(raw_json)) if isinstance(raw_json, str) else None
    except (ValueError, TypeError):
        recomputed = None
    checks.append(
        VerificationCheck(
            "card_hash",
            recomputed is not None and recomputed == payload.get("card_hash") == recorded_hash,
            f"recomputed {recomputed}; payload {payload.get('card_hash')}; record {recorded_hash}",
        )
    )

    checks.append(
        VerificationCheck(
            "attestation and contract ids",
            payload.get("attestation_id") == attestation.get("id")
            and _get(payload, "contract", "id") == _get(result, "contract", "id")
            and _get(payload, "contract", "version") == _get(result, "contract", "version"),
            f"payload attestation {payload.get('attestation_id')}, contract "
            f"{_get(payload, 'contract', 'id')} v{_get(payload, 'contract', 'version')}",
        )
    )

    payload_hashes = payload.get("transcript_hashes") or {}
    runs = result.get("runs") or []
    run_ids = [str(_get(run, "run", "id")) for run in runs]
    problems: list[str] = []
    for run in runs:
        run_id = str(_get(run, "run", "id"))
        expected = payload_hashes.get(run_id)
        data = transcript_files.get(run_id)
        if data is None:
            problems.append(f"run {run_id}: transcript file missing")
            continue
        actual = sha256_hex(data)
        if actual != expected:
            problems.append(
                f"run {run_id}: transcript hash {actual} differs from signed {expected}"
            )
        if _get(run, "document_hash") != actual:
            problems.append(f"run {run_id}: result document records {_get(run, 'document_hash')}")
    missing_in_result = sorted(set(payload_hashes) - set(run_ids))
    if missing_in_result:
        problems.append(f"signed runs absent from the result: {', '.join(missing_in_result)}")
    checks.append(
        VerificationCheck(
            "transcript hashes",
            not problems,
            "; ".join(problems)
            if problems
            else f"{len(runs)} transcript(s) match the signed hashes",
        )
    )

    decisions = result.get("decisions") or []
    first = decisions[0] if decisions else None
    recorded_decision = (
        {"outcome": first.get("outcome"), "policy_version": first.get("policy_version")}
        if isinstance(first, dict)
        else None
    )
    checks.append(
        VerificationCheck(
            "decision",
            payload.get("decision") == recorded_decision,
            f"signed {payload.get('decision')}; recorded {recorded_decision}",
        )
    )

    counts: Counter[tuple[str, str]] = Counter()
    for run in runs:
        counts[(str(_get(run, "run", "test_case_id")), str(_get(run, "run", "verdict")))] += 1
    mismatched: list[str] = []
    for entry in payload.get("results") or []:
        tc = str(entry.get("test_case_id"))
        for verdict in ("pass", "fail", "inconclusive"):
            if entry.get(verdict) != counts[(tc, verdict)]:
                mismatched.append(
                    f"test case {tc}: signed {verdict}={entry.get(verdict)}, "
                    f"runs show {counts[(tc, verdict)]}"
                )
    checks.append(
        VerificationCheck(
            "aggregated results",
            not mismatched,
            "; ".join(mismatched) if mismatched else "the signed counts match the recorded runs",
        )
    )
    return VerificationResult(checks)
