"""Signing keys of the Suncly deployment (schema §7, §11)."""

from __future__ import annotations

from typing import Protocol


class Signer(Protocol):
    """A loaded deployment key. The private key never leaves the adapter."""

    @property
    def key_id(self) -> str:
        """``attestation.signing_key_id`` for signatures made with this key."""
        ...

    @property
    def public_key(self) -> bytes:
        """The raw public key, for verifiers."""
        ...

    def sign(self, payload: bytes) -> bytes: ...


class SigningKeys(Protocol):
    """Where a deployment keeps its keys."""

    def current(self) -> Signer | None:
        """The key to sign with, or ``None`` when no key exists yet."""
        ...

    def create(self) -> Signer:
        """Create a new key and make it current."""
        ...

    def public_key_for(self, key_id: str) -> bytes | None:
        """The public key with ``key_id`` if this deployment holds it."""
        ...
