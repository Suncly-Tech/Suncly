"""Fetches an Agent Card with a timeout, a size limit and the network policy (schema §4).

Every URL, including every redirect target, is checked against the policy
before it is requested, and every resolved address is checked again at
connection time (``runner/http_transport.py``). Redirects are followed by
hand, at most a few times, never to a forbidden destination.
"""

from __future__ import annotations

from datetime import UTC, datetime

import httpx

from suncly.domain.errors import CardFetchError, TargetHostRefusedError
from suncly.domain.network import NetworkPolicy, check_url, is_loopback_host
from suncly.ports.card_fetcher import FetchedCard
from suncly.runner.http_transport import GuardedTransport, Resolver, default_policy, resolve_host

MAX_REDIRECTS = 3
WELL_KNOWN_HINT = "Check the URL; A2A cards are usually at /.well-known/agent-card.json."


class HttpxCardFetcher:
    def __init__(
        self,
        timeout_s: float,
        max_bytes: int,
        policy: NetworkPolicy | None = None,
        resolver: Resolver = resolve_host,
    ) -> None:
        self._timeout_s = timeout_s
        self._max_bytes = max_bytes
        self._policy = policy or default_policy()
        self._resolver = resolver

    def _client(self, url: str) -> httpx.Client:
        verify = not (self._policy.allows_loopback and is_loopback_host(httpx.URL(url).host))
        return httpx.Client(
            follow_redirects=False,
            timeout=self._timeout_s,
            transport=GuardedTransport(self._policy, self._resolver, verify=verify),
        )

    def fetch(self, url: str) -> FetchedCard:
        current = url
        try:
            check_url(current, self._policy, "card URL")
        except TargetHostRefusedError as exc:
            raise CardFetchError(exc.what, exc.why, exc.next_step) from exc
        with self._client(url) as client:
            for _ in range(self._policy.max_redirects + 1):
                try:
                    body, redirect = self._get(client, current)
                except httpx.TimeoutException as exc:
                    raise CardFetchError(
                        "Fetching the card timed out.",
                        f"{current} did not answer within {self._timeout_s} seconds.",
                        "Check that the agent is running and reachable from this machine.",
                    ) from exc
                except TargetHostRefusedError as exc:
                    raise CardFetchError(exc.what, exc.why, exc.next_step) from exc
                except httpx.HTTPError as exc:
                    raise CardFetchError(
                        "The card could not be fetched.",
                        f"{type(exc).__name__}: {exc}",
                        "Check the URL and the network; for a local sandbox, check it is running.",
                    ) from exc
                if redirect is not None:
                    current = redirect
                    continue
                try:
                    text = body.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise CardFetchError(
                        "The card is not UTF-8 text.",
                        f"Decoding the body of {current} failed at byte {exc.start}.",
                        "Serve the Agent Card as UTF-8 JSON.",
                    ) from exc
                return FetchedCard(url=url, raw_json=text, fetched_at=datetime.now(UTC))
        raise CardFetchError(
            "The card URL redirected too many times.",
            f"More than {self._policy.max_redirects} redirects starting from {url}.",
            "Use the final URL of the card directly.",
        )

    def _get(self, client: httpx.Client, url: str) -> tuple[bytes, str | None]:
        """``(body, None)`` for a card, ``(b"", target)`` for a redirect."""
        with client.stream("GET", url, headers={"Accept": "application/json"}) as response:
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    raise CardFetchError(
                        "The card URL redirected without a destination.",
                        f"{url} answered {response.status_code} with no Location header.",
                    )
                target = str(httpx.URL(url).join(location))
                try:
                    check_url(target, self._policy, "redirect target")
                except TargetHostRefusedError as exc:
                    raise CardFetchError(
                        "The card URL redirects to a URL that is not https or not allowed by "
                        "the policy.",
                        f"The redirect target is {target}: {exc.why}",
                        "Use the final https URL of the card directly.",
                    ) from exc
                return b"", target
            if response.status_code != 200:
                raise CardFetchError(
                    "The card URL did not return the card.",
                    f"{url} answered HTTP {response.status_code}.",
                    WELL_KNOWN_HINT,
                )
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > self._max_bytes:
                    raise CardFetchError(
                        "The card is larger than the size limit.",
                        f"More than {self._max_bytes} bytes were received from {url}.",
                        "Check that the URL serves the card and not a larger document, or "
                        "raise card_max_bytes in the configuration.",
                    )
            return bytes(body), None
