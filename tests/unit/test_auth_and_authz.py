"""Token verification (OIDC and local) and role-based authorization per organization."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from suncly.adapters.auth import (
    LOCAL_ISSUER,
    LocalTokenVerifier,
    OidcTokenVerifier,
    issue_local_token,
)
from suncly.core.app_config import AppConfig, AuthConfig
from suncly.core.authz import ADMINISTRATOR_PERMISSIONS, REVIEWER_PERMISSIONS, VIEWER_PERMISSIONS
from suncly.domain.errors import AuthenticationError, AuthorizationError, ConfigError, NotFoundError
from suncly.domain.tenancy import DeploymentMode, Role
from tests.hosted import build_world

ISSUER = "https://issuer.example.test/"
AUDIENCE = "suncly-api"


class _Key:
    def __init__(self, kid: str) -> None:
        self.kid = kid
        self.private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.key = self.private.public_key()

    def pem(self) -> bytes:
        return self.private.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )


class _Jwks:
    """Stands in for ``jwt.PyJWKClient``: knows the keys the issuer published."""

    def __init__(self, keys: list[_Key]) -> None:
        self._keys = {k.kid: k for k in keys}

    def get_signing_key_from_jwt(self, token: str) -> Any:
        kid = jwt.get_unverified_header(token).get("kid")
        if kid not in self._keys:
            raise jwt.PyJWKClientError(f"unknown kid {kid}")
        return self._keys[kid]


def oidc_token(key: _Key, **overrides: Any) -> str:
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-1",
        "email": "alice@example.test",
        "name": "Alice",
        "iat": now,
        "exp": now + 600,
    }
    claims.update(overrides)
    for name in [k for k, v in claims.items() if v is None]:
        del claims[name]
    return jwt.encode(claims, key.pem(), algorithm="RS256", headers={"kid": key.kid})


def test_oidc_tokens_are_verified_against_the_published_keys() -> None:
    key = _Key("k1")
    verifier = OidcTokenVerifier(
        ISSUER, AUDIENCE, "https://issuer.example.test/jwks", jwk_client=_Jwks([key])
    )
    principal = verifier.verify(oidc_token(key))
    assert principal.subject == "user-1" and principal.issuer == ISSUER
    assert principal.email == "alice@example.test" and principal.verified_by == "oidc"
    assert principal.reviewer_id == "alice@example.test"


@pytest.mark.parametrize(
    ("overrides", "why"),
    [
        ({"aud": "another-api"}, "audience"),
        ({"iss": "https://evil.example.test/"}, "issuer"),
        ({"exp": int(time.time()) - 120}, "expired"),
        ({"sub": None}, "subject"),
        ({"iat": None}, "iat"),
        ({"aud": None}, "audience"),
    ],
)
def test_oidc_tokens_failing_any_claim_check_are_refused(
    overrides: dict[str, Any], why: str
) -> None:
    key = _Key("k1")
    verifier = OidcTokenVerifier(ISSUER, AUDIENCE, "https://x/jwks", jwk_client=_Jwks([key]))
    with pytest.raises(AuthenticationError):
        verifier.verify(oidc_token(key, **overrides))


def test_oidc_tokens_signed_by_an_unknown_key_or_unsigned_are_refused() -> None:
    published, rogue = _Key("k1"), _Key("k1")  # same kid, different key material
    verifier = OidcTokenVerifier(ISSUER, AUDIENCE, "https://x/jwks", jwk_client=_Jwks([published]))
    with pytest.raises(AuthenticationError):
        verifier.verify(oidc_token(rogue))
    other_kid = _Key("k2")
    with pytest.raises(AuthenticationError):
        verifier.verify(oidc_token(other_kid))
    unsigned = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "sub": "x", "iat": 1, "exp": 2**31},
        "",
        algorithm="none",
        headers={"kid": "k1"},
    )
    with pytest.raises(AuthenticationError):
        verifier.verify(unsigned)
    with pytest.raises(AuthenticationError):
        verifier.verify("not.a.token")
    with pytest.raises(ConfigError):
        OidcTokenVerifier("", AUDIENCE, "https://x/jwks")


def test_local_tokens_work_outside_production_only() -> None:
    secret = "a-local-secret-of-sufficient-length"
    verifier = LocalTokenVerifier(secret, "development")
    principal = verifier.verify(issue_local_token(secret, "dev-1", "dev@example.test"))
    assert principal.issuer == LOCAL_ISSUER and principal.verified_by == "local"
    with pytest.raises(AuthenticationError, match="expired"):
        verifier.verify(issue_local_token(secret, "dev-1", ttl_seconds=-10))
    with pytest.raises(AuthenticationError):
        verifier.verify(issue_local_token("another-secret-of-sufficient-length", "dev-1"))
    with pytest.raises(AuthenticationError):
        verifier.verify(issue_local_token(secret, "dev-1", audience="other"))
    with pytest.raises(ConfigError, match="production"):
        LocalTokenVerifier(secret, "production")
    with pytest.raises(ConfigError, match="16 characters"):
        LocalTokenVerifier("short", "development")
    with pytest.raises(ConfigError, match="cannot be enabled in production"):
        AppConfig(
            environment="production",
            auth=AuthConfig(
                local_auth_enabled=True, issuer=ISSUER, audience=AUDIENCE, jwks_url="https://x/jwks"
            ),
        )
    with pytest.raises(ConfigError, match="identity provider"):
        AppConfig(environment="production")
    with pytest.raises(ConfigError, match="local network mode"):
        AppConfig(
            environment="production",
            network_mode=DeploymentMode.LOCAL,
            auth=AuthConfig(issuer=ISSUER, audience=AUDIENCE, jwks_url="https://x/jwks"),
        )


def test_roles_nest_and_non_members_cannot_tell_an_organization_exists(tmp_path: Path) -> None:
    assert VIEWER_PERMISSIONS < REVIEWER_PERMISSIONS < ADMINISTRATOR_PERMISSIONS
    world = build_world(tmp_path)
    acme = world.organization(
        "acme", {"admin": Role.ADMINISTRATOR, "rev": Role.REVIEWER, "view": Role.VIEWER}
    )
    other = world.organization("other", {"stranger": Role.ADMINISTRATOR})
    authorizer = world.services.authorizer

    ctx = authorizer.require(world.principal("rev"), acme.id, "attestations:start")
    assert ctx.organization_id == acme.id and ctx.reviewer_id == "rev@example.test"
    assert ctx.can("contracts:approve") and not ctx.can("policy:write")

    with pytest.raises(AuthorizationError, match="not allowed for your role"):
        authorizer.require(world.principal("view"), acme.id, "agents:write")
    with pytest.raises(AuthorizationError, match="not allowed for your role"):
        authorizer.require(world.principal("rev"), acme.id, "members:manage")
    authorizer.require(world.principal("admin"), acme.id, "members:manage")

    # A stranger (member elsewhere) and a nobody both get "not found", never "forbidden".
    with pytest.raises(NotFoundError):
        authorizer.require(world.principal("stranger"), acme.id, "agents:read")
    with pytest.raises(NotFoundError):
        authorizer.require(world.principal("nobody"), other.id, "agents:read")
    with pytest.raises(NotFoundError):
        authorizer.require(world.principal("admin"), world.ids.new_id(), "agents:read")
    with pytest.raises(AuthorizationError, match="Unknown permission"):
        authorizer.require(world.principal("admin"), acme.id, "root:everything")
