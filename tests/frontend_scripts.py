"""Load the Python scripts under ``frontend/scripts`` for testing.

``frontend/scripts/make-sample.py`` has a hyphen in its name, so it cannot be
imported by name; it is loaded from its path and registered as ``make_sample``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

REPO_ROOT = Path(__file__).resolve().parents[1]
MAKE_SAMPLE = REPO_ROOT / "frontend" / "scripts" / "make-sample.py"
MODULE_NAME = "make_sample"


def load_make_sample() -> ModuleType:
    """Import ``frontend/scripts/make-sample.py`` once and return the module."""
    loaded = sys.modules.get(MODULE_NAME)
    if loaded is not None:
        return loaded
    spec = importlib.util.spec_from_file_location(MODULE_NAME, MAKE_SAMPLE)
    assert spec is not None and spec.loader is not None, MAKE_SAMPLE
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module
