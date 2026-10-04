"""One typed Config, resolved from defaults, file and environment in that order."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from suncly.adapters.config_loader import load_config
from suncly.core.config import Config, build_config, env_var_for
from suncly.domain.errors import ConfigError


def test_defaults_then_file_then_environment() -> None:
    config = build_config(
        default_home=Path("/h"),
        file_values={"runs": 7, "concurrency": "3", "reports_dir": "out"},
        env={"SUNCLY_RUNS": "9", "DATABASE_URL": "postgresql://x/y"},
    )
    assert config.runs == 9, "environment wins over the file"
    assert config.concurrency == 3, "file wins over defaults"
    assert config.reports_dir == Path("out")
    assert config.database_url == "postgresql://x/y" and config.uses_postgres
    assert config.max_retries == 2, "untouched defaults stay"
    assert config.store_dir == Path("/h") / "store"


def test_blank_values_are_ignored() -> None:
    config = build_config(
        default_home=Path("/h"), file_values={"runs": ""}, env={"SUNCLY_RUNS": "  "}
    )
    assert config.runs == 5


@pytest.mark.parametrize(
    ("env", "message"),
    [
        ({"SUNCLY_RUNS": "zero"}, "not a whole number"),
        ({"SUNCLY_RUNS": "0"}, "at least 1"),
        ({"SUNCLY_MAX_RETRIES": "-1"}, "cannot be negative"),
        ({"SUNCLY_RUN_TIMEOUT_S": "0"}, "greater than 0"),
        ({"SUNCLY_BUDGET_LIMIT": "abc"}, "not a number"),
    ],
)
def test_invalid_values_fail_with_the_setting_named(env: dict[str, str], message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        build_config(default_home=Path("/h"), file_values={}, env=env)


def test_env_var_names() -> None:
    assert env_var_for("runs") == "SUNCLY_RUNS"
    assert env_var_for("database_url") == "DATABASE_URL"


def test_with_overrides_applies_only_given_values() -> None:
    config = Config(home=Path("/h")).with_overrides(runs=None, reports_dir=Path("r"))
    assert config.runs == 5 and config.reports_dir == Path("r")


def test_load_config_reads_the_toml_file_in_home(tmp_path: Path) -> None:
    (tmp_path / "config.toml").write_text(
        'runs = 4\nbudget_limit = "12.5"\nhome = "ignored"\n', encoding="utf-8"
    )
    config = load_config({}, home=tmp_path)
    assert config.home == tmp_path and config.runs == 4 and config.budget_limit == Decimal("12.5")
    (tmp_path / "config.toml").write_text("runs = [", encoding="utf-8")
    with pytest.raises(ConfigError, match="cannot be read"):
        load_config({}, home=tmp_path)


def test_load_config_honours_suncly_home_from_the_environment(tmp_path: Path) -> None:
    config = load_config({"SUNCLY_HOME": str(tmp_path / "elsewhere")})
    assert config.home == tmp_path / "elsewhere"
