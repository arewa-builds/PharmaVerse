# Marble world outputs

Generated World Labs worlds for PharmaVerse live here.

```text
worlds/marble/
  prompts/                 # human-readable copies of recipe prompts
  metadata/
    planned_jobs.json      # dry-run / planned generate requests
    <job_id>.json          # per-world provenance after a live run
    index.json             # written after a live batch
  exports/                 # gitignored binaries (PLY, GLB, pano)
    <job_id>/
```

Create worlds with:

```bash
python -m pharmaverse.worlds generate --mode primary
```

See [`docs/phase-2-world-generation.md`](../../docs/phase-2-world-generation.md).
