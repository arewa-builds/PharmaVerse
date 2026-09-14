"""CLI for PharmaVerse OpenUSD environment composition."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pharmaverse.usd.compose import write_environment
from pharmaverse.usd.convert import ConversionError, ply_to_usdz, threedgrut_available

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_TAXONOMY = ROOT / "config" / "taxonomy.yaml"
DEFAULT_CAMERAS = ROOT / "config" / "cameras.yaml"
DEFAULT_LAYOUT = ROOT / "config" / "usd" / "environment_v1.yaml"
DEFAULT_OUTPUT = ROOT / "worlds" / "usd" / "environment_v1" / "environment_v1.usda"


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

    convert = sub.add_parser("convert", help="Convert a Marble PLY splat to USDZ via 3DGRUT")
    convert.add_argument("--ply", type=Path, required=True)
    convert.add_argument("--usdz", type=Path, required=True)
    return parser


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
        if args.command == "convert":
            if not threedgrut_available():
                print(
                    "3DGRUT is not installed. Install https://github.com/nv-tlabs/3dgrut "
                    "on a machine with an NVIDIA GPU, then rerun this command.",
                    file=sys.stderr,
                )
            usdz = ply_to_usdz(args.ply, args.usdz)
            print(usdz)
            return 0
    except (ConversionError, ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
