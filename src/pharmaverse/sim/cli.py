"""CLI for PharmaVerse Isaac Sim Phase 4."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pharmaverse.sim.runtime import bootstrap_report
from pharmaverse.sim.scene import checklist_items, load_sim_config, verify_stage_file
from pharmaverse.usd.compose import attach_marble, write_environment
from pharmaverse.worlds.pipeline import latest_record

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TAXONOMY = ROOT / "config" / "taxonomy.yaml"
DEFAULT_CAMERAS = ROOT / "config" / "cameras.yaml"
DEFAULT_LAYOUT = ROOT / "config" / "usd" / "environment_v1.yaml"
DEFAULT_CLEAR = ROOT / "worlds" / "usd" / "environment_v1" / "environment_v1.usda"
DEFAULT_DISCREPANCY = ROOT / "worlds" / "usd" / "environment_v1" / "discrepancy_carton.usda"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pharmaverse-sim",
        description="Isaac Sim Phase 4 helpers for PharmaVerse Environment V1.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("checklist", help="Print the Isaac Sim validation checklist")

    verify = sub.add_parser("verify", help="Statically verify Environment V1 USDA")
    verify.add_argument("--usda", type=Path, default=DEFAULT_CLEAR)

    spawn = sub.add_parser("spawn", help="Write a REVIEW REQUIRED USDA with one residual visible")
    spawn.add_argument("--class", dest="residual_class", default="carton")
    spawn.add_argument("--output", type=Path, default=DEFAULT_DISCREPANCY)
    spawn.add_argument("--metadata", type=Path)

    boot = sub.add_parser("bootstrap", help="Report how to open the stage in Isaac Sim")
    boot.add_argument("--usda", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "checklist":
        payload = {
            "isaac_sim": load_sim_config().get("isaac_sim"),
            "checklist": checklist_items(),
            "rules": load_sim_config().get("rules"),
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0
    if args.command == "verify":
        record = latest_record(ROOT / "worlds" / "marble")
        world_id = record.get("world_id") if record else None
        report = verify_stage_file(args.usda, world_id=world_id)
        json.dump(report, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if report["ok"] else 2
    if args.command == "spawn":
        record = latest_record(ROOT / "worlds" / "marble")
        metadata = args.metadata
        if metadata is None and record:
            metadata = Path(record["metadata_path"])
        if metadata and Path(metadata).is_file():
            path = attach_marble(
                args.output,
                metadata_path=Path(metadata),
                taxonomy_path=DEFAULT_TAXONOMY,
                cameras_path=DEFAULT_CAMERAS,
                layout_path=DEFAULT_LAYOUT,
                sample_discrepancy=args.residual_class,
            )
        else:
            path = write_environment(
                args.output,
                taxonomy_path=DEFAULT_TAXONOMY,
                cameras_path=DEFAULT_CAMERAS,
                layout_path=DEFAULT_LAYOUT,
                sample_discrepancy=args.residual_class,
            )
        print(path)
        return 0
    if args.command == "bootstrap":
        report = bootstrap_report(args.usda)
        json.dump(report, sys.stdout, indent=2, sort_keys=True)
        sys.stdout.write("\n")
        if report.get("hint"):
            print(report["hint"], file=sys.stderr)
        return 0 if report.get("ok") else 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
