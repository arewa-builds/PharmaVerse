from __future__ import annotations

import json
from urllib.request import Request

from pharmaverse.worlds.client import WorldLabsClient, unwrap_world


def test_unwrap_world_accepts_wrapped_and_id_fields() -> None:
    wrapped = unwrap_world({"world": {"id": "abc", "display_name": "x"}})
    assert wrapped["world_id"] == "abc"
    direct = unwrap_world({"world_id": "def", "display_name": "y"})
    assert direct["world_id"] == "def"


def test_generate_and_poll(tmp_path) -> None:  # noqa: ARG001
    calls: list[tuple[str, str]] = []

    def opener(req: Request) -> tuple[int, bytes]:
        calls.append((req.get_method(), req.full_url))
        if req.full_url.endswith("/worlds:generate"):
            return 200, json.dumps({"operation_id": "op-1", "done": False}).encode()
        if req.full_url.endswith("/operations/op-1"):
            return 200, json.dumps(
                {
                    "operation_id": "op-1",
                    "done": True,
                    "error": None,
                    "metadata": {"world_id": "w-1"},
                    "response": {"id": "w-1"},
                }
            ).encode()
        raise AssertionError(req.full_url)

    client = WorldLabsClient("test-key", opener=opener)
    started = client.generate_world(
        {
            "display_name": "test",
            "model": "marble-1.1",
            "world_prompt": {"type": "text", "text_prompt": "A room"},
        }
    )
    done = client.poll_operation("op-1", interval_s=0, sleep=lambda _s: None)
    assert started["operation_id"] == "op-1"
    assert unwrap_world(done["response"])["world_id"] == "w-1"
    assert ("POST", "https://api.worldlabs.ai/marble/v1/worlds:generate") in calls
