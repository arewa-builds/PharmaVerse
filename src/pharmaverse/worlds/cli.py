"""CLI for PharmaVerse Marble world generation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pharmaverse.worlds.client import WorldAPIError, WorldLabsClient, load_api_key
from pharmaverse.worlds.pipeline import generate_jobs, planned_payload, write_json
from pharmaverse.worlds.recipe import PlanMode, load_recipe, plan_jobs

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RECIPE = ROOT / "config" / "marble" / "packaging_suite_v1.yaml"
DEFAULT_OUTPUT = ROOT / "worlds" / "marble"


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pharmaverse-worlds",
        description="Generate and export World Labs Marble worlds for PharmaVerse.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    generate = sub.add_parser("generate", help="Generate worlds from a YAML recipe")
    generate.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    generate.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    generate.add_argument(
        "--mode",
        choices=("primary", "variants", "family"),
        default="primary",
        help="primary=one keeper, variants=primary+variants at one seed, family=all seeds",
    )
    generate.add_argument("--prompt-id", dest="prompt_id")
    generate.add_argument("--seed", type=int)
    generate.add_argument(
        "--draft",
        action="store_true",
        help="Use recipe draft_model (marble-1.0-draft) for cheap prompt iteration",
    )
    generate.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned World API requests without calling Marble",
    )
    generate.add_argument(
        "--no-download",
        action="store_true",
        help="Record metadata and URLs but skip PLY/GLB/pano downloads",
    )
    generate.add_argument("--poll-interval", type=float, default=5.0)
    generate.add_argument("--base-url", default="https://api.worldlabs.ai")

    credits = sub.add_parser("credits", help="Show remaining World API credits")
    credits.add_argument("--base-url", default="https://api.worldlabs.ai")

    export = sub.add_parser("plan", help="Write planned jobs JSON and exit")
    export.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    export.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    export.add_argument("--mode", choices=("primary", "variants", "family"), default="primary")
    export.add_argument("--prompt-id", dest="prompt_id")
    export.add_argument("--seed", type=int)
    export.add_argument("--draft", action="store_true")
    return parser


def _jobs_from_args(args: argparse.Namespace) -> tuple[dict, list]:
    recipe = load_recipe(args.recipe)
    mode: PlanMode = args.mode
    jobs = plan_jobs(
        recipe,
        mode=mode,
        seed=args.seed,
        draft=args.draft,
        prompt_id=args.prompt_id,
    )
    return recipe, jobs


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command in {"generate", "plan"}:
            recipe, jobs = _jobs_from_args(args)
            try:
                recipe_path = str(Path(args.recipe).resolve().relative_to(ROOT))
            except ValueError:
                recipe_path = str(args.recipe)
            plan = planned_payload(
                jobs, recipe_path, args.mode, bool(args.draft)
            )
            dry_run = args.command == "plan" or bool(getattr(args, "dry_run", False))
            if dry_run:
                write_json(args.output / "metadata" / "planned_jobs.json", plan)
                json.dump(plan, sys.stdout, indent=2, sort_keys=True)
                sys.stdout.write("\n")
                print(
                    f"Planned {len(jobs)} world(s) from {recipe['id']}. "
                    "No World API calls were made.",
                    file=sys.stderr,
                )
                return 0
            _load_env_file(ROOT / ".env")
            client = WorldLabsClient(load_api_key(), base_url=args.base_url)
            records = generate_jobs(
                client,
                jobs,
                args.output,
                download=not args.no_download,
                poll_interval_s=args.poll_interval,
                progress=lambda message: print(message, file=sys.stderr),
            )
            json.dump(
                [{"job_id": r["job"]["job_id"], "world_id": r["world_id"]} for r in records],
                sys.stdout,
                indent=2,
            )
            sys.stdout.write("\n")
            return 0

        if args.command == "credits":
            _load_env_file(ROOT / ".env")
            client = WorldLabsClient(load_api_key(), base_url=args.base_url)
            json.dump(client.get_credits(), sys.stdout, indent=2)
            sys.stdout.write("\n")
            return 0
    except WorldAPIError as exc:
        print(exc, file=sys.stderr)
        if exc.status == 402:
            print(
                "Buy World API credits at https://platform.worldlabs.ai/billing "
                "(not marble.worldlabs.ai).",
                file=sys.stderr,
            )
        return 2
    except (ValueError, OSError) as exc:
        print(exc, file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
