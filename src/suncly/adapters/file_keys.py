"""Deployment signing keys on disk (schema §7: asymmetric signatures).

Ed25519 keys live under ``<home>/keys``, outside the repository, with the
private key readable only by the owner. The private key is never logged,
printed or returned; ``Signer.sign`` is the only operation that uses it.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from suncly.core.signing import key_id_for
from suncly.domain.errors import SigningError

PRIVATE_SUFFIX = ".key.pem"
PUBLIC_SUFFIX = ".pub"
CURRENT_FILE = "current"


class Ed25519FileSigner:
    def __init__(self, key_id: str, private_key: ed25519.Ed25519PrivateKey) -> None:
        self._key_id = key_id
        self._private_key = private_key
        self._public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )

    @property
    def key_id(self) -> str:
        return self._key_id

    @property
    def public_key(self) -> bytes:
        return self._public_key

    def sign(self, payload: bytes) -> bytes:
        return self._private_key.sign(payload)

    def __repr__(self) -> str:
        return f"Ed25519FileSigner(key_id={self._key_id!r})"


class FileSigningKeys:
    def __init__(self, keys_dir: Path) -> None:
        self._dir = keys_dir

    def current(self) -> Ed25519FileSigner | None:
        pointer = self._dir / CURRENT_FILE
        if not pointer.is_file():
            return None
        key_id = pointer.read_text(encoding="utf-8").strip()
        if not key_id:
            return None
        return self._load(key_id)

    def create(self) -> Ed25519FileSigner:
        self._dir.mkdir(parents=True, exist_ok=True)
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        key_id = key_id_for(public_bytes)
        private_path = self._dir / f"{key_id}{PRIVATE_SUFFIX}"
        pem = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(private_path, flags, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(pem)
        private_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        (self._dir / f"{key_id}{PUBLIC_SUFFIX}").write_bytes(public_bytes)
        (self._dir / CURRENT_FILE).write_text(key_id + "\n", encoding="utf-8")
        return Ed25519FileSigner(key_id, private_key)

    def public_key_for(self, key_id: str) -> bytes | None:
        path = self._dir / f"{key_id}{PUBLIC_SUFFIX}"
        return path.read_bytes() if path.is_file() else None

    def _load(self, key_id: str) -> Ed25519FileSigner:
        path = self._dir / f"{key_id}{PRIVATE_SUFFIX}"
        try:
            loaded = serialization.load_pem_private_key(path.read_bytes(), password=None)
        except (OSError, ValueError) as exc:
            raise SigningError(
                "The deployment key cannot be loaded.",
                f"{path} is missing or not a readable Ed25519 key.",
                "Create a new key with `suncly keys init`.",
            ) from exc
        if not isinstance(loaded, ed25519.Ed25519PrivateKey):
            raise SigningError(
                "The deployment key is not an Ed25519 key.",
                f"{path} holds a {type(loaded).__name__}.",
                "Create a new key with `suncly keys init`.",
            )
        return Ed25519FileSigner(key_id, loaded)
