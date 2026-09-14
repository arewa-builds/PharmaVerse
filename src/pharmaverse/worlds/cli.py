"""CLI for PharmaVerse Marble world generation."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from pharmaverse.worlds.client import WorldAPIError, WorldLabsClient, load_api_key
from pharmaverse.worlds.pipeline import (
    generate_jobs,
    handoff_status,
    ingest_world,
    parse_world_id,
    planned_payload,
    write_json,
)
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
        description="Generate, ingest, and export World Labs Marble worlds for PharmaVerse.",
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

    ingest = sub.add_parser(
        "ingest",
        help="Record an already-generated Marble world and export PLY + collider",
    )
    ingest.add_argument("--world-id", required=True, help="World UUID or marble.worldlabs.ai/world/ URL")
    ingest.add_argument("--recipe", type=Path, default=DEFAULT_RECIPE)
    ingest.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ingest.add_argument("--job-id")
    ingest.add_argument("--prompt-id", dest="prompt_id")
    ingest.add_argument("--seed", type=int, default=1)
    ingest.add_argument(
        "--as-primary",
        action="store_true",
        help="Store as the packaging_suite_v1 primary keeper (seed 1 unless --seed is set)",
    )
    ingest.add_argument("--no-download", action="store_true")
    ingest.add_argument("--poll-interval", type=float, default=5.0)
    ingest.add_argument("--base-url", default="https://api.worldlabs.ai")

    listing = sub.add_parser("list", help="List World API worlds for this account")
    listing.add_argument("--model", default="marble-1.1")
    listing.add_argument("--page-size", type=int, default=20)
    listing.add_argument("--page-token")
    listing.add_argument("--base-url", default="https://api.worldlabs.ai")

    credits = sub.add_parser("credits", help="Show remaining World API credits")
    credits.add_argument("--base-url", default="https://api.worldlabs.ai")

    status = sub.add_parser("status", help="Show the next step after a generated Marble world")
    status.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)

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


def _client(args: argparse.Namespace) -> WorldLabsClient:
    _load_env_file(ROOT / ".env")
    return WorldLabsClient(load_api_key(), base_url=args.base_url)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "status":
            payload = handoff_status(args.output)
            json.dump(payload, sys.stdout, indent=2, sort_keys=True)
            sys.stdout.write("\n")
            print(payload["summary"], file=sys.stderr)
            for command in payload["commands"]:
                print(f"  {command}", file=sys.stderr)
            return 0

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
            client = _client(args)
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
            print(handoff_status(args.output)["summary"], file=sys.stderr)
            return 0

        if args.command == "ingest":
            client = _client(args)
            record = ingest_world(
                client,
                parse_world_id(args.world_id),
                args.output,
                recipe_path=args.recipe,
                job_id=args.job_id,
                prompt_id=args.prompt_id,
                seed=args.seed,
                as_primary=args.as_primary or not args.job_id,
                download=not args.no_download,
                poll_interval_s=args.poll_interval,
                progress=lambda message: print(message, file=sys.stderr),
            )
            json.dump(
                {
                    "job_id": record["job"]["job_id"],
                    "world_id": record["world_id"],
                    "metadata_path": record["metadata_path"],
                    "local_files": record.get("local_files") or {},
                },
                sys.stdout,
                indent=2,
            )
            sys.stdout.write("\n")
            status = handoff_status(args.output)
            print(status["summary"], file=sys.stderr)
            for command in status["commands"]:
                print(f"  {command}", file=sys.stderr)
            return 0

        if args.command == "list":
            client = _client(args)
            payload = client.list_worlds(
                model=args.model,
                page_size=args.page_size,
                page_token=args.page_token,
                sort_by="created_at",
            )
            worlds = payload.get("worlds") or payload.get("items") or []
            compact = []
            for world in worlds:
                world = world if isinstance(world, dict) else {}
                world_id = world.get("world_id") or world.get("id")
                compact.append(
                    {
                        "world_id": world_id,
                        "model": world.get("model"),
                        "display_name": world.get("display_name"),
                        "marble_url": world.get("world_marble_url")
                        or (f"https://marble.worldlabs.ai/world/{world_id}" if world_id else None),
                    }
                )
            json.dump(
                {"worlds": compact, "next_page_token": payload.get("next_page_token")},
                sys.stdout,
                indent=2,
            )
            sys.stdout.write("\n")
            return 0

        if args.command == "credits":
            client = _client(args)
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
    except (ValueError, OSError, RuntimeError) as exc:
        print(exc, file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
