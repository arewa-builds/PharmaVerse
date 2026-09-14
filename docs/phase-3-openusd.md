# Phase 3: OpenUSD conversion and Environment V1

Phase 3 turns a Marble world into a **simulation-ready OpenUSD stage**. Isaac Sim (Phase 4) still adds Replicator writers and runtime physics tuning. This phase owns hierarchy, semantics, cameras, zones, and the NuRec conversion slot.

## What this phase produces

| Artifact | Location |
| --- | --- |
| Stage layout | `config/usd/environment_v1.yaml` |
| Environment V1 ASCII USD | `worlds/usd/environment_v1/environment_v1.usda` |
| Manifest | `worlds/usd/environment_v1/environment_v1.manifest.json` |
| Composer / converter | `src/pharmaverse/usd/` |

The stage matches the Phase 1 contract:

```text
/World
  /World/Marble/Splat          # NuRec USDZ reference when a PLY has been converted
  /World/Marble/Collider       # GLB path + X=-90° + PhysicsCollisionAPI
  /World/GroundPlane
  /World/Lights
  /World/Equipment             # conveyor, packaging station, inspection, staging
  /World/Zones                 # invisible guide volumes
  /World/Residuals             # 10 spawnable classes, CLEAR = invisible
  /World/Cameras/cam_overhead
  /World/Cameras/cam_angled
```

Default expected state is **CLEAR**. Prototype residuals are cubes sized from `config/taxonomy.yaml`. They are stand-ins until better meshes exist; they are **not** baked Marble splat bottles.

## Commands

```bash
python -m pip install -e ".[dev]"

# Compose Environment V1 (no GPU required)
python -m pharmaverse.usd compose

# Optional: one visible carton for a REVIEW REQUIRED screenshot
python -m pharmaverse.usd compose --sample-discrepancy carton --output worlds/usd/environment_v1/discrepancy_carton.usda

# When a Phase 2 PLY exists and 3DGRUT is installed (NVIDIA GPU)
python -m pharmaverse.usd convert --ply worlds/marble/exports/JOB/splats_full_res.ply --usdz worlds/usd/environment_v1/marble/splats.usdz
python -m pharmaverse.usd compose --splat-usdz worlds/usd/environment_v1/marble/splats.usdz --collider-glb worlds/marble/exports/JOB/collider.glb --marble-metadata worlds/marble/metadata/JOB.json
```

## Marble → USD (NuRec)

NVIDIA’s documented path:

```text
python -m threedgrut.export.scripts.ply_to_usd scene.ply --output_file scene.usdz
```

Then parent the collider under the Gaussian volume, rotate it **X = −90°**, scale with `semantics_metadata.metric_scale_factor`, and subtract `ground_plane_offset` from Y. The composer writes those transforms on `/World/Marble`.

This environment has **no NVIDIA GPU and no 3DGRUT**, so live PLY→USDZ conversion is not executed here. The Splat prim is marked `pending_nurec_conversion` until a USDZ is passed in.

## Open in Isaac Sim (Phase 4)

1. Open `environment_v1.usda`.
2. If a USDZ was attached, align the splat to the ground plane using the 1 m reference cube.
3. Import the collider GLB under `/World/Marble/Collider` if the asset converter did not already load `pharmaverse:colliderGltf`.
4. Enable the PhysX collision mesh, hide collider rendering, confirm residual cubes rest on the conveyor.

## Coordinate note

Marble/OpenCV: **+x left, +y down, +z forward**. Isaac / OpenUSD V1: **Y-up**. Do not treat splat-baked bottles as detection targets.
