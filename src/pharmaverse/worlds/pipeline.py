"""Generate Marble worlds from a recipe, export assets, and write metadata."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pharmaverse.worlds.client import WorldLabsClient, unwrap_world
from pharmaverse.worlds.recipe import WorldJob

Progress = Callable[[str], None]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
    assets = _assets(world)

    ply_export: dict[str, Any] | None = None
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

    export_dir = output_root / "exports" / job.job_id
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
            local_files[name] = str(dest)

    record = {
        "assets": assets,
        "created_at": _utc_now(),
        "experiment": job.experiment,
        "job": job.to_dict(),
        "local_files": local_files,
        "operation_id": operation_id,
        "ply_export": ply_export,
        "world": {
            "caption": assets.get("caption"),
            "id": world_id,
            "marble_url": world.get("world_marble_url")
            or f"https://marble.worldlabs.ai/world/{world_id}",
            "model": world.get("model") or job.model,
        },
        "world_id": world_id,
    }
    metadata_path = output_root / "metadata" / f"{job.job_id}.json"
    write_json(metadata_path, record)
    record["metadata_path"] = str(metadata_path)
    return record


def generate_jobs(
    client: WorldLabsClient,
    jobs: list[WorldJob],
    output_root: Path,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    records = [generate_one(client, job, output_root, **kwargs) for job in jobs]
    write_json(
        output_root / "metadata" / "index.json",
        {
            "created_at": _utc_now(),
            "records": [
                {
                    "job_id": record["job"]["job_id"],
                    "metadata_path": record["metadata_path"],
                    "world_id": record["world_id"],
                    "world_marble_url": record["world"]["marble_url"],
                }
                for record in records
            ],
        },
    )
    return records
