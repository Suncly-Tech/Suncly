"""Signing keys that live in Secret Manager or in the environment, never on a Cloud Run disk."""

from __future__ import annotations

import pytest

from suncly.adapters.secret_keys import (
    EnvSigningKeys,
    SecretManagerSigningKeys,
    generate_pem,
)
from suncly.core.signing import key_id_for
from suncly.domain.errors import SigningError


def test_environment_keys_sign_but_never_rotate() -> None:
    pem, generated = generate_pem()
    keys = EnvSigningKeys({"SUNCLY_SIGNING_KEY": pem.decode("utf-8")})
    signer = keys.current()
    assert signer is not None and signer.key_id == generated.key_id
    assert signer.key_id == key_id_for(signer.public_key)
    assert keys.public_key_for(signer.key_id) == signer.public_key
    assert keys.public_key_for("ed25519-unknown") is None
    assert len(signer.sign(b"payload")) == 64
    with pytest.raises(SigningError, match="cannot create"):
        keys.create()
    assert EnvSigningKeys({}).current() is None
    with pytest.raises(SigningError, match="cannot be loaded"):
        EnvSigningKeys({"SUNCLY_SIGNING_KEY": "not a key"}).current()
    assert "payload" not in repr(signer) and "PRIVATE" not in repr(signer)


def test_secret_manager_keys_rotate_by_adding_a_version() -> None:
    versions: list[bytes] = []

    def read_latest(name: str) -> bytes | None:
        assert name == "projects/p/secrets/suncly-signing-key"
        return versions[-1] if versions else None

    def add_version(name: str, pem: bytes) -> None:
        versions.append(pem)

    keys = SecretManagerSigningKeys(
        "projects/p/secrets/suncly-signing-key", read_latest, add_version
    )
    assert keys.current() is None
    first = keys.create()
    assert len(versions) == 1 and keys.current().key_id == first.key_id  # type: ignore[union-attr]
    second = keys.create()
    assert second.key_id != first.key_id and keys.current().key_id == second.key_id  # type: ignore[union-attr]
    assert keys.public_key_for(first.key_id) == first.public_key, "an older key stays verifiable"
    assert keys.public_key_for(second.key_id) == second.public_key
    assert b"PRIVATE KEY" in versions[-1] and versions[0] != versions[1]
    fresh = SecretManagerSigningKeys(
        "projects/p/secrets/suncly-signing-key", read_latest, add_version
    )
    assert fresh.public_key_for(second.key_id) == second.public_key
    assert fresh.public_key_for(first.key_id) is None, (
        "a new process knows only the versions it loaded"
    )
