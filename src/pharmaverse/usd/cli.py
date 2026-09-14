"""CLI for PharmaVerse OpenUSD environment composition."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pharmaverse.usd.compose import attach_marble, write_environment
from pharmaverse.usd.convert import ConversionError, ply_to_usdz, threedgrut_available
from pharmaverse.worlds.pipeline import latest_record, resolve_recorded_path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TAXONOMY = ROOT / "config" / "taxonomy.yaml"
DEFAULT_CAMERAS = ROOT / "config" / "cameras.yaml"
DEFAULT_LAYOUT = ROOT / "config" / "usd" / "environment_v1.yaml"
DEFAULT_OUTPUT = ROOT / "worlds" / "usd" / "environment_v1" / "environment_v1.usda"
DEFAULT_MARBLE = ROOT / "worlds" / "marble"


def _default_metadata() -> Path | None:
    record = latest_record(DEFAULT_MARBLE)
    if record and record.get("metadata_path"):
        return Path(record["metadata_path"])
    fallback = DEFAULT_MARBLE / "metadata" / "packaging_suite_v1__primary__seed1.json"
    return fallback if fallback.is_file() else None


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pharmaverse-usd",
        description="Compose PharmaVerse Environment V1 and convert Marble PLY to USDZ.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compose = sub.add_parser("compose", help="Write the Environment V1 USDA stage")
    compose.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    compose.add_argument("--cameras", type=Path, default=DEFAULT_CAMERAS)
    compose.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    compose.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    compose.add_argument("--marble-metadata", type=Path)
    compose.add_argument("--splat-usdz", type=Path)
    compose.add_argument("--collider-glb", type=Path)
    compose.add_argument(
        "--enable-residuals",
        action="store_true",
        help="Make all prototype residuals visible (not a CLEAR scene)",
    )
    compose.add_argument(
        "--sample-discrepancy",
        help="Make one residual class visible (e.g. carton) for a REVIEW REQUIRED demo",
    )

    attach = sub.add_parser(
        "attach",
        help="Stamp a recorded Marble world onto Environment V1 (scale, collider, optional USDZ)",
    )
    attach.add_argument("--metadata", type=Path)
    attach.add_argument("--taxonomy", type=Path, default=DEFAULT_TAXONOMY)
    attach.add_argument("--cameras", type=Path, default=DEFAULT_CAMERAS)
    attach.add_argument("--layout", type=Path, default=DEFAULT_LAYOUT)
    attach.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    attach.add_argument("--splat-usdz", type=Path)
    attach.add_argument("--collider-glb", type=Path)
    attach.add_argument(
        "--convert",
        action="store_true",
        help="Run 3DGRUT PLY→USDZ before composing (needs NVIDIA GPU)",
    )
    attach.add_argument("--sample-discrepancy")

    convert = sub.add_parser("convert", help="Convert a Marble PLY splat to USDZ via 3DGRUT")
    convert.add_argument("--ply", type=Path)
    convert.add_argument(
        "--usdz",
        type=Path,
        default=ROOT / "worlds" / "usd" / "environment_v1" / "marble" / "splats.usdz",
    )
    return parser


def _default_ply() -> Path | None:
    record = latest_record(DEFAULT_MARBLE)
    if not record:
        return None
    local = (record.get("local_files") or {}).get("ply")
    path = resolve_recorded_path(local, output_root=DEFAULT_MARBLE)
    return path


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "compose":
            path = write_environment(
                args.output,
                taxonomy_path=args.taxonomy,
                cameras_path=args.cameras,
                layout_path=args.layout,
                metadata_path=args.marble_metadata,
                splat_usdz=args.splat_usdz,
                collider_glb=args.collider_glb,
                enable_residuals=args.enable_residuals,
                sample_discrepancy=args.sample_discrepancy,
            )
            print(path)
            return 0
        if args.command == "attach":
            metadata = args.metadata or _default_metadata()
            if metadata is None or not Path(metadata).is_file():
                print(
                    "No Marble metadata found. Pass --metadata or run "
                    "`python -m pharmaverse.worlds ingest --world-id ...`.",
                    file=sys.stderr,
                )
                return 2
            path = attach_marble(
                args.output,
                metadata_path=Path(metadata),
                taxonomy_path=args.taxonomy,
                cameras_path=args.cameras,
                layout_path=args.layout,
                splat_usdz=args.splat_usdz,
                collider_glb=args.collider_glb,
                convert=args.convert,
                sample_discrepancy=args.sample_discrepancy,
            )
            print(path)
            return 0
        if args.command == "convert":
            ply = args.ply or _default_ply()
            if ply is None:
                print("Pass --ply or record a Marble world first.", file=sys.stderr)
                return 2
            if not threedgrut_available():
                print(
                    "3DGRUT is not installed. Install https://github.com/nv-tlabs/3dgrut "
                    "on a machine with an NVIDIA GPU, then rerun this command.",
                    file=sys.stderr,
                )
            usdz = ply_to_usdz(ply, args.usdz)
            print(usdz)
            return 0
    except (ConversionError, ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
