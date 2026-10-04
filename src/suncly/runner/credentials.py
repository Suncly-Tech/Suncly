"""The only module that reads the credential for the agent under test (DR-003, OQ-P4).

Credentials come from the environment, never from command-line arguments,
files in the repository or the run job. A test asserts that no other module
names the variable.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

#: The full value of the HTTP ``Authorization`` header, for example ``Bearer <token>``.
CREDENTIAL_ENV_VAR = "SUNCLY_AGENT_AUTHORIZATION"

#: Secrets shorter than this are not treated as redaction targets on their own, so that
#: a short scheme word such as ``Basic`` does not blank out ordinary text.
MIN_SECRET_LENGTH = 6


@dataclass(frozen=True, repr=False)
class Credentials:
    authorization: str | None

    def __repr__(self) -> str:  # never leak the value, not even in debugging output
        return f"Credentials(authorization={'<set>' if self.authorization else None})"

    def headers(self) -> dict[str, str]:
        return {"Authorization": self.authorization} if self.authorization else {}

    def secrets(self) -> list[str]:
        """Every string form of the credential that must never appear in a transcript."""
        if not self.authorization:
            return []
        values = {self.authorization}
        parts = self.authorization.split(None, 1)
        if len(parts) == 2 and len(parts[1]) >= MIN_SECRET_LENGTH:
            values.add(parts[1])
        return sorted(values, key=len, reverse=True)


def read_credentials(env: Mapping[str, str]) -> Credentials:
    value = env.get(CREDENTIAL_ENV_VAR, "").strip()
    return Credentials(authorization=value or None)
