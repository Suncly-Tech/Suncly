"""Deployment signing keys that are not on a disk (Cloud Run has none that lasts).

``EnvSigningKeys`` loads the current Ed25519 private key from one environment
variable the platform fills from Secret Manager (``SUNCLY_SIGNING_KEY``, PEM).
It can sign and expose the public key; it cannot rotate, because a process
that only reads a secret must not be the one that writes it.

``SecretManagerSigningKeys`` is the writable variant for ``suncly trust
rotate``: ``current()`` reads the latest version of the secret and
``create()`` adds a new version. Both functions are injected so the adapter is
tested without Google credentials; the default accessors use the optional
``gcp`` extra. The private key never leaves these objects.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from suncly.adapters.file_keys import Ed25519FileSigner
from suncly.core.signing import key_id_for
from suncly.domain.errors import SigningError

SIGNING_KEY_ENV_VAR = "SUNCLY_SIGNING_KEY"


def _signer_from_pem(pem: bytes, where: str) -> Ed25519FileSigner:
    try:
        loaded = serialization.load_pem_private_key(pem, password=None)
    except (ValueError, TypeError) as exc:
        raise SigningError(
            "The deployment key cannot be loaded.",
            f"{where} does not hold a readable PEM private key.",
            "Add a PKCS8 PEM Ed25519 key as the secret's value.",
        ) from exc
    if not isinstance(loaded, ed25519.Ed25519PrivateKey):
        raise SigningError(
            "The deployment key is not an Ed25519 key.",
            f"{where} holds a {type(loaded).__name__}.",
        )
    public = loaded.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return Ed25519FileSigner(key_id_for(public), loaded)


def generate_pem() -> tuple[bytes, Ed25519FileSigner]:
    private = ed25519.Ed25519PrivateKey.generate()
    pem = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public = private.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    return pem, Ed25519FileSigner(key_id_for(public), private)


class EnvSigningKeys:
    """Read-only keys from the environment (filled by the platform from Secret Manager)."""

    def __init__(self, environment: Mapping[str, str], variable: str = SIGNING_KEY_ENV_VAR) -> None:
        self._env = environment
        self._variable = variable
        self._loaded: Ed25519FileSigner | None = None

    def current(self) -> Ed25519FileSigner | None:
        raw = self._env.get(self._variable, "").strip()
        if not raw:
            return None
        if self._loaded is None:
            self._loaded = _signer_from_pem(raw.encode("utf-8"), self._variable)
        return self._loaded

    def create(self) -> Ed25519FileSigner:
        raise SigningError(
            "This process cannot create a signing key.",
            f"Keys come from {self._variable}, which only reads Secret Manager.",
            "Rotate with `suncly trust rotate` in a process configured with "
            "SUNCLY_SIGNING_KEY_SECRET.",
        )

    def public_key_for(self, key_id: str) -> bytes | None:
        signer = self.current()
        return signer.public_key if signer and signer.key_id == key_id else None


ReadLatest = Callable[[str], bytes | None]
AddVersion = Callable[[str, bytes], None]


class SecretManagerSigningKeys:
    """Keys in one Secret Manager secret; every version is one key, the latest is current."""

    def __init__(
        self,
        secret_name: str,
        read_latest: ReadLatest | None = None,
        add_version: AddVersion | None = None,
    ) -> None:
        self._secret = secret_name
        self._read = read_latest or self._default_read
        self._add = add_version or self._default_add
        self._known: dict[str, bytes] = {}

    @staticmethod
    def _client() -> object:
        try:
            from google.cloud import secretmanager
        except ImportError as exc:  # pragma: no cover - needs the optional extra
            raise SigningError(
                "Secret Manager support is not installed.", "Install suncly[gcp]."
            ) from exc
        return secretmanager.SecretManagerServiceClient()

    def _default_read(self, secret_name: str) -> bytes | None:  # pragma: no cover - network
        client = self._client()
        try:
            response = client.access_secret_version(  # type: ignore[attr-defined]
                request={"name": f"{secret_name}/versions/latest"}
            )
        except Exception as exc:
            if "NOT_FOUND" in str(exc) or "not found" in str(exc).lower():
                return None
            raise SigningError("The signing key secret cannot be read.", f"{exc}") from exc
        return bytes(response.payload.data)

    def _default_add(self, secret_name: str, pem: bytes) -> None:  # pragma: no cover - network
        client = self._client()
        client.add_secret_version(  # type: ignore[attr-defined]
            request={"parent": secret_name, "payload": {"data": pem}}
        )

    def current(self) -> Ed25519FileSigner | None:
        pem = self._read(self._secret)
        if not pem or not pem.strip():
            return None
        signer = _signer_from_pem(pem, self._secret)
        self._known[signer.key_id] = signer.public_key
        return signer

    def create(self) -> Ed25519FileSigner:
        pem, signer = generate_pem()
        self._add(self._secret, pem)
        self._known[signer.key_id] = signer.public_key
        return signer

    def public_key_for(self, key_id: str) -> bytes | None:
        if key_id not in self._known:
            self.current()
        return self._known.get(key_id)
