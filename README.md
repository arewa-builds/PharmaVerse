# PharmaVerse

Generative world models, digital twins, synthetic data, and Physical AI for pharmaceutical manufacturing.

PharmaVerse is a research prototype for building a **virtual pharmaceutical manufacturing environment**. The goal is to generate labeled synthetic computer vision data, evaluate inspection models, and eventually test Physical AI — without requiring access to a real production line.

**World Labs Marble is a core component**, not an optional environment-generation tool. The system that can be built today is:

**World Labs Marble / World API → OpenUSD → NVIDIA Omniverse / Isaac Sim → synthetic data → computer vision → Sim2Real → Physical AI**

This is a research, simulation, and engineering prototype. It is **not** a validated GMP manufacturing system and does not replace qualified pharmaceutical manufacturing, quality, safety, or regulatory processes.

The full objectives and execution plan live in [`project_description.txt`](./project_description.txt).

**Current phase: 3 — OpenUSD conversion and Environment V1.**  
Phase 1 design: [`docs/system-design.md`](./docs/system-design.md).  
Phase 2 runbook: [`docs/phase-2-world-generation.md`](./docs/phase-2-world-generation.md).  
Phase 3 runbook: [`docs/phase-3-openusd.md`](./docs/phase-3-openusd.md).

---

## Research questions

1. Can World Labs Marble generate pharmaceutical manufacturing worlds that NVIDIA Omniverse and Isaac Sim can turn into simulation-ready environments for synthetic inspection data and Physical AI research?
2. Can computer vision models trained primarily or partially on that synthetic data generalize to real-world imagery (Sim2Real)?

---

## Architecture

PharmaVerse adapts an existing **World Labs → NVIDIA simulation pattern** (documented by World Labs with Lightwheel, and by NVIDIA for Marble → Isaac Sim) to pharmaceutical manufacturing.

```text
World Labs Marble / World API
        ↓
Marble 3D world (Gaussian splats + meshes)
        ↓
OpenUSD conversion / Omniverse NuRec
        ↓
NVIDIA Omniverse + Isaac Sim
  physics, SimReady assets, cameras, sensors, controllable objects
        ↓
Synthetic data
  RGB, boxes, masks, depth, ground truth
        ↓
Computer vision models
        ↓
Sim2Real evaluation
        ↓
Physical AI (later)
```

Marble generates the world. Isaac Sim makes it controllable. PharmaVerse orchestrates the research loop.

A representative Marble prompt:

> A modern pharmaceutical packaging suite with stainless-steel equipment, a packaging conveyor, inspection stations, pharmaceutical bottles, cartons, material staging areas and controlled manufacturing architecture.

---

## Responsibilities

| Platform | Role in PharmaVerse |
| --- | --- |
| **World Labs Marble** | Generate / reconstruct the pharmaceutical world |
| **World API** | Programmatically generate world variations |
| **Marble Chisel** | Control coarse 3D layout |
| **Marble Export** | Gaussian splat and mesh output |
| **Omniverse / OpenUSD** | Structure the simulation environment |
| **Isaac Sim** | Physics, sensors, cameras, robots |
| **Synthetic data tools** | Generate labeled CV datasets |
| **PyTorch / CV models** | Train inspection models |
| **PharmaVerse** | Orchestrate the complete research platform |

Marble is not expected to emit a perfectly engineered production line with exact physics and semantic labels. That work happens in Isaac Sim.

---

## Roadmap

**V1 (build now)**  
World Labs Marble + World API → Omniverse / OpenUSD → Isaac Sim → synthetic data → CV

**Future**  
World Labs Atlas → richer world modeling / simulation → Omniverse / Isaac Sim → Physical AI

Marble is generally available and the World API is public. Atlas is entering early access with select partners, so it is not a V1 dependency.

### First implementation phases

1. Research and architecture — **done** ([`docs/system-design.md`](./docs/system-design.md))
2. **World Labs Marble world generation** — done ([`docs/phase-2-world-generation.md`](./docs/phase-2-world-generation.md))
3. OpenUSD conversion and environment prototype — in progress ([`docs/phase-3-openusd.md`](./docs/phase-3-openusd.md))
4. Isaac Sim integration
5. Synthetic data pipeline
6. Domain randomization
7. Baseline computer vision model
8. Synthetic line-clearance experiment
9. Sim2Real evaluation
10. Inspection command center
11. Physical AI expansion and Atlas adoption

---

## First experiment: synthetic line clearance

A Marble-generated packaging area is configured in Isaac Sim with a known **cleared** state. The simulation then introduces residuals — a previous-product bottle, loose label, carton, tool, or document — with automatic ground truth.

The inspection model compares **expected state vs actual state** and flags discrepancies for human review.

---

## MVP

The first useful demo stays small:

- One packaging suite generated with **Marble**
- That world converted into one OpenUSD / Isaac Sim room
- ~10–20 controllable object types (`Bottle`, `Carton`, `Label`, `Tray`, `Tool`, `Document`)
- Two fixed virtual RGB cameras
- One detection or segmentation model
- 5,000–10,000 automatically labeled synthetic images

Demo loop: cleared station → residual object appears → camera observes it → model flags **REVIEW REQUIRED** → lighting, pose, or occlusion can be changed to see whether detection holds.

---

## Repository status

Phase 3 adds Environment V1 as OpenUSD ASCII. Live NuRec PLY→USDZ conversion needs an NVIDIA GPU and 3DGRUT.

```text
PharmaVerse/
├── docs/phase-3-openusd.md
├── config/usd/environment_v1.yaml
├── src/pharmaverse/usd/
└── worlds/usd/environment_v1/environment_v1.usda
```

### Generate a Marble world

```bash
python -m pip install -e ".[dev]"
cp .env.example .env   # set WLT_API_KEY from https://platform.worldlabs.ai/

python -m pharmaverse.worlds generate --mode primary --dry-run
python -m pharmaverse.worlds generate --mode primary
```

`--mode variants` generates the small packaging-suite family (primary + 3 prompt variants). Details: [`docs/phase-2-world-generation.md`](./docs/phase-2-world-generation.md).

### Compose Environment V1

```bash
python -m pharmaverse.usd compose
```

Opens as `worlds/usd/environment_v1/environment_v1.usda`. Details: [`docs/phase-3-openusd.md`](./docs/phase-3-openusd.md).

Intended later layout:

```text
pharmaverse/
├── worlds/
│   ├── marble/
│   │   ├── prompts/
│   │   ├── exports/
│   │   └── metadata/
│   └── usd/
├── scenes/
├── synthetic_data/
│   ├── images/
│   ├── labels/
│   ├── masks/
│   ├── depth/
│   └── metadata/
├── models/
├── experiments/
└── evaluation/
```

---

## Sources

- [Marble: A Multimodal World Model](https://www.worldlabs.ai/blog/marble-world-model)
- [Marble](https://marble.worldlabs.ai/)
- [World API](https://docs.worldlabs.ai/api)
- [Lightwheel × World Labs case study](https://www.worldlabs.ai/case-studies/2-lightwheel)
- [NVIDIA: Isaac Sim + World Labs Marble](https://developer.nvidia.com/blog/simulate-robotic-environments-faster-with-nvidia-isaac-sim-and-world-labs-marble/)
- [Atlas: A World Model for Spatial Intelligence](https://www.worldlabs.ai/blog/atlas)
