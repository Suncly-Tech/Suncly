"""Fetching an Agent Card from its URL (schema §4, step 2)."""

from __future__ import annotations

from typing import Protocol

from pydantic import AwareDatetime, BaseModel, ConfigDict


class FetchedCard(BaseModel):
    """The card text exactly as fetched, and when."""

    model_config = ConfigDict(frozen=True)

    url: str
    raw_json: str
    fetched_at: AwareDatetime


class CardFetcher(Protocol):
    """Fetches the card at ``url``. Raises ``CardFetchError`` on any failure."""

    def fetch(self, url: str) -> FetchedCard: ...
