from __future__ import annotations

import json
from pathlib import Path
from urllib.request import Request

from pharmaverse.worlds.client import WorldLabsClient
from pharmaverse.worlds.pipeline import generate_one
from pharmaverse.worlds.recipe import load_recipe, plan_jobs

RECIPE = Path(__file__).resolve().parents[1] / "config" / "marble" / "packaging_suite_v1.yaml"


def test_generate_one_writes_metadata(tmp_path: Path) -> None:
    job = plan_jobs(load_recipe(RECIPE), mode="primary")[0]

    def opener(req: Request) -> tuple[int, bytes]:
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
            return 200, json.dumps(
                {
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
            ).encode()
        if method == "POST" and url.endswith("/worlds/world-1:export"):
            return 200, json.dumps(
                {
                    "operation_id": "op-ply",
                    "done": True,
                    "response": {"url": "https://example.com/world.ply"},
                }
            ).encode()
        raise AssertionError((method, url))

    record = generate_one(
        WorldLabsClient("test-key", opener=opener),
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
