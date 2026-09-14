"""Isaac Sim scene contract and USDA verification for Phase 4."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "config" / "sim" / "isaac_v1.yaml"

REQUIRED_MARKERS = (
    'def Xform "World"',
    'def Xform "Marble"',
    'def Xform "Splat"',
    'def Xform "Collider"',
    'def Cube "GroundPlane"',
    'def Cube "ReferenceMeterCube"',
    'def Xform "Residuals"',
    'def Cube "Carton"',
    'def Camera "cam_overhead"',
    'def Camera "cam_angled"',
    "PhysicsCollisionAPI",
    "PhysicsRigidBodyAPI",
    "rotateXYZ = (-90, 0, 0)",
)


def load_sim_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path else DEFAULT_CONFIG
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{config_path} must contain a mapping")
    return data


def checklist_items(config: dict[str, Any] | None = None) -> list[dict[str, str]]:
    cfg = config or load_sim_config()
    return list(cfg.get("checklist") or [])


def isaac_available() -> bool:
    try:
        import isaacsim  # noqa: F401
        return True
    except ImportError:
        try:
            import omni.usd  # noqa: F401
            return True
        except ImportError:
            return False


def verify_usda(text: str, *, world_id: str | None = None) -> list[dict[str, Any]]:
    """Static checks that do not require Isaac Sim."""
    results: list[dict[str, Any]] = []
    for marker in REQUIRED_MARKERS:
        results.append(
            {
                "id": f"marker:{marker}",
                "ok": marker in text,
                "detail": marker,
            }
        )
    results.append(
        {
            "id": "clear_or_discrepancy",
            "ok": 'pharmaverse:expectedState = "CLEAR"' in text
            or 'pharmaverse:expectedState = "DISCREPANCY"' in text,
            "detail": "expectedState authored",
        }
    )
    if world_id:
        results.append(
            {
                "id": "world_id",
                "ok": world_id in text,
                "detail": world_id,
            }
        )
    results.append(
        {
            "id": "balanced_braces",
            "ok": text.count("{") == text.count("}"),
            "detail": f"opens={text.count('{')} closes={text.count('}')}",
        }
    )
    return results


def verify_stage_file(path: str | Path, *, world_id: str | None = None) -> dict[str, Any]:
    stage = Path(path)
    text = stage.read_text(encoding="utf-8") if stage.is_file() else ""
    checks = verify_usda(text, world_id=world_id) if text else [
        {"id": "stage_exists", "ok": False, "detail": str(stage)}
    ]
    if text:
        checks.insert(0, {"id": "stage_exists", "ok": True, "detail": str(stage)})
    return {
        "path": str(stage),
        "ok": all(item["ok"] for item in checks),
        "isaac_available": isaac_available(),
        "checks": checks,
    }
