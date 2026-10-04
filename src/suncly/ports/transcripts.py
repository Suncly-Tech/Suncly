"""Transcript storage: the object storage of schema §7, behind a small interface."""

from __future__ import annotations

from typing import Protocol


class TranscriptStorage(Protocol):
    """Write-once storage addressed by ``run.transcript_ref``."""

    def put(self, key: str, data: bytes) -> str:
        """Store ``data`` under ``key`` and return the ``transcript_ref`` to record.

        Writing an existing key again is refused (evidence is immutable, DR-002).
        """
        ...

    def get(self, transcript_ref: str) -> bytes: ...

    def exists(self, transcript_ref: str) -> bool: ...
