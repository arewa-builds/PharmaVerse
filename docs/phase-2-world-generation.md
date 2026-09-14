# Phase 2: World Labs Marble world generation

Phase 2 turns the frozen `packaging_suite_v1` recipe into Marble worlds, then exports Gaussian splats and collider meshes for OpenUSD / Isaac Sim (Phase 3).

Marble generates appearance and layout. It does **not** produce the spawnable residuals used for line clearance. Those are USD assets added in Isaac Sim.

## What this phase produces

For each generated world:

| Artifact | Location |
| --- | --- |
| Generation recipe | `config/marble/packaging_suite_v1.yaml` |
| Planned jobs | `worlds/marble/metadata/planned_jobs.json` |
| World metadata (`world_id`, model, seed, prompt, asset URLs, metric scale) | `worlds/marble/metadata/<job_id>.json` |
| Full-res PLY splat | `worlds/marble/exports/<job_id>/splats_full_res.ply` |
| Collider mesh | `worlds/marble/exports/<job_id>/collider.glb` |
| Panorama / thumbnail | `worlds/marble/exports/<job_id>/pano.png`, `thumbnail.jpg` |

Large binaries are gitignored. Metadata is the durable record.

## Prerequisites

1. A World Labs account at [platform.worldlabs.ai](https://platform.worldlabs.ai/).
2. **World API credits** purchased on that platform. Credits bought in the Marble web app **cannot** be used with the API.
3. An API key in `.env` as `WLT_API_KEY`. That value is sent as the `WLT-Api-Key` HTTP header. There is no second env var.

```bash
cp .env.example .env
# set WLT_API_KEY=...
```

`marble-1.1` world generation is billed as a world-generation usage event (currently 1,500 credits per standard generation). Draft (`marble-1.0-draft`) is much cheaper and is for prompt iteration only.

## Commands

```bash
python -m pip install -e ".[dev]"

# Inspect the exact generate payloads (no API calls)
python -m pharmaverse.worlds generate --mode primary --dry-run
python -m pharmaverse.worlds generate --mode variants --dry-run

# Check API credits
python -m pharmaverse.worlds credits

# Cheap prompt iteration
python -m pharmaverse.worlds generate --mode primary --draft

# Phase 2 keeper: one packaging suite, marble-1.1, seed 1
python -m pharmaverse.worlds generate --mode primary

# Small family (primary + 3 lighting/layout variants, seed 1)
python -m pharmaverse.worlds generate --mode variants

# Phase 6 scale: all prompts × all seeds
python -m pharmaverse.worlds generate --mode family
```

Generation is asynchronous. The client polls `/marble/v1/operations/{id}` until Marble reports `done` (typically several minutes), then:

1. `GET /marble/v1/worlds/{world_id}`
2. `POST /marble/v1/worlds/{world_id}:export` for a full-res PLY
3. Download collider GLB from `assets.mesh.collider_mesh_url`
4. Persist metadata, including `semantics_metadata.metric_scale_factor` and `ground_plane_offset` for Phase 3 metric alignment

Open a finished world in Marble at `https://marble.worldlabs.ai/world/{world_id}`.

## Coordinate note for Phase 3

Marble assets are in an OpenCV-style frame (**+x left, +y down, +z forward**). Convert before Isaac Sim. NVIDIA’s Marble tutorial rotates the collider by X = −90° and converts the PLY through 3DGRUT / NuRec:

```text
python -m threedgrut.export.scripts.ply_to_usd scene.ply --output_file scene.usdz
```

Do not treat bottles or cartons baked into the splat as line-clearance objects.

## Status in this environment

This cloud agent did not have `WLT_API_KEY` or World API credits, so live Marble generation was not executed here. The recipe, client, CLI, tests, and dry-run plan are in the repo. Setting the key and running `python -m pharmaverse.worlds generate --mode primary` is the remaining live step.
