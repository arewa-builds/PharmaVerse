# PharmaVerse GPU-day run sheet (Phase 4)

**Goal:** One Launchable session. Convert the Marble 1.1 keeper, attach Environment V1, prove the carton rests on the conveyor. Then **stop the instance**. Do not capture the 8k dataset. Do not add a robot.

**Blocked until:** GPU billing account is live.

## Account

| | Fill in before the session |
| --- | --- |
| Payer account | _GPU billing account (separate from personal)_ |
| NVIDIA Brev login | |
| Spend cap this session | $______ |
| Who may **start** the instance | |
| Who may **stop** the instance | |
| Idle rule | **Stop as soon as Play-mode proof is done, or if idle > 15 min** |

Isaac Sim software is free. You pay Brev GPU hours. Stopped VMs can still incur a small disk charge.

## Assets (already protected)

| | |
| --- | --- |
| World | https://marble.worldlabs.ai/world/850b4709-cabf-4643-8bf6-5cc187e85fa4 |
| `world_id` | `850b4709-cabf-4643-8bf6-5cc187e85fa4` |
| Model | `marble-1.1` |
| Job | `packaging_suite_v1__primary__seed1` |
| PLY / GLB backup | _not only OneDrive — path: _____________ |
| `WLT_API_KEY` | password manager of the **GPU** account |

Git does not store the PLY/GLB. Bottles/cartons in the Marble view are **background**, not detection targets.

## Start (Launchable)

1. Open https://brev.nvidia.com/launchable/deploy/now?launchableID=env-35JP2ywERLgqtD0b0MIeK1HnF46
2. Deploy. GPU must have **RT cores / NVENC** (RTX, L4, L40, A10-class). **Not A100.**
3. Wait until running + setup finished.
4. Secure Links → VS Code in the browser.
5. `nvidia-smi` must show a GPU.

## Day-one sequence

```bash
cd ~
git clone https://github.com/arewa-builds/PharmaVerse.git
cd PharmaVerse
python3 -m pip install -e ".[dev]"
```

**Get PLY + GLB** (one of):

- Ingest: put `WLT_API_KEY` in `.env`, then  
  `python3 -m pharmaverse.worlds ingest --world-id 850b4709-cabf-4643-8bf6-5cc187e85fa4 --as-primary`
- Or upload `splats_full_res.ply` and `collider.glb` into  
  `worlds/marble/exports/packaging_suite_v1__primary__seed1/`

**Convert + attach**

```bash
# 3DGRUT env, then:
python -m pharmaverse.usd convert
python -m pharmaverse.usd attach
python -m pharmaverse.sim spawn --class carton
python -m pharmaverse.sim verify
```

**Isaac UI**

```bash
/isaac-sim/runheadless.sh
```

Wait for `app ready`. Open the same host with `/viewer` (one viewer tab only).

File → Open  
`…/worlds/usd/environment_v1/environment_v1.usda`  
then the carton stage  
`…/worlds/usd/environment_v1/discrepancy_carton.usda`

Play: carton cube **rests on the conveyor**, does not fall through. Collider under `/World/Marble`, X = −90°, hidden, collision on.

## Done when

- [ ] USDZ exists and is attached
- [ ] CLEAR stage loads (residuals invisible)
- [ ] Carton stage: Play, cube sits on conveyor
- [ ] Both cameras render
- [ ] **Instance stopped**

Then Phase 5 capture is unblocked. Not this session.

## Do not

More `marble-1.1` worlds · taxonomy edits · Atlas · plant-floor/GMP · command center · robot · Replicator 8k frames · treat splat-baked bottles as labels.

## Abort

No GPU / A100 / viewer never ready / carton falls through after collider check → **stop the instance**, do not keep it running to debug overnight.
