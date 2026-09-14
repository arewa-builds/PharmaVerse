"""Compose PharmaVerse Environment V1 as OpenUSD ASCII."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import yaml

from pharmaverse.usd.convert import ConversionError, ply_to_usdz
from pharmaverse.usd.usda import fmt_vec, semantic_block, xform_ops
from pharmaverse.worlds.pipeline import repo_relative, resolve_recorded_path

ROOT = Path(__file__).resolve().parents[3]
HORIZONTAL_APERTURE_MM = 20.955


def _existing_asset(raw: str | Path | None) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if path.is_file():
        return path
    rooted = ROOT / path
    if rooted.is_file():
        return rooted
    resolved = resolve_recorded_path(str(raw))
    if resolved is not None and resolved.is_file():
        return resolved
    return None


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def focal_length_mm(horizontal_fov_deg: float, aperture_mm: float = HORIZONTAL_APERTURE_MM) -> float:
    return aperture_mm / (2.0 * math.tan(math.radians(horizontal_fov_deg) / 2.0))


def marble_overrides(metadata_path: str | Path | None) -> dict[str, Any]:
    if not metadata_path:
        return {}
    payload = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
    assets = payload.get("assets") or {}
    semantics = assets.get("semantics_metadata") or {}
    local = payload.get("local_files") or {}
    ply = resolve_recorded_path(local.get("ply"))
    collider = resolve_recorded_path(local.get("collider"))
    return {
        "world_id": payload.get("world_id"),
        "metric_scale_factor": semantics.get("metric_scale_factor"),
        "ground_plane_offset": semantics.get("ground_plane_offset"),
        "ply_path": repo_relative(ply) if ply else local.get("ply"),
        "collider_path": repo_relative(collider) if collider else local.get("collider"),
        "marble_url": (payload.get("world") or {}).get("marble_url"),
        "model": (payload.get("world") or {}).get("model"),
    }


def _cube(
    name: str,
    *,
    translate,
    scale,
    semantic: str | None = None,
    color=None,
    indent: str = "    ",
    extra_apis: list[str] | None = None,
    extra_body: list[str] | None = None,
    visibility: str | None = None,
    purpose: str | None = None,
) -> str:
    inner = indent + "    "
    apis = list(extra_apis or [])
    if semantic:
        apis.insert(0, "SemanticsAPI:Semantics")
    if apis:
        joined = ", ".join(f'"{item}"' for item in apis)
        lines = [
            f'{indent}def Cube "{name}" (',
            f"{indent}    prepend apiSchemas = [{joined}]",
            f"{indent})",
            f"{indent}{{",
        ]
    else:
        lines = [f'{indent}def Cube "{name}"', f"{indent}{{"]
    if semantic:
        lines.append(semantic_block(semantic, inner))
    lines.append(f"{inner}double size = 1")
    if color is not None:
        lines.append(f"{inner}color3f[] primvars:displayColor = [{fmt_vec(color)}]")
    if visibility:
        lines.append(f'{inner}token visibility = "{visibility}"')
    if purpose:
        lines.append(f'{inner}uniform token purpose = "{purpose}"')
    xf = xform_ops(translate=translate, scale=scale, indent=inner)
    if xf:
        lines.append(xf)
    if extra_body:
        lines.extend(f"{inner}{line}" for line in extra_body)
    lines.append(f"{indent}}}")
    return "\n".join(lines)


def compose_usda(
    *,
    taxonomy: dict[str, Any],
    cameras: dict[str, Any],
    layout: dict[str, Any],
    marble: dict[str, Any] | None = None,
    splat_relpath: str | None = None,
    collider_relpath: str | None = None,
    enable_residuals: bool = False,
    sample_discrepancy: str | None = None,
) -> str:
    marble = marble or {}
    marble_cfg = layout.get("marble") or {}
    scale = float(marble.get("metric_scale_factor") or marble_cfg.get("metric_scale_factor") or 1.0)
    ground_offset = float(
        marble.get("ground_plane_offset")
        if marble.get("ground_plane_offset") is not None
        else marble_cfg.get("ground_plane_offset") or 0.0
    )
    collider_rot = marble_cfg.get("collider_rotate_xyz_deg") or [-90.0, 0.0, 0.0]
    world_id = marble.get("world_id") or ""

    cam_by_id = {item["id"]: item for item in cameras.get("cameras") or []}
    cam_defaults = cameras.get("defaults") or {}
    clip = cam_defaults.get("clipping_range_m") or [0.05, 20.0]

    residual_visibility = "inherited" if enable_residuals else "invisible"
    spawn = layout.get("residual_spawns") or {}

    chunks: list[str] = [
        "#usda 1.0",
        "(",
        '    defaultPrim = "World"',
        f"    metersPerUnit = {float(layout.get('meters_per_unit', 1))}",
        f'    upAxis = "{layout.get("up_axis", "Y")}"',
        '    doc = "PharmaVerse Environment V1 — OpenUSD packaging cell for line-clearance simulation"',
        ")",
        "",
        'def Xform "World"',
        "{",
        '    custom string pharmaverse:stageId = "environment_v1"',
        '    custom string pharmaverse:experiment = "line_clearance_01"',
        f'    custom string pharmaverse:expectedState = "{"DISCREPANCY" if sample_discrepancy or enable_residuals else "CLEAR"}"',
        "",
        '    def Xform "Marble"',
        "    {",
        f'        custom string pharmaverse:worldId = "{world_id}"',
        f"        custom double pharmaverse:metricScaleFactor = {scale:.6g}",
        f"        custom double pharmaverse:groundPlaneOffset = {ground_offset:.6g}",
        '        custom string pharmaverse:coordinateNote = "Marble OpenCV (+x left, +y down, +z forward). Collider rotateXYZ -90 X for Isaac Sim."',
        xform_ops(
            translate=[0.0, -ground_offset, 0.0],
            scale=[scale, scale, scale],
            indent="        ",
            order=["xformOp:scale", "xformOp:translate"],
        ),
    ]

    if splat_relpath:
        chunks.extend(
            [
                '        def Xform "Splat" (',
                f"            prepend references = @{splat_relpath}@",
                "        )",
                "        {",
                '            custom string pharmaverse:role = "gaussian_splat"',
                "        }",
            ]
        )
    else:
        chunks.extend(
            [
                '        def Xform "Splat"',
                "        {",
                '            custom string pharmaverse:role = "gaussian_splat"',
                '            custom string pharmaverse:status = "pending_nurec_conversion"',
                "        }",
            ]
        )

    collider_header = '        def Xform "Collider"'
    if collider_relpath:
        chunks.extend(
            [
                '        def Xform "Collider" (',
                f'            prepend apiSchemas = ["PhysicsCollisionAPI"]',
                "        )",
                "        {",
                f'            custom asset pharmaverse:colliderGltf = @{collider_relpath}@',
            ]
        )
    else:
        chunks.extend(
            [
                f"{collider_header} (",
                '            prepend apiSchemas = ["PhysicsCollisionAPI"]',
                "        )",
                "        {",
                '            custom string pharmaverse:status = "pending_collider_mesh"',
            ]
        )
    chunks.extend(
        [
            '            custom string pharmaverse:role = "collider"',
            "            bool physics:collisionEnabled = 1",
            '            token visibility = "invisible"',
            xform_ops(rotate_xyz_deg=collider_rot, indent="            "),
            "        }",
            "    }",
            "",
        ]
    )

    ground = layout["ground"]
    chunks.append(
        _cube(
            "GroundPlane",
            translate=ground["translate"],
            scale=ground["scale"],
            semantic="floor",
            color=[0.34, 0.35, 0.38],
            extra_apis=["PhysicsCollisionAPI"],
            extra_body=["bool physics:collisionEnabled = 1"],
        )
    )
    chunks.append("")

    cube = layout["reference_cube"]
    chunks.append(
        _cube(
            "ReferenceMeterCube",
            translate=cube["translate"],
            scale=cube["scale"],
            color=[0.9, 0.2, 0.2],
        )
    )
    chunks.append("")

    chunks.append('    def Xform "Lights"')
    chunks.append("    {")
    dome = layout["lights"]["dome"]
    distant = layout["lights"]["distant"]
    chunks.extend(
        [
            '        def DomeLight "Sky"',
            "        {",
            f"            float inputs:intensity = {float(dome['intensity']):.6g}",
            f"            color3f inputs:color = {fmt_vec(dome['color'])}",
            "        }",
            '        def DistantLight "Key"',
            "        {",
            f"            float inputs:intensity = {float(distant['intensity']):.6g}",
            xform_ops(rotate_xyz_deg=distant["rotate_xyz_deg"], indent="            "),
            "        }",
            "    }",
            "",
            '    def Xform "Equipment"',
            "    {",
        ]
    )
    for item in layout.get("equipment") or []:
        chunks.append(
            _cube(
                item["name"],
                translate=item["translate"],
                scale=item["scale"],
                semantic=item["semantic"],
                color=item.get("display_color"),
                extra_apis=["PhysicsCollisionAPI"],
                extra_body=["bool physics:collisionEnabled = 1"],
                indent="        ",
            )
        )
        chunks.append("")
    chunks.append("    }")
    chunks.append("")
    chunks.append('    def Xform "Zones"')
    chunks.append("    {")
    zone_lookup = {zone["id"]: zone for zone in taxonomy.get("zones") or []}
    for zone_id, pose in (layout.get("zones") or {}).items():
        meta = zone_lookup.get(zone_id) or {"display_name": zone_id}
        chunks.extend(
            [
                _cube(
                    zone_id,
                    translate=pose["translate"],
                    scale=pose["scale"],
                    color=[0.2, 0.6, 0.9],
                    extra_body=[
                        f'custom string pharmaverse:displayName = "{meta.get("display_name", zone_id)}"',
                        'custom string pharmaverse:expectedStateWhenClear = "empty_of_detection_classes"',
                    ],
                    visibility="invisible",
                    purpose="guide",
                    indent="        ",
                ),
                "",
            ]
        )
    chunks.append("    }")
    chunks.append("")
    chunks.append('    def Xform "Residuals"')
    chunks.append("    {")
    chunks.append('        custom string pharmaverse:role = "spawnable_detection_targets"')
    for cls in taxonomy.get("detection_classes") or []:
        name = cls["name"]
        size = cls.get("typical_size_m") or [0.05, 0.05, 0.05]
        visible = residual_visibility
        if sample_discrepancy:
            visible = "inherited" if name == sample_discrepancy else "invisible"
        translate = spawn.get(name) or [0.0, 1.0, 0.0]
        prim_name = "".join(part.title() for part in name.split("_"))
        chunks.append(
            _cube(
                prim_name,
                translate=translate,
                scale=size,
                semantic=cls["usd_semantic"],
                extra_apis=["PhysicsCollisionAPI", "PhysicsRigidBodyAPI"],
                extra_body=[
                    "bool physics:collisionEnabled = 1",
                    "bool physics:rigidBodyEnabled = 1",
                    f"custom int pharmaverse:classId = {int(cls['id'])}",
                    f"custom int pharmaverse:cocoId = {int(cls['coco_id'])}",
                ],
                visibility=visible,
                indent="        ",
            )
        )
        chunks.append("")
    chunks.append("    }")
    chunks.append("")
    chunks.append('    def Xform "Cameras"')
    chunks.append("    {")
    cam_layout = layout.get("cameras") or {}
    for cam_id, pose in cam_layout.items():
        spec = cam_by_id.get(cam_id) or {}
        fov = float(spec.get("horizontal_fov_deg") or 70)
        resolution = spec.get("resolution") or cam_defaults.get("resolution") or [1920, 1080]
        chunks.extend(
            [
                f'        def Camera "{cam_id}"',
                "        {",
                f'            custom string pharmaverse:displayName = "{spec.get("display_name", cam_id)}"',
                f'            custom string pharmaverse:role = "{spec.get("role", "")}"',
                f'            custom string pharmaverse:targetZone = "{spec.get("target_zone", "")}"',
                f"            custom int[] pharmaverse:resolution = [{int(resolution[0])}, {int(resolution[1])}]",
                '            token projection = "perspective"',
                f"            float focalLength = {focal_length_mm(fov):.6g}",
                f"            float horizontalAperture = {HORIZONTAL_APERTURE_MM}",
                f"            float2 clippingRange = {fmt_vec(clip)}",
                xform_ops(
                    translate=pose["translate"],
                    rotate_xyz_deg=pose["rotate_xyz_deg"],
                    indent="            ",
                ),
                "        }",
                "",
            ]
        )
    chunks.append("    }")
    chunks.append("}")
    chunks.append("")
    return "\n".join(chunks)


def write_environment(
    output: Path,
    *,
    taxonomy_path: Path,
    cameras_path: Path,
    layout_path: Path,
    metadata_path: Path | None = None,
    splat_usdz: Path | None = None,
    collider_glb: Path | None = None,
    enable_residuals: bool = False,
    sample_discrepancy: str | None = None,
) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    marble = marble_overrides(metadata_path) if metadata_path else {}
    if splat_usdz is None:
        default_usdz = output.parent / "marble" / "splats.usdz"
        if default_usdz.is_file():
            splat_usdz = default_usdz
    if collider_glb is None:
        collider_glb = _existing_asset(marble.get("collider_path"))
    splat_rel = None
    collider_rel = None
    if splat_usdz:
        splat_usdz = Path(splat_usdz)
        dest = output.parent / "marble" / splat_usdz.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if splat_usdz.is_file() and splat_usdz.resolve() != dest.resolve():
            dest.write_bytes(splat_usdz.read_bytes())
        if dest.is_file() or splat_usdz.is_file():
            splat_rel = f"./marble/{dest.name}"
    if collider_glb:
        collider_glb = Path(collider_glb)
        dest = output.parent / "marble" / collider_glb.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if collider_glb.is_file() and collider_glb.resolve() != dest.resolve():
            dest.write_bytes(collider_glb.read_bytes())
        if dest.is_file() or collider_glb.is_file():
            collider_rel = f"./marble/{dest.name}"
    usda = compose_usda(
        taxonomy=load_yaml(taxonomy_path),
        cameras=load_yaml(cameras_path),
        layout=load_yaml(layout_path),
        marble=marble,
        splat_relpath=splat_rel,
        collider_relpath=collider_rel,
        enable_residuals=enable_residuals,
        sample_discrepancy=sample_discrepancy,
    )
    output.write_text(usda, encoding="utf-8")
    try:
        stage_path = str(output.resolve().relative_to(ROOT))
    except ValueError:
        stage_path = str(output)
    manifest = {
        "stage": stage_path,
        "expected_state": "DISCREPANCY" if sample_discrepancy or enable_residuals else "CLEAR",
        "marble": marble,
        "splat": splat_rel,
        "collider": collider_rel,
        "prims": {
            "world": "/World",
            "marble": "/World/Marble",
            "ground": "/World/GroundPlane",
            "zones": "/World/Zones",
            "residuals": "/World/Residuals",
            "cameras": ["/World/Cameras/cam_overhead", "/World/Cameras/cam_angled"],
        },
    }
    output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output


def attach_marble(
    output: Path,
    *,
    metadata_path: Path,
    taxonomy_path: Path,
    cameras_path: Path,
    layout_path: Path,
    splat_usdz: Path | None = None,
    collider_glb: Path | None = None,
    convert: bool = False,
    sample_discrepancy: str | None = None,
) -> Path:
    """Compose Environment V1 from a recorded Marble world, converting PLY if asked."""
    marble = marble_overrides(metadata_path)
    if convert:
        ply = _existing_asset(marble.get("ply_path"))
        if ply is None:
            raise ConversionError(
                "PLY is not on disk. Run ingest/generate on the machine that has "
                f"the export, or pass an existing file. Looked for: {marble.get('ply_path')}"
            )
        dest = output.parent / "marble" / "splats.usdz"
        splat_usdz = ply_to_usdz(ply, dest)
    return write_environment(
        output,
        taxonomy_path=taxonomy_path,
        cameras_path=cameras_path,
        layout_path=layout_path,
        metadata_path=metadata_path,
        splat_usdz=splat_usdz,
        collider_glb=collider_glb,
        sample_discrepancy=sample_discrepancy,
    )
