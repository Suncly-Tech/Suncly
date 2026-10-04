"""Developer task runner: ``python tasks.py <task>``.

The same commands work on Windows PowerShell, macOS and Linux, which is why
this is a Python script rather than a Makefile. The Makefile in the repository
root delegates to it. Tasks:

    install     install the package with its development dependencies
    lint        ruff check and ruff format --check
    format      ruff format and ruff check --fix
    typecheck   mypy in strict mode
    test        pytest with coverage
    check       lint, typecheck and test, in that order
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

TASKS: dict[str, Sequence[Sequence[str]]] = {
    "install": [[sys.executable, "-m", "pip", "install", "-e", ".[dev]"]],
    "lint": [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
    ],
    "format": [
        [sys.executable, "-m", "ruff", "format", "."],
        [sys.executable, "-m", "ruff", "check", "--fix", "."],
    ],
    "typecheck": [[sys.executable, "-m", "mypy"]],
    "test": [
        [sys.executable, "-m", "pytest", "--cov", "--cov-report=term-missing"],
    ],
}
TASKS["check"] = [*TASKS["lint"], *TASKS["typecheck"], *TASKS["test"]]


def run(task: str, extra: Sequence[str]) -> int:
    """Run every command of ``task`` and stop at the first failure."""
    commands = TASKS.get(task)
    if commands is None:
        print(f"unknown task {task!r}; choose one of: {', '.join(TASKS)}")
        return 2
    for command in commands:
        full = [*command, *extra] if task in {"test", "typecheck"} else list(command)
        print("$", " ".join(full), flush=True)
        result = subprocess.run(full, check=False)
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(run(sys.argv[1], sys.argv[2:]))
