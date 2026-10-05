"""Transcript storage on Google Cloud Storage (the object storage of schema §7).

Write-once is enforced by the bucket's precondition ``if_generation_match=0``:
a second write under an existing key fails at the bucket, not only in code.
The client is injectable so the adapter is tested without a bucket; the real
client is imported lazily (``suncly[gcp]``).
"""

from __future__ import annotations

from typing import Any, Protocol

from suncly.adapters.local_transcripts import validate_key
from suncly.domain.errors import StoreError, TranscriptExistsError


class Blob(Protocol):
    def upload_from_string(
        self, data: bytes, content_type: str, if_generation_match: int
    ) -> None: ...

    def download_as_bytes(self) -> bytes: ...

    def exists(self) -> bool: ...


class Bucket(Protocol):
    def blob(self, name: str) -> Blob: ...


class GcsTranscriptStorage:
    def __init__(self, bucket: Bucket, prefix: str = "evidence/") -> None:
        self._bucket = bucket
        self._prefix = prefix

    @classmethod
    def for_bucket(cls, bucket_name: str, prefix: str = "evidence/") -> GcsTranscriptStorage:
        try:
            from google.cloud import storage  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - needs the optional extra
            raise StoreError(
                "Cloud Storage support is not installed.", "Install suncly[gcp]."
            ) from exc
        client = storage.Client()
        return cls(client.bucket(bucket_name), prefix)

    def _name(self, key: str) -> str:
        return self._prefix + "/".join(validate_key(key))

    def put(self, key: str, data: bytes) -> str:
        blob = self._bucket.blob(self._name(key))
        try:
            blob.upload_from_string(data, content_type="application/json", if_generation_match=0)
        except Exception as exc:
            if _is_precondition_failure(exc):
                raise TranscriptExistsError(
                    "A transcript with this key already exists.",
                    f"{key} was written before; evidence is never overwritten (DR-002).",
                ) from exc
            raise StoreError(
                "The transcript could not be written.", f"{type(exc).__name__}."
            ) from exc
        return key

    def get(self, transcript_ref: str) -> bytes:
        blob = self._bucket.blob(self._name(transcript_ref))
        try:
            return blob.download_as_bytes()
        except Exception as exc:
            raise StoreError(
                "A transcript is missing from storage.", f"{transcript_ref}: {type(exc).__name__}."
            ) from exc

    def exists(self, transcript_ref: str) -> bool:
        return self._bucket.blob(self._name(transcript_ref)).exists()


def _is_precondition_failure(exc: Exception) -> bool:
    name = type(exc).__name__
    status = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    return name in ("PreconditionFailed", "ObjectExists") or status == 412


class MemoryBucket:
    """An in-memory bucket honouring ``if_generation_match=0``, for tests."""

    class _Exists(Exception):
        code = 412

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def blob(self, name: str) -> Any:
        bucket = self

        class _Blob:
            def upload_from_string(
                self, data: bytes, content_type: str, if_generation_match: int
            ) -> None:
                if if_generation_match == 0 and name in bucket.objects:
                    raise MemoryBucket._Exists(name)
                bucket.objects[name] = data

            def download_as_bytes(self) -> bytes:
                if name not in bucket.objects:
                    raise KeyError(name)
                return bucket.objects[name]

            def exists(self) -> bool:
                return name in bucket.objects

        return _Blob()
