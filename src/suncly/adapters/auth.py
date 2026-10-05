"""Token verifiers (``ports/identity.py``).

``OidcTokenVerifier`` validates a bearer token from an OpenID Connect
provider: the signature against the provider's published JWKS, the issuer,
the audience, the expiry and the not-before claim. ``LocalTokenVerifier``
validates HS256 tokens signed with a local secret; it exists for tests and
local development and refuses to be constructed for a production
environment, in addition to ``AppConfig`` refusing the setting.
"""

from __future__ import annotations

import time
from typing import Any

import jwt

from suncly.domain.errors import AuthenticationError, ConfigError
from suncly.domain.tenancy import Principal

LOCAL_ISSUER = "suncly-local"


def _principal(claims: dict[str, Any], issuer: str, verified_by: str) -> Principal:
    subject = str(claims.get("sub") or "").strip()
    if not subject:
        raise AuthenticationError("The token has no subject.", "The sub claim is missing.")
    email = claims.get("email")
    name = claims.get("name") or claims.get("preferred_username")
    return Principal(
        subject=subject,
        issuer=issuer,
        email=str(email) if email else None,
        display_name=str(name) if name else None,
        verified_by=verified_by,
    )


class OidcTokenVerifier:
    name = "oidc"

    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: str,
        algorithms: tuple[str, ...] = ("RS256", "ES256"),
        jwk_client: Any | None = None,
        leeway_seconds: int = 30,
    ) -> None:
        if not issuer or not audience or not jwks_url:
            raise ConfigError("The OIDC verifier needs an issuer, an audience and a JWKS URL.")
        self._issuer = issuer
        self._audience = audience
        self._algorithms = list(algorithms)
        self._leeway = leeway_seconds
        self._jwks = jwk_client or jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=300)

    def verify(self, token: str) -> Principal:
        try:
            key = self._jwks.get_signing_key_from_jwt(token).key
            claims = jwt.decode(
                token,
                key,
                algorithms=self._algorithms,
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("The token has expired.", "Sign in again.") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError(
                "The token could not be verified.", f"{type(exc).__name__}."
            ) from exc
        return _principal(claims, self._issuer, self.name)


class LocalTokenVerifier:
    """HS256 tokens for development and tests. Never constructible in production."""

    name = "local"

    def __init__(self, secret: str, environment: str, audience: str = "suncly-local") -> None:
        if environment == "production":
            raise ConfigError(
                "The local token verifier cannot run in production.",
                "SUNCLY_ENVIRONMENT is production.",
            )
        if len(secret) < 16:
            raise ConfigError("The local auth secret must be at least 16 characters.")
        self._secret = secret
        self._audience = audience

    def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=["HS256"],
                audience=self._audience,
                issuer=LOCAL_ISSUER,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("The token has expired.") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError(
                "The local token could not be verified.", f"{type(exc).__name__}."
            ) from exc
        return _principal(claims, LOCAL_ISSUER, self.name)


def issue_local_token(
    secret: str,
    subject: str,
    email: str | None = None,
    name: str | None = None,
    ttl_seconds: int = 3600,
    audience: str = "suncly-local",
) -> str:
    """A development token the local verifier accepts."""
    now = int(time.time())
    claims: dict[str, Any] = {
        "iss": LOCAL_ISSUER,
        "aud": audience,
        "sub": subject,
        "iat": now,
        "exp": now + ttl_seconds,
    }
    if email:
        claims["email"] = email
    if name:
        claims["name"] = name
    return jwt.encode(claims, secret, algorithm="HS256")
