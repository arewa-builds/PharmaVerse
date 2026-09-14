# Phase 4: Isaac Sim integration

Phase 4 opens Environment V1 in **Isaac Sim** and proves hypothesis H1: a Marble packaging-suite world can be a collision-aware scene with spawnable residuals. Replicator dataset capture is Phase 5.

## Where you are

A **marble-1.1** keeper already exists:

| Field | Value |
| --- | --- |
| `world_id` | `850b4709-cabf-4643-8bf6-5cc187e85fa4` |
| Marble URL | https://marble.worldlabs.ai/world/850b4709-cabf-4643-8bf6-5cc187e85fa4 |
| Metadata | `worlds/marble/metadata/packaging_suite_v1__primary__seed1.json` |
| Metric scale | `1.663786…` |
| Ground plane offset | `1.791928…` |

PLY + collider were downloaded on the machine that ran generate. They are gitignored. This cloud checkout does not have an NVIDIA GPU, so 3DGRUT conversion is still a local step.

Check status anytime:

```bash
python -m pharmaverse.worlds status
```

## Next commands (local NVIDIA GPU)

```bash
python -m pip install -e ".[dev]"

# If this checkout does not already have the PLY/GLB:
python -m pharmaverse.worlds ingest --world-id 850b4709-cabf-4643-8bf6-5cc187e85fa4 --as-primary

# Convert Gaussian splat (3DGRUT / NuRec)
python -m pharmaverse.usd convert \
  --ply worlds/marble/exports/packaging_suite_v1__primary__seed1/splats_full_res.ply \
  --usdz worlds/usd/environment_v1/marble/splats.usdz

# Stamp scale, world_id, collider, and USDZ onto Environment V1
python -m pharmaverse.usd attach \
  --metadata worlds/marble/metadata/packaging_suite_v1__primary__seed1.json

# REVIEW REQUIRED screenshot stage (carton only)
python -m pharmaverse.sim spawn --class carton
```

`attach --convert` runs 3DGRUT and compose in one step when 3DGRUT is installed.

## Open in Isaac Sim

1. Install **Isaac Sim 5.1+** (prefer **6.x** once NuRec USDZ import is confirmed).
2. File → Open `worlds/usd/environment_v1/environment_v1.usda`.
3. If the USDZ was unzipped for editing, open the extracted `default.usda` and keep `/World/Marble/Splat` as the Gaussian volume.
4. Align `/World/Marble` to the ground plane using `/World/ReferenceMeterCube` (1 m). Metadata already applies `metric_scale_factor` and subtracts `ground_plane_offset` from Y.
5. Confirm `/World/Marble/Collider` is a child of `/World/Marble`, `rotateXYZ` X = **−90°**, collision enabled, visibility **invisible**.
6. Set the ground plane collision mesh as a matte / shadow receiver (NuRec proxy target) per NVIDIA’s Marble tutorial.
7. Play. Spawn visibility is CLEAR (hidden). Then open `discrepancy_carton.usda` or run `python -m pharmaverse.sim spawn --class carton` and Play again: the carton cube must rest on the conveyor, not fall through.

Do **not** add a robot in this phase. Do **not** treat bottles painted into the splat as line-clearance objects.

## Commands that do not need Isaac

```bash
python -m pharmaverse.sim checklist
python -m pharmaverse.sim verify
python -m pharmaverse.sim bootstrap
```

`verify` checks the USDA contract (prims, collider rotation, cameras, residual APIs). Runtime physics still has to be confirmed in Isaac Sim.

## Exit criteria

Phase 4 is done when all of the following are true on a GPU workstation:

- [ ] Full-res PLY converted to USDZ via 3DGRUT
- [ ] Environment V1 references that USDZ and the collider GLB
- [ ] Stage opens in Isaac Sim 5.1+ / 6.x
- [ ] 1 m cube vs room scale looks human, not dollhouse
- [ ] Hidden collider stops a residual cube
- [ ] CLEAR and carton-discrepancy stages both load
- [ ] Both cameras render

**Next:** Phase 5 — Isaac Sim Replicator writers (~8,000 COCO frames). Do not expand taxonomy before Experiment 01 has numbers.
