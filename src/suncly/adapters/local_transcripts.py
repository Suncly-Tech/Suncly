"""Transcript storage on the local disk: the object storage of schema §7, for now."""

from __future__ import annotations

from pathlib import Path

from suncly.domain.errors import StoreError


class LocalTranscriptStorage:
    """Write-once files under one root. ``transcript_ref`` is the key, relative to the root."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if self._root.resolve() not in path.parents:
            raise StoreError(f"The transcript key {key!r} leaves the storage root.")
        return path

    def put(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError as exc:
            raise StoreError(
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
