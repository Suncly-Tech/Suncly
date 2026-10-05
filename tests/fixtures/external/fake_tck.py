"""A stand-in for the TCK's run_tck.py: writes the fixture report, or misbehaves on request."""

import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
mode = os.environ.get("FAKE_TCK_MODE", "ok")
args = sys.argv[1:]
assert "--sut-host" in args, args
if mode == "hang":
    import time

    time.sleep(30)
if mode == "crash":
    sys.stderr.write("Traceback: the SUT is unreachable\n")
    sys.exit(2)
reports = Path("reports")
reports.mkdir(exist_ok=True)
if mode == "garbage":
    (reports / "compatibility.json").write_text("{not json", encoding="utf-8")
else:
    shutil.copy(HERE / "compatibility.json", reports / "compatibility.json")
    (reports / "junitreport.xml").write_text("<testsuite/>", encoding="utf-8")
sys.stdout.write("A2A Compatibility: 66.7%\n")
sys.exit(0 if mode == "ok" else 1)
