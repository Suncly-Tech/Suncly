"""Reads the config file and the environment and builds the one ``Config``."""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from suncly.core.config import Config, build_config, env_var_for
from suncly.domain.errors import ConfigError

DEFAULT_HOME_NAME = ".suncly"


def default_home() -> Path:
    return Path.home() / DEFAULT_HOME_NAME


def read_config_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        with path.open("rb") as handle:
            loaded = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(
            f"The config file {path} cannot be read.",
            f"The error was: {exc}.",
            "Fix or remove the file; every setting also works as an environment variable.",
        ) from exc
    return loaded


def load_config(env: Mapping[str, str], home: Path | None = None) -> Config:
    """Defaults, then ``<home>/config.toml``, then the environment (core/config.py)."""
    env_home = env.get(env_var_for("home"))
    resolved_home = home or (Path(env_home).expanduser() if env_home else default_home())
    file_values = read_config_file(resolved_home / "config.toml")
    file_values.pop("home", None)  # the file cannot relocate itself
    return build_config(default_home=resolved_home, file_values=file_values, env=env)
