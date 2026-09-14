"""Generate Marble worlds from a recipe, export assets, and write metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pharmaverse.worlds.client import WorldLabsClient, unwrap_world
from pharmaverse.worlds.recipe import WorldJob, load_recipe, plan_jobs

Progress = Callable[[str], None]

ROOT = Path(__file__).resolve().parents[3]
SKIP_METADATA_NAMES = {"planned_jobs.json", "index.json"}
EXPORT_MARKER = "worlds/marble/exports/"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_world_id(value: str) -> str:
    """Accept a raw world_id or a marble.worldlabs.ai/world/{id} URL."""
    text = (value or "").strip()
    if not text:
        raise ValueError("world_id is required")
    if "/world/" in text:
        text = text.split("/world/", 1)[1]
    text = text.split("?", 1)[0].split("#", 1)[0].strip("/")
    if not text:
        raise ValueError(f"Could not parse a Marble world_id from {value!r}")
    return text


def repo_relative(path: Path, root: Path | None = None) -> str:
    base = (root or ROOT).resolve()
    try:
        return path.resolve().relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def resolve_recorded_path(raw: str | None, *, output_root: Path | None = None) -> Path | None:
    """Resolve a recorded export path across Windows/POSIX checkouts."""
    if not raw:
        return None
    posix = str(raw).replace("\\", "/")
    candidates = [Path(raw), Path(posix)]
    if EXPORT_MARKER in posix:
        tail = posix.split(EXPORT_MARKER, 1)[1]
        candidates.append(ROOT / "worlds" / "marble" / "exports" / tail)
        if output_root is not None:
            candidates.append(Path(output_root) / "exports" / tail)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    if EXPORT_MARKER in posix:
        tail = posix.split(EXPORT_MARKER, 1)[1]
        return ROOT / "worlds" / "marble" / "exports" / tail
    return Path(posix)


def _assets(world: dict[str, Any]) -> dict[str, Any]:
    assets = world.get("assets") or {}
    splats = assets.get("splats") or {}
    mesh = assets.get("mesh") or {}
    imagery = assets.get("imagery") or {}
    return {
        "caption": assets.get("caption"),
        "thumbnail_url": assets.get("thumbnail_url"),
        "pano_url": imagery.get("pano_url"),
        "collider_mesh_url": mesh.get("collider_mesh_url"),
        "hq_mesh_url": mesh.get("hq_mesh_url"),
        "spz_urls": splats.get("spz_urls") or {},
        "semantics_metadata": splats.get("semantics_metadata") or {},
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def planned_payload(jobs: list[WorldJob], recipe_path: str, mode: str, draft: bool) -> dict[str, Any]:
    return {
        "created_at": _utc_now(),
        "draft": draft,
        "mode": mode,
        "recipe_path": recipe_path,
        "jobs": [job.to_dict() for job in jobs],
    }


def _index_entry(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": record["job"]["job_id"],
        "metadata_path": repo_relative(Path(record["metadata_path"])),
        "world_id": record["world_id"],
        "world_marble_url": record["world"]["marble_url"],
    }


def upsert_index(output_root: Path, records: list[dict[str, Any]]) -> None:
    path = output_root / "metadata" / "index.json"
    existing: list[dict[str, Any]] = []
    if path.is_file():
        payload = json.loads(path.read_text(encoding="utf-8"))
        existing = payload.get("records") or []
    by_world: dict[str, dict[str, Any]] = {}
    for item in existing:
        key = item.get("world_id") or item.get("job_id")
        if key:
            by_world[str(key)] = item
    for record in records:
        by_world[str(record["world_id"])] = _index_entry(record)
    write_json(
        path,
        {
            "created_at": _utc_now(),
            "records": list(by_world.values()),
        },
    )


def persist_world(
    client: WorldLabsClient,
    world: dict[str, Any],
    output_root: Path,
    *,
    job: dict[str, Any],
    operation_id: str | None = None,
    download: bool = True,
    poll_interval_s: float = 5.0,
    poll_timeout_s: float = 1200.0,
    progress: Progress | None = None,
    experiment: str | None = None,
) -> dict[str, Any]:
    log = progress or (lambda _message: None)
    world = unwrap_world(world)
    world_id = world.get("world_id") or world.get("id")
    if not world_id:
        raise RuntimeError(f"No world_id in world payload: {world}")
    assets = _assets(world)

    log(f"exporting PLY for {world_id}")
    ply_op = client.export_world(
        world_id,
        {"asset_type": "splats", "format": "ply", "resolution": "full_res"},
    )
    if not ply_op.get("done"):
        ply_op = client.poll_operation(
            ply_op["operation_id"], interval_s=poll_interval_s, timeout_s=poll_timeout_s
        )
    ply_response = ply_op.get("response") or {}
    ply_url = ply_response.get("url")
    ply_export = {"operation_id": ply_op.get("operation_id"), "url": ply_url}

    job_id = job["job_id"]
    export_dir = output_root / "exports" / job_id
    local_files: dict[str, str] = {}
    if download:
        export_dir.mkdir(parents=True, exist_ok=True)
        downloads = {
            "thumbnail": (assets.get("thumbnail_url"), "thumbnail.jpg"),
            "pano": (assets.get("pano_url"), "pano.png"),
            "collider": (assets.get("collider_mesh_url"), "collider.glb"),
            "ply": (ply_url, "splats_full_res.ply"),
        }
        for name, (url, filename) in downloads.items():
            if not url:
                continue
            dest = export_dir / filename
            log(f"downloading {name} -> {dest}")
            client.download(url, str(dest))
            local_files[name] = repo_relative(dest)

    record = {
        "assets": assets,
        "created_at": _utc_now(),
        "experiment": experiment if experiment is not None else job.get("experiment"),
        "job": job,
        "local_files": local_files,
        "operation_id": operation_id,
        "ply_export": ply_export,
        "world": {
            "caption": assets.get("caption"),
            "id": world_id,
            "marble_url": world.get("world_marble_url")
            or f"https://marble.worldlabs.ai/world/{world_id}",
            "model": world.get("model") or job.get("model"),
        },
        "world_id": world_id,
    }
    metadata_path = output_root / "metadata" / f"{job_id}.json"
    write_json(metadata_path, record)
    record["metadata_path"] = str(metadata_path)
    return record


def generate_one(
    client: WorldLabsClient,
    job: WorldJob,
    output_root: Path,
    *,
    download: bool = True,
    poll_interval_s: float = 5.0,
    poll_timeout_s: float = 1200.0,
    progress: Progress | None = None,
) -> dict[str, Any]:
    log = progress or (lambda _message: None)
    log(f"generating {job.job_id} with {job.model} seed={job.seed}")
    started = client.generate_world(job.generate_request())
    operation_id = started["operation_id"]
    log(f"operation {operation_id}")
    finished = client.poll_operation(
        operation_id, interval_s=poll_interval_s, timeout_s=poll_timeout_s
    )
    snapshot = unwrap_world(finished.get("response") or {})
    world_id = snapshot.get("world_id") or (finished.get("metadata") or {}).get("world_id")
    if not world_id:
        raise RuntimeError(f"No world_id in operation {operation_id}: {finished}")
    world = client.get_world(world_id)
    return persist_world(
        client,
        world,
        output_root,
        job=job.to_dict(),
        operation_id=operation_id,
        download=download,
        poll_interval_s=poll_interval_s,
        poll_timeout_s=poll_timeout_s,
        progress=progress,
        experiment=job.experiment,
    )


def ingest_world(
    client: WorldLabsClient,
    world_id: str,
    output_root: Path,
    *,
    recipe_path: Path | None = None,
    job_id: str | None = None,
    prompt_id: str | None = None,
    seed: int | None = None,
    as_primary: bool = False,
    download: bool = True,
    poll_interval_s: float = 5.0,
    poll_timeout_s: float = 1200.0,
    progress: Progress | None = None,
) -> dict[str, Any]:
    """Record an already-generated Marble world (API or web app) and export PLY/GLB."""
    log = progress or (lambda _message: None)
    world_id = parse_world_id(world_id)
    log(f"ingesting {world_id}")
    world = client.get_world(world_id)
    recipe = load_recipe(recipe_path) if recipe_path else None
    job: dict[str, Any]
    if as_primary or (recipe and not job_id):
        if recipe is None:
            raise ValueError("--as-primary requires a recipe")
        planned = plan_jobs(
            recipe,
            mode="primary",
            seed=seed,
            prompt_id=prompt_id or "primary",
        )
        job = planned[0].to_dict()
    else:
        job = {
            "job_id": job_id or f"ingested__{world_id}",
            "prompt_id": prompt_id or "ingested",
            "seed": seed,
            "model": world.get("model"),
            "display_name": world.get("display_name"),
            "text_prompt": ((world.get("world_prompt") or {}) or {}).get("text_prompt"),
            "source": "ingest",
            "recipe_id": (recipe or {}).get("id") if recipe else None,
            "experiment": (recipe or {}).get("experiment") if recipe else "line_clearance_01",
        }
    record = persist_world(
        client,
        world,
        output_root,
        job=job,
        download=download,
        poll_interval_s=poll_interval_s,
        poll_timeout_s=poll_timeout_s,
        progress=progress,
        experiment=job.get("experiment"),
    )
    upsert_index(output_root, [record])
    return record


def generate_jobs(
    client: WorldLabsClient,
    jobs: list[WorldJob],
    output_root: Path,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    records = [generate_one(client, job, output_root, **kwargs) for job in jobs]
    upsert_index(output_root, records)
    return records


def recorded_worlds(output_root: Path) -> list[dict[str, Any]]:
    meta_dir = output_root / "metadata"
    if not meta_dir.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(meta_dir.glob("*.json")):
        if path.name in SKIP_METADATA_NAMES:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("world_id"):
            payload = dict(payload)
            payload["metadata_path"] = str(path)
            records.append(payload)
    return records


def latest_record(output_root: Path) -> dict[str, Any] | None:
    records = recorded_worlds(output_root)
    if not records:
        return None
    return records[-1]


def handoff_status(
    marble_root: Path | None = None,
    usd_root: Path | None = None,
) -> dict[str, Any]:
    """What to do next after a Marble 1.1 world exists."""
    marble_root = marble_root or (ROOT / "worlds" / "marble")
    usd_root = usd_root or (ROOT / "worlds" / "usd" / "environment_v1")
    record = latest_record(marble_root)
    usda = usd_root / "environment_v1.usda"
    usdz = usd_root / "marble" / "splats.usdz"
    usda_text = usda.read_text(encoding="utf-8") if usda.is_file() else ""

    ply_path = None
    collider_path = None
    metadata_path = None
    world_id = None
    model = None
    if record:
        world_id = record.get("world_id")
        model = (record.get("world") or {}).get("model")
        metadata_path = repo_relative(Path(record["metadata_path"]))
        local = record.get("local_files") or {}
        ply_resolved = resolve_recorded_path(local.get("ply"), output_root=marble_root)
        collider_resolved = resolve_recorded_path(local.get("collider"), output_root=marble_root)
        ply_path = repo_relative(ply_resolved) if ply_resolved else local.get("ply")
        collider_path = repo_relative(collider_resolved) if collider_resolved else local.get("collider")
        ply_exists = bool(ply_resolved and ply_resolved.is_file())
        collider_exists = bool(collider_resolved and collider_resolved.is_file())
    else:
        ply_exists = False
        collider_exists = False

    usdz_exists = usdz.is_file()
    attached = bool(usda_text) and "pending_nurec_conversion" not in usda_text
    scaled = bool(usda_text) and world_id and world_id in usda_text

    if not record:
        action = "generate_or_ingest"
        commands = [
            "python -m pharmaverse.worlds generate --mode primary",
            "python -m pharmaverse.worlds ingest --world-id WORLD_ID --as-primary",
        ]
        summary = "No Marble world is recorded. Generate one, or ingest a world_id from marble.worldlabs.ai."
    elif not usdz_exists:
        action = "convert_ply"
        ply_arg = ply_path or "worlds/marble/exports/JOB/splats_full_res.ply"
        commands = [
            f"python -m pharmaverse.usd convert --ply {ply_arg} --usdz worlds/usd/environment_v1/marble/splats.usdz",
            f"python -m pharmaverse.usd attach --metadata {metadata_path}",
            "python -m pharmaverse.sim checklist",
        ]
        summary = (
            "Marble 1.1 world is recorded. Next: convert the full-res PLY through 3DGRUT "
            "on an NVIDIA GPU, attach it to Environment V1, then open Isaac Sim."
        )
    elif not attached:
        action = "attach_usd"
        commands = [
            f"python -m pharmaverse.usd attach --metadata {metadata_path}",
            "python -m pharmaverse.sim checklist",
        ]
        summary = "USDZ exists. Attach splat + collider + Marble scale onto Environment V1."
    else:
        action = "isaac_sim"
        commands = [
            "python -m pharmaverse.sim checklist",
            "python -m pharmaverse.sim spawn --class carton",
        ]
        summary = "Environment V1 has a converted splat. Open the USDA in Isaac Sim and run the Phase 4 checklist."

    return {
        "action": action,
        "collider_exists": collider_exists,
        "collider_path": collider_path,
        "commands": commands,
        "metadata_path": metadata_path,
        "model": model,
        "ply_exists": ply_exists,
        "ply_path": ply_path,
        "scaled_in_usda": scaled,
        "splat_attached": attached,
        "summary": summary,
        "usda": repo_relative(usda) if usda.is_file() else None,
        "usdz": repo_relative(usdz) if usdz_exists else None,
        "usdz_exists": usdz_exists,
        "world_id": world_id,
        "world_marble_url": (record.get("world") or {}).get("marble_url") if record else None,
    }
