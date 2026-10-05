"""Network destination policy: which URLs and addresses the Runner may contact.

Pure classification. The transports (``runner/http_transport.py`` and the
card fetcher) call ``check_url`` before a request and ``check_addresses`` on
every resolved address at connection time, so a hostname that resolves to a
private address later (DNS rebinding) is refused when the socket is opened,
not only when the URL was parsed.

This is application-level filtering. It is not network isolation: the hosted
deployment adds egress controls outside the process (deploy/README.md).
"""

from __future__ import annotations

import ipaddress
from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from suncly.domain.errors import TargetHostRefusedError
from suncly.domain.tenancy import DeploymentMode

#: Hostnames that always mean a cloud metadata service or the local machine.
BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata",
        "metadata.google.internal",
        "metadata.internal",
        "instance-data",
        "ip6-localhost",
        "ip6-loopback",
    }
)
LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})

#: Address ranges that are never a public agent endpoint.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "172.16.0.0/12",
        "192.0.0.0/24",
        "192.0.2.0/24",
        "192.168.0.0/16",
        "198.18.0.0/15",
        "198.51.100.0/24",
        "203.0.113.0/24",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "255.255.255.255/32",
        "::/128",
        "::1/128",
        "::ffff:0:0/96",
        "64:ff9b::/96",
        "fc00::/7",
        "fe80::/10",
        "fd00:ec2::254/128",
        "ff00::/8",
        "2001:db8::/32",
    )
]


@dataclass(frozen=True)
class NetworkPolicy:
    """What one deployment mode allows."""

    mode: DeploymentMode
    allowed_ports: frozenset[int] = field(default_factory=lambda: frozenset({443}))
    max_redirects: int = 3
    max_response_bytes: int = 4_000_000

    @classmethod
    def for_mode(cls, mode: DeploymentMode, extra_ports: Iterable[int] = ()) -> NetworkPolicy:
        if mode is DeploymentMode.PUBLIC:
            return cls(mode, frozenset({443, 8443, *extra_ports}))
        if mode is DeploymentMode.PRIVATE_NETWORK:
            return cls(mode, frozenset({80, 443, 8080, 8443, *extra_ports}))
        return cls(mode, frozenset())  # local: any port

    @property
    def allows_plain_http(self) -> bool:
        return self.mode is not DeploymentMode.PUBLIC

    @property
    def allows_private_addresses(self) -> bool:
        return self.mode is DeploymentMode.PRIVATE_NETWORK

    @property
    def allows_loopback(self) -> bool:
        return self.mode is DeploymentMode.LOCAL


def is_loopback_host(host: str | None) -> bool:
    if not host:
        return False
    if host in LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def address_block_reason(address: str) -> str | None:
    """Why an IP address is not a public destination, or ``None`` when it is."""
    try:
        parsed = ipaddress.ip_address(address.strip("[]"))
    except ValueError:
        return "not an IP address"
    if parsed.version == 6 and parsed.ipv4_mapped is not None:
        parsed = parsed.ipv4_mapped
    if parsed.is_unspecified:
        return "reserved"
    if parsed.is_loopback:
        return "loopback"
    if parsed.is_link_local:
        return "link-local (cloud metadata range)"
    if parsed.is_private:
        return "private"
    if parsed.is_multicast:
        return "multicast"
    if parsed.is_reserved or parsed.is_unspecified:
        return "reserved"
    for network in _BLOCKED_NETWORKS:
        if parsed in network:
            return f"in blocked range {network}"
    return None


def check_url(url: str, policy: NetworkPolicy, what: str = "URL") -> None:
    """Refuse a URL whose scheme, port or literal host the policy forbids."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme not in ("http", "https") or not host:
        raise TargetHostRefusedError(
            f"The {what} must use https.",
            f"{url!r} has scheme {parts.scheme or 'none'}" + ("" if host else " and no host") + ".",
            "Use an https URL.",
        )
    if parts.username or parts.password:
        raise TargetHostRefusedError(
            f"The {what} must not carry credentials.", "Userinfo in URLs is refused."
        )
    if parts.scheme == "http":
        if policy.mode is DeploymentMode.PUBLIC:
            raise TargetHostRefusedError(
                f"The {what} must use https.",
                f"{url} uses plain http; the hosted Runner only contacts https endpoints.",
                "Use an https URL.",
            )
        if policy.mode is DeploymentMode.LOCAL and not is_loopback_host(host):
            raise TargetHostRefusedError(
                f"The {what} must use https.",
                f"{url} uses plain http; in local mode plain http is allowed only for loopback "
                "addresses such as 127.0.0.1.",
                "Use an https URL, or run the sandbox on this machine.",
            )
    port = parts.port or (443 if parts.scheme == "https" else 80)
    if policy.allowed_ports and port not in policy.allowed_ports:
        raise TargetHostRefusedError(
            f"The {what} uses a port the deployment does not allow.",
            f"Port {port} is not in {sorted(policy.allowed_ports)}.",
        )
    if host in BLOCKED_HOSTNAMES and not (policy.allows_loopback and is_loopback_host(host)):
        raise TargetHostRefusedError(
            f"The {what} names a host that is never a public endpoint.", f"Host {host!r}."
        )
    literal = host.strip("[]")
    try:
        ipaddress.ip_address(literal)
    except ValueError:
        return
    reason = address_block_reason(literal)
    if reason is not None and not _address_allowed(reason, policy):
        raise TargetHostRefusedError(
            f"The {what} points at an address that is not a public endpoint.",
            f"{literal} is {reason}.",
        )


def _address_allowed(reason: str, policy: NetworkPolicy) -> bool:
    if policy.allows_loopback and reason == "loopback":
        return True
    return bool(policy.allows_private_addresses and reason in ("private", "loopback"))


def check_addresses(host: str, addresses: Iterable[str], policy: NetworkPolicy) -> None:
    """Refuse the connection unless every resolved address is allowed (rebinding defence)."""
    resolved = list(addresses)
    if not resolved:
        raise TargetHostRefusedError("The host did not resolve to any address.", f"Host {host!r}.")
    for address in resolved:
        reason = address_block_reason(address)
        if reason is not None and not _address_allowed(reason, policy):
            raise TargetHostRefusedError(
                "The Runner refused to connect to an address that is not a public endpoint.",
                f"{host} resolved to {address}, which is {reason}.",
                "Public hosted mode only reaches public addresses; private endpoints need the "
                "separately authorized private-network Runner.",
            )
