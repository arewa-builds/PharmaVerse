"""Open PharmaVerse Environment V1 inside Isaac Sim.

Run with Isaac Sim's Python, not system Python:

    ./python.sh scripts/isaac/bootstrap_environment_v1.py

Or:

    python -m pharmaverse.sim bootstrap
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from pharmaverse.sim.runtime import bootstrap_report  # noqa: E402


def main() -> int:
    report = bootstrap_report()
    json.dump(report, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    if report.get("hint"):
        print(report["hint"], file=sys.stderr)
    if report.get("isaac_available"):
        print(
            "Isaac Sim is importable. Open "
            "worlds/usd/environment_v1/environment_v1.usda and complete "
            "docs/phase-4-isaac-sim.md.",
            file=sys.stderr,
        )
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
