"""Attestation integrity: the signed payload version 2 and its layered verification.

Payload version 2 binds everything a relying party needs to decide whether
to trust an attestation today: the card hash, the contract content hash and
version, the policy content hash and version, the suite, judge and rubric
versions, every evidence hash, the tested endpoint and environment, the
agent's deployment identity when it was independently available, the issue
and expiry times, the decision and the responsible reviewer. Version 1
payloads (``core/signing.py``) keep verifying unchanged.

Verification separates four questions that are often conflated:

1. cryptographic validity: does the signature match the payload under the key?
2. issuer trust: is the key one this deployment trusts, and was it unrevoked
   when the attestation was issued?
3. freshness: is the attestation within its validity window now?
4. policy acceptability: does the bound policy match the one in force, and
   does the decision approve?

A "yes" to the first never implies a "yes" to the others.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from suncly.core import signing
from suncly.domain.evidence import TestCaseResult
from suncly.domain.models import Attestation, Contract, Decision, JsonObject
from suncly.ports.app_store import SigningKeyRecord

PAYLOAD_VERSION_2 = 2
PAYLOAD_VERSIONS = (1, 2)


@dataclass(frozen=True)
class EnvironmentBinding:
    """The tested endpoint and the deployment mode it was reached in."""

    target_url: str
    deployment_mode: str
    sandbox_declared: bool
    protocol_binding: str
    protocol_version: str

    def to_json(self) -> JsonObject:
        return {
            "target_url": self.target_url,
            "deployment_mode": self.deployment_mode,
            "sandbox_declared": self.sandbox_declared,
            "protocol_binding": self.protocol_binding,
            "protocol_version": self.protocol_version,
        }


@dataclass(frozen=True)
class DeploymentIdentity:
    """What the remote agent independently told us about itself, when it did.

    Never fabricated: ``source`` names where each value came from (the card's
    ``version`` field, a response header, a TLS certificate). When nothing was
    available the payload carries ``null``.
    """

    agent_version: str | None
    source: str
    extra: JsonObject = field(default_factory=dict)

    def to_json(self) -> JsonObject:
        return {"agent_version": self.agent_version, "source": self.source, **self.extra}


def build_payload_v2(
    *,
    attestation: Attestation,
    card_hash: str,
    contract: Contract,
    contract_content_hash: str,
    suite_version: str,
    judge_version: str,
    rubric_versions: Mapping[str, str],
    policy_version: str | None,
    policy_content_hash: str | None,
    results: Sequence[TestCaseResult],
    transcript_hashes: Mapping[str, str],
    artifact_hashes: Mapping[str, str],
    environment: EnvironmentBinding,
    deployment_identity: DeploymentIdentity | None,
    issued_at: datetime,
    expires_at: datetime,
    decision: Decision | None,
    reviewer: str | None,
    issuer: str,
) -> JsonObject:
    """The signed payload, version 2. Order-independent like version 1."""
    return {
        "payload_version": PAYLOAD_VERSION_2,
        "issuer": issuer,
        "attestation_id": str(attestation.id),
        "card_hash": card_hash,
        "contract": {
            "id": str(contract.id),
            "version": contract.version,
            "content_hash": contract_content_hash,
        },
        "policy": None
        if policy_version is None
        else {"version": policy_version, "content_hash": policy_content_hash},
        "versions": {
            "suite": suite_version,
            "judge": judge_version,
            "rubrics": dict(sorted(rubric_versions.items())),
        },
        "results": [
            result.to_payload()
            for result in sorted(results, key=lambda result: str(result.test_case_id))
        ],
        "transcript_hashes": dict(sorted(transcript_hashes.items())),
        "artifact_hashes": dict(sorted(artifact_hashes.items())),
        "environment": environment.to_json(),
        "deployment_identity": None
        if deployment_identity is None
        else deployment_identity.to_json(),
        "issued_at": issued_at.isoformat(timespec="seconds"),
        "expires_at": expires_at.isoformat(timespec="seconds"),
        "decision": None
        if decision is None
        else {
            "outcome": decision.outcome.value,
            "policy_version": decision.policy_version,
            "decided_by": decision.decided_by,
            "reviewer": reviewer,
        },
    }


# -- layered verification --------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class TrustContext:
    """What the verifier knows besides the report: trusted keys, the time, the policy in force."""

    now: datetime
    trusted_keys: Mapping[str, SigningKeyRecord] = field(default_factory=dict)
    expected_issuer: str | None = None
    current_policy_hash: str | None = None
    require_human_for_high_risk: bool = True


@dataclass(frozen=True)
class LayeredVerification:
    cryptographic: list[Check]
    issuer_trust: list[Check]
    freshness: list[Check]
    policy: list[Check]

    @property
    def cryptographically_valid(self) -> bool:
        return all(c.ok for c in self.cryptographic)

    @property
    def issuer_trusted(self) -> bool:
        return all(c.ok for c in self.issuer_trust)

    @property
    def fresh(self) -> bool:
        return all(c.ok for c in self.freshness)

    @property
    def policy_acceptable(self) -> bool:
        return all(c.ok for c in self.policy)

    @property
    def accepted(self) -> bool:
        """Every layer passed. Only this means "approved under the current policy"."""
        return (
            self.cryptographically_valid
            and self.issuer_trusted
            and self.fresh
            and self.policy_acceptable
        )

    def to_json(self) -> JsonObject:
        def section(checks: list[Check]) -> JsonObject:
            return {
                "ok": all(c.ok for c in checks),
                "checks": [{"name": c.name, "ok": c.ok, "detail": c.detail} for c in checks],
            }

        return {
            "accepted": self.accepted,
            "cryptographic": section(self.cryptographic),
            "issuer_trust": section(self.issuer_trust),
            "freshness": section(self.freshness),
            "policy": section(self.policy),
        }


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


def verify_layers(
    result: JsonObject,
    transcript_files: Mapping[str, bytes],
    trust: TrustContext,
    public_key: bytes | None = None,
) -> LayeredVerification:
    """Run the four layers over a ``result.json`` document and its transcript files."""
    from suncly.core.verify import verify_result

    crypto = verify_result(result, transcript_files, public_key)
    cryptographic = [Check(c.name, c.ok, c.detail) for c in crypto.checks]
    payload = result.get("signature_payload") if isinstance(result, dict) else None
    payload = payload if isinstance(payload, dict) else {}
    attestation: JsonObject = (
        result["attestation"] if isinstance(result.get("attestation"), dict) else {}
    )
    key_id = attestation.get("signing_key_id")
    version = payload.get("payload_version")

    issuer_trust: list[Check] = []
    record = trust.trusted_keys.get(str(key_id)) if key_id else None
    issuer_trust.append(
        Check(
            "key is trusted",
            record is not None,
            f"key {key_id} is registered with issuer {record.issuer}"
            if record is not None
            else f"key {key_id} is not in the trusted-key registry",
        )
    )
    issued_at = _parse_time(payload.get("issued_at"))
    if record is not None:
        if trust.expected_issuer is not None:
            issuer_trust.append(
                Check(
                    "issuer matches",
                    record.issuer == trust.expected_issuer
                    and payload.get("issuer", record.issuer) == trust.expected_issuer,
                    f"expected {trust.expected_issuer}, key issuer {record.issuer}, "
                    f"payload issuer {payload.get('issuer')}",
                )
            )
        if record.revoked_at is not None:
            revoked_before_issue = issued_at is None or record.revoked_at <= issued_at
            issuer_trust.append(
                Check(
                    "key not revoked at issue time",
                    not revoked_before_issue,
                    f"revoked at {record.revoked_at.isoformat()} ({record.revocation_reason}); "
                    f"issued at {issued_at.isoformat() if issued_at else 'unknown'}",
                )
            )
        else:
            issuer_trust.append(Check("key not revoked", True, "no revocation recorded"))

    freshness: list[Check] = []
    if version == PAYLOAD_VERSION_2:
        expires_at = _parse_time(payload.get("expires_at"))
        freshness.append(
            Check(
                "issue time present and not in the future",
                issued_at is not None and issued_at <= trust.now,
                f"issued_at {payload.get('issued_at')}, now {trust.now.isoformat()}",
            )
        )
        freshness.append(
            Check(
                "not expired",
                expires_at is not None and trust.now < expires_at,
                f"expires_at {payload.get('expires_at')}, now {trust.now.isoformat()}",
            )
        )
    else:
        freshness.append(
            Check(
                "validity window",
                False,
                "payload version 1 carries no issue or expiry time; freshness cannot be shown",
            )
        )

    policy_checks: list[Check] = []
    decision = payload.get("decision")
    bound_policy = payload.get("policy") if version == PAYLOAD_VERSION_2 else None
    if trust.current_policy_hash is not None:
        bound_hash = bound_policy.get("content_hash") if isinstance(bound_policy, dict) else None
        policy_checks.append(
            Check(
                "bound policy is the policy in force",
                bound_hash == trust.current_policy_hash,
                f"payload policy {bound_hash}, current {trust.current_policy_hash}",
            )
        )
    decisions = result.get("decisions") if isinstance(result.get("decisions"), list) else []
    latest = decisions[-1] if decisions else None
    latest_outcome = latest.get("outcome") if isinstance(latest, dict) else None
    signed_outcome = decision.get("outcome") if isinstance(decision, dict) else None
    policy_checks.append(
        Check(
            "signed decision present",
            isinstance(decision, dict),
            f"signed decision {decision}",
        )
    )
    policy_checks.append(
        Check(
            "latest recorded decision approves",
            latest_outcome == "approve",
            f"latest decision {latest_outcome}; signed decision {signed_outcome}",
        )
    )
    return LayeredVerification(cryptographic, issuer_trust, freshness, policy_checks)


def payload_version_of(result: JsonObject) -> int | None:
    payload = result.get("signature_payload")
    if isinstance(payload, dict) and isinstance(payload.get("payload_version"), int):
        return int(payload["payload_version"])
    return None


def signature_matches(public_key: bytes, payload: JsonObject, signature: str) -> bool:
    return signing.verify_payload(public_key, payload, signature)
