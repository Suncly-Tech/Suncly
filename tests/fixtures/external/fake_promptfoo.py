"""A stand-in for the promptfoo binary: answers --version and writes the fixture results."""

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
args = sys.argv[1:]
if args == ["--version"]:
    sys.stdout.write(os.environ.get("FAKE_PROMPTFOO_VERSION", "0.123.1") + "\n")
    sys.exit(0)
assert args[0] == "eval", args
output = Path(args[args.index("--output") + 1])
assert "--no-cache" in args and any(a.startswith("target_url=") for a in args), args
if os.environ.get("FAKE_PROMPTFOO_MODE") == "no-output":
    sys.exit(3)
shutil.copy(HERE / "promptfoo-results.json", output)
sys.exit(0)
