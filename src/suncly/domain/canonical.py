"""Canonical JSON (RFC 8785, JCS) and hashing.

One canonicalization scheme serves both the Agent Card hash (OQ-A7, proposal)
and the attestation signature payload (schema §11, OQ-A8, proposal).
"""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785

#: Prefix that makes a hash string self-describing, e.g. ``sha256:3f2a…``.
SHA256_PREFIX = "sha256:"


def canonical_json(value: Any) -> bytes:
    """Serialize ``value`` with the JSON Canonicalization Scheme (RFC 8785)."""
    return rfc8785.dumps(value)


def sha256_hex(data: bytes) -> str:
    """Lowercase hex SHA-256 of ``data``, prefixed with ``sha256:``."""
    return SHA256_PREFIX + hashlib.sha256(data).hexdigest()


def canonical_sha256(value: Any) -> str:
    """``sha256_hex`` of the canonical JSON form of ``value``."""
    return sha256_hex(canonical_json(value))
