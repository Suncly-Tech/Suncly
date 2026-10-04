"""Progress events, so the CLI can show live progress without owning any logic."""

from __future__ import annotations

from typing import Any, Protocol


class ProgressListener(Protocol):
    def on_event(self, event: str, **details: Any) -> None: ...


class NoProgress:
    """Listener that ignores everything."""

    def on_event(self, event: str, **details: Any) -> None:
        return None
