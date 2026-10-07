"""The only module that names the customer's model key variable (OQ-A1, decided 2026-10-07).

The key comes from the environment of the judge subprocess, never from the
configuration, a command-line argument, a file in the repository or the
judge job. A test asserts that no other source module names the variable.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

#: The customer's model key, read only inside the judge subprocess.
JUDGE_KEY_ENV_VAR = "SUNCLY_JUDGE_MODEL_KEY"

#: What the key is replaced with wherever it would otherwise appear.
REDACTED = "[REDACTED]"


@dataclass(frozen=True, repr=False)
class ModelKey:
    value: str | None

    def __repr__(self) -> str:  # never leak the value, not even in debugging output
        return f"ModelKey({'<set>' if self.value else None})"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.value}"} if self.value else {}

    def redact(self, text: str) -> str:
        """``text`` with every occurrence of the key replaced."""
        if not self.value:
            return text
        return text.replace(self.value, REDACTED)


def read_key(env: Mapping[str, str]) -> ModelKey:
    value = env.get(JUDGE_KEY_ENV_VAR, "").strip()
    return ModelKey(value=value or None)
