from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

from pharmaverse.worlds.client import WorldLabsClient
from pharmaverse.worlds.cli import main
from pharmaverse.worlds.pipeline import (
    generate_one,
    handoff_status,
    ingest_world,
    parse_world_id,
    persist_world,
    resolve_recorded_path,
)
from pharmaverse.worlds.recipe import load_recipe, plan_jobs

RECIPE = Path(__file__).resolve().parents[1] / "config" / "marble" / "packaging_suite_v1.yaml"
ROOT = Path(__file__).resolve().parents[1]


def _world_payload() -> dict:
    return {
        "world_id": "world-1",
        "world_marble_url": "https://marble.worldlabs.ai/world/world-1",
        "model": "marble-1.1",
        "assets": {
            "caption": "A packaging suite",
            "thumbnail_url": "https://example.com/thumb.jpg",
            "splats": {
                "spz_urls": {"full_res": "https://example.com/world.spz"},
                "semantics_metadata": {
                    "metric_scale_factor": 1.5,
                    "ground_plane_offset": 0.2,
                },
            },
            "mesh": {"collider_mesh_url": "https://example.com/collider.glb"},
            "imagery": {"pano_url": "https://example.com/pano.png"},
        },
    }


def _opener(req: Request) -> tuple[int, bytes]:
    url = req.full_url
    method = req.get_method()
    if method == "POST" and url.endswith("/worlds:generate"):
        return 200, json.dumps({"operation_id": "op-gen", "done": False}).encode()
    if url.endswith("/operations/op-gen"):
        return 200, json.dumps(
            {
                "operation_id": "op-gen",
                "done": True,
                "error": None,
                "metadata": {"world_id": "world-1"},
                "response": {"id": "world-1"},
            }
        ).encode()
    if method == "GET" and url.endswith("/worlds/world-1"):
        return 200, json.dumps(_world_payload()).encode()
    if method == "POST" and url.endswith("/worlds/world-1:export"):
        return 200, json.dumps(
            {
                "operation_id": "op-ply",
                "done": True,
                "response": {"url": "https://example.com/world.ply"},
            }
        ).encode()
    raise AssertionError((method, url))


def test_parse_world_id_from_url() -> None:
    assert (
        parse_world_id("https://marble.worldlabs.ai/world/850b4709-cabf-4643-8bf6-5cc187e85fa4")
        == "850b4709-cabf-4643-8bf6-5cc187e85fa4"
    )
    assert parse_world_id("world-1") == "world-1"


def test_generate_one_writes_metadata(tmp_path: Path) -> None:
    job = plan_jobs(load_recipe(RECIPE), mode="primary")[0]
    record = generate_one(
        WorldLabsClient("test-key", opener=_opener),
        job,
        tmp_path,
        download=False,
        poll_interval_s=0,
    )
    assert record["world_id"] == "world-1"
    assert record["assets"]["collider_mesh_url"].endswith("collider.glb")
    assert record["ply_export"]["url"].endswith("world.ply")
    saved = json.loads((tmp_path / "metadata" / f"{job.job_id}.json").read_text())
    assert saved["world"]["model"] == "marble-1.1"
    assert saved["assets"]["semantics_metadata"]["metric_scale_factor"] == 1.5


def test_ingest_world_exports_existing_id(tmp_path: Path) -> None:
    record = ingest_world(
        WorldLabsClient("test-key", opener=_opener),
        "https://marble.worldlabs.ai/world/world-1",
        tmp_path,
        recipe_path=RECIPE,
        as_primary=True,
        download=False,
        poll_interval_s=0,
    )
    assert record["job"]["job_id"] == "packaging_suite_v1__primary__seed1"
    index = json.loads((tmp_path / "metadata" / "index.json").read_text())
    assert index["records"][0]["world_id"] == "world-1"


def test_resolve_recorded_windows_export_path(tmp_path: Path) -> None:
    export = ROOT / "worlds" / "marble" / "exports" / "demo" / "collider.glb"
    export.parent.mkdir(parents=True, exist_ok=True)
    export.write_bytes(b"glb")
    try:
        raw = r"C:\Users\arewa\PharmaVerse\worlds\marble\exports\demo\collider.glb"
        resolved = resolve_recorded_path(raw, output_root=ROOT / "worlds" / "marble")
        assert resolved == export
    finally:
        export.unlink()
        export.parent.rmdir()


def test_handoff_status_points_at_convert() -> None:
    payload = handoff_status(ROOT / "worlds" / "marble")
    assert payload["world_id"] == "850b4709-cabf-4643-8bf6-5cc187e85fa4"
    assert payload["action"] in {"convert_ply", "attach_usd", "isaac_sim"}
    assert payload["commands"]


def test_persist_world_relative_paths(tmp_path: Path) -> None:
    calls: list[str] = []

    def opener(req: Request) -> tuple[int, bytes]:
        calls.append(req.full_url)
        if req.full_url.endswith(":export"):
            return 200, json.dumps(
                {"operation_id": "op-ply", "done": True, "response": {"url": "https://example.com/world.ply"}}
            ).encode()
        raise AssertionError(req.full_url)

    def download(_url: str, dest: str, timeout_s: float = 300.0) -> str:
        Path(dest).write_bytes(b"x")
        return dest

    client = WorldLabsClient("test-key", opener=opener)
    client.download = download  # type: ignore[method-assign]
    job = plan_jobs(load_recipe(RECIPE), mode="primary")[0].to_dict()
    record = persist_world(client, _world_payload(), tmp_path, job=job, download=True)
    ply = record["local_files"]["ply"]
    assert "\\" not in ply
    assert ply.endswith("splats_full_res.ply")
    assert Path(ply).is_file() or (tmp_path / "exports" / job["job_id"] / "splats_full_res.ply").is_file()


def test_status_cli(capsys) -> None:
    code = main(["status"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert "action" in payload
    assert "commands" in payload
