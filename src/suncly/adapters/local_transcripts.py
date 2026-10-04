"""Transcript storage on the local disk: the object storage of schema §7, for now."""

from __future__ import annotations

import re
from pathlib import Path

from suncly.domain.errors import StoreError, TranscriptExistsError

#: A key is a relative POSIX path of safe segments, such as ``<attestation>/<test_case>-1.json``.
#: Keys are validated lexically and never resolved against the file system: on Windows,
#: resolving a not-yet-existing path while another thread creates its folder can yield a
#: wrong path, which must never decide where evidence is written.
KEY_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def validate_key(key: str) -> list[str]:
    """The segments of a valid key. Raises ``StoreError`` for anything that could leave the root."""
    segments = key.split("/")
    if not key or any(
        not KEY_SEGMENT.match(segment) or segment in (".", "..") for segment in segments
    ):
        raise StoreError(f"The transcript key {key!r} is not a relative path of safe segments.")
    return segments


class LocalTranscriptStorage:
    """Write-once files under one root. ``transcript_ref`` is the key, relative to the root."""

    def __init__(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        self._root = root.resolve()

    def _path(self, key: str) -> Path:
        return self._root.joinpath(*validate_key(key))

    def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError as exc:
            raise TranscriptExistsError(
                "A transcript with this key already exists.",
                f"{key} was written before; evidence is never overwritten (DR-002).",
            ) from exc
        path.chmod(0o444)
        return key

    def get(self, transcript_ref: str) -> bytes:
        path = self._path(transcript_ref)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise StoreError(
                "A transcript is missing from storage.",
                f"{transcript_ref} does not exist under {self._root}.",
            ) from exc

    def exists(self, transcript_ref: str) -> bool:
        return self._path(transcript_ref).is_file()
