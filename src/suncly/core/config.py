"""One typed configuration object, built once.

Values are resolved in this order: built-in defaults, then the config file
(``SUNCLY_HOME/config.toml``), then environment variables. The object is
immutable and passed down explicitly; there is no global state. The two
credentials Suncly uses, the agent credential and the judge model key, are
not settings: each is read by its own subprocess and nowhere else.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from suncly.domain.errors import ConfigError

ENV_PREFIX = "SUNCLY_"

#: Repetitions per test case when ``--runs`` is not given (OQ-P5, proposal).
DEFAULT_RUNS = 5
#: Budget in attempts is ``DEFAULT_BUDGET_FACTOR`` x planned runs when not given (OQ-D1, OQ-P5).
DEFAULT_BUDGET_FACTOR = 2


@dataclass(frozen=True)
class Config:
    """Every setting Suncly reads. Field names are the TOML keys; env vars add ``SUNCLY_``."""

    home: Path
    database_url: str | None = None
    reports_dir: Path = Path("suncly-reports")
    runs: int = DEFAULT_RUNS
    budget_limit: Decimal | None = None
    run_timeout_s: float = 30.0
    latency_limit_ms: int = 10_000
    max_retries: int = 2
    concurrency: int = 4
    card_timeout_s: float = 10.0
    card_max_bytes: int = 1_000_000
    poll_interval_s: float = 0.5
    max_test_cases_per_skill: int = 3
    judge_model: str | None = None
    """The one pinned Layer 2 model id (DR-004). No default: without it Layer 2 does not run."""
    judge_endpoint: str | None = None
    """The one URL the judge subprocess may talk to. No default."""
    judge_rubric_version: str | None = None
    """The rubric frame version in use; must be the one this build carries (DR-004)."""
    judge_timeout_s: float = 60.0
    """Seconds one model question may take before it counts as a timeout (inconclusive)."""

    @property
    def store_dir(self) -> Path:
        return self.home / "store"

    @property
    def transcripts_dir(self) -> Path:
        return self.home / "transcripts"

    @property
    def keys_dir(self) -> Path:
        return self.home / "keys"

    @property
    def config_file(self) -> Path:
        return self.home / "config.toml"

    @property
    def uses_postgres(self) -> bool:
        return bool(self.database_url)

    def with_overrides(self, **values: Any) -> Config:
        """A copy with explicit (non-``None``) command-line values applied."""
        return replace(self, **{k: v for k, v in values.items() if v is not None})


def _positive_int(name: str) -> Callable[[str], int]:
    def parse(raw: str) -> int:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigError(
                f"The setting {name} is not a whole number.",
                f"Its value is {raw!r}.",
                f"Set {name} to a positive whole number.",
            ) from exc
        if value < 1:
            raise ConfigError(f"The setting {name} must be at least 1.", f"Its value is {value}.")
        return value

    return parse


def _non_negative_int(name: str) -> Callable[[str], int]:
    def parse(raw: str) -> int:
        try:
            value = int(raw)
        except ValueError as exc:
            raise ConfigError(
                f"The setting {name} is not a whole number.", f"Its value is {raw!r}."
            ) from exc
        if value < 0:
            raise ConfigError(f"The setting {name} cannot be negative.", f"Its value is {value}.")
        return value

    return parse


def _positive_float(name: str) -> Callable[[str], float]:
    def parse(raw: str) -> float:
        try:
            value = float(raw)
        except ValueError as exc:
            raise ConfigError(
                f"The setting {name} is not a number.", f"Its value is {raw!r}."
            ) from exc
        if value <= 0:
            raise ConfigError(
                f"The setting {name} must be greater than 0.", f"Its value is {value}."
            )
        return value

    return parse


def _decimal(name: str) -> Callable[[str], Decimal]:
    def parse(raw: str) -> Decimal:
        try:
            value = Decimal(raw)
        except InvalidOperation as exc:
            raise ConfigError(
                f"The setting {name} is not a number.", f"Its value is {raw!r}."
            ) from exc
        if value < 0:
            raise ConfigError(f"The setting {name} cannot be negative.", f"Its value is {value}.")
        return value

    return parse


def _path(raw: str) -> Path:
    return Path(raw).expanduser()


def _text(raw: str) -> str:
    return raw


#: Field name -> parser from the string form (environment variables and TOML strings).
PARSERS: dict[str, Callable[[str], Any]] = {
    "home": _path,
    "database_url": _text,
    "reports_dir": _path,
    "runs": _positive_int("runs"),
    "budget_limit": _decimal("budget_limit"),
    "run_timeout_s": _positive_float("run_timeout_s"),
    "latency_limit_ms": _positive_int("latency_limit_ms"),
    "max_retries": _non_negative_int("max_retries"),
    "concurrency": _positive_int("concurrency"),
    "card_timeout_s": _positive_float("card_timeout_s"),
    "card_max_bytes": _positive_int("card_max_bytes"),
    "poll_interval_s": _positive_float("poll_interval_s"),
    "max_test_cases_per_skill": _positive_int("max_test_cases_per_skill"),
    "judge_model": _text,
    "judge_endpoint": _text,
    "judge_rubric_version": _text,
    "judge_timeout_s": _positive_float("judge_timeout_s"),
}

#: Environment variables that do not follow the ``SUNCLY_<FIELD>`` pattern.
ENV_ALIASES = {"database_url": "DATABASE_URL"}


def env_var_for(field: str) -> str:
    return ENV_ALIASES.get(field, ENV_PREFIX + field.upper())


def build_config(
    *, default_home: Path, file_values: Mapping[str, Any], env: Mapping[str, str]
) -> Config:
    """Resolve defaults, then the config file, then the environment, in that order."""
    config = Config(home=default_home)
    for name, parser in PARSERS.items():
        if name in file_values:
            raw = file_values[name]
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                continue
            config = replace(config, **{name: parser(str(raw))})
    for name, parser in PARSERS.items():
        raw = env.get(env_var_for(name))
        if raw is None or not raw.strip():
            continue
        config = replace(config, **{name: parser(raw)})
    return config
