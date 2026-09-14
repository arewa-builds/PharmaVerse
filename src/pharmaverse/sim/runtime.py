"""Optional Isaac Sim runtime helpers. Safe to import without Isaac installed."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pharmaverse.sim.scene import isaac_available, load_sim_config, verify_stage_file


def bootstrap_report(stage_path: str | Path | None = None) -> dict[str, Any]:
    config = load_sim_config()
    stage = Path(stage_path) if stage_path else Path(config["stage"])
    if not stage.is_absolute():
        stage = Path(__file__).resolve().parents[3] / stage
    report = verify_stage_file(stage)
    report["isaac_available"] = isaac_available()
    report["isaac_minimum"] = (config.get("isaac_sim") or {}).get("minimum")
    report["manual_steps"] = [item["title"] for item in config.get("checklist") or []]
    if not report["isaac_available"]:
        report["hint"] = (
            "Open this USDA with Isaac Sim 5.1+ (prefer 6.x), or rerun "
            "`python -m pharmaverse.sim bootstrap` using Isaac Sim's python.sh."
        )
    return report
