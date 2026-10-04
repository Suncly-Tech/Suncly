"""Redaction inside the Runner (DR-003, schema §8).

What counts as a secret is open (OQ-A3). This is the stage 1 proposal: the
credential the Runner was given, sensitive headers, and a small documented list
of token patterns. Redaction runs over the whole transcript as data, so a
secret echoed back by the agent is removed as well.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Iterable
from typing import Any

from suncly.domain.transcript import RedactionSummary, Transcript

REDACTED = "[REDACTED]"

#: Header names whose values are always removed, wherever they appear as keys.
SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "x-api-key",
        "api-key",
        "apikey",
        "x-auth-token",
        "x-amz-security-token",
    }
)

#: Documented token patterns (OQ-A3). The whole match is replaced.
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]{6,}=*")),
    ("basic_credentials", re.compile(r"(?i)\bbasic\s+[A-Za-z0-9+/]{6,}=*")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    ("openai_style_key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "private_key_block",
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    ),
)

#: ``key=value`` and ``key: value`` forms; only the value is replaced.
KEY_VALUE_PATTERN = re.compile(
    r"""(?i)\b(api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|passwd)"""
    r"""(\s*[:=]\s*)(["']?)([^\s"',;&]{6,})"""
)


class Redactor:
    """Removes the given secrets, sensitive keys and known token patterns from any value."""

    def __init__(self, secrets: Iterable[str] = ()) -> None:
        literal = {s for s in secrets if s}
        literal |= {urllib.parse.quote(s, safe="") for s in list(literal)}
        self._secrets = sorted(literal, key=len, reverse=True)
        self.replacements = 0
        self.rules_used: set[str] = set()

    def redact_text(self, text: str) -> str:
        for secret in self._secrets:
            if secret in text:
                self.replacements += text.count(secret)
                self.rules_used.add("credential")
                text = text.replace(secret, REDACTED)
        for name, pattern in PATTERNS:
            text, count = pattern.subn(REDACTED, text)
            if count:
                self.replacements += count
                self.rules_used.add(name)

        def keep_key(match: re.Match[str]) -> str:
            self.replacements += 1
            self.rules_used.add("key_value")
            return f"{match.group(1)}{match.group(2)}{match.group(3)}{REDACTED}"

        return KEY_VALUE_PATTERN.sub(keep_key, text)

    def redact(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.redact_text(value)
        if isinstance(value, dict):
            result: dict[Any, Any] = {}
            for key, item in value.items():
                if isinstance(key, str) and key.lower() in SENSITIVE_KEYS:
                    if item not in (None, "", REDACTED):
                        self.replacements += 1
                        self.rules_used.add("sensitive_key")
                    result[key] = REDACTED if item not in (None, "") else item
                else:
                    result[key] = self.redact(item)
            return result
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        if isinstance(value, tuple):
            return [self.redact(item) for item in value]
        return value

    def summary(self) -> RedactionSummary:
        return RedactionSummary(replacements=self.replacements, rules=sorted(self.rules_used))


def redact_transcript(transcript: Transcript, redactor: Redactor) -> Transcript:
    """The transcript with every string field redacted and the summary filled in.

    Raises on any failure; the caller then withholds the transcript (OQ-A11).
    """
    data = transcript.model_dump(mode="json")
    redacted = redactor.redact(data)
    redacted["redaction"] = redactor.summary().model_dump(mode="json")
    return Transcript.model_validate(redacted)
