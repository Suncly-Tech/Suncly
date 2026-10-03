"""Time and identifiers as ports, so core logic is deterministic under test."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID


class Clock(Protocol):
    """Source of timezone-aware UTC timestamps."""

    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    """Source of entity ids."""

    def new_id(self) -> UUID: ...
