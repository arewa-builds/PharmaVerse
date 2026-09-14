from __future__ import annotations

import json
from pathlib import Path

from pharmaverse.worlds.cli import main

RECIPE = Path(__file__).resolve().parents[1] / "config" / "marble" / "packaging_suite_v1.yaml"


def test_dry_run_writes_plan(tmp_path, capsys) -> None:
    code = main(
        [
            "generate",
            "--recipe",
            str(RECIPE),
            "--output",
            str(tmp_path),
            "--mode",
            "variants",
            "--dry-run",
        ]
    )
    assert code == 0
    plan_path = tmp_path / "metadata" / "planned_jobs.json"
    payload = json.loads(plan_path.read_text(encoding="utf-8"))
    assert payload["mode"] == "variants"
    assert len(payload["jobs"]) == 4
    printed = json.loads(capsys.readouterr().out)
    assert printed["jobs"][0]["generate_request"]["model"] == "marble-1.1"


def test_missing_key_fails_live_generate(monkeypatch) -> None:
    monkeypatch.delenv("WLT_API_KEY", raising=False)
    code = main(["generate", "--recipe", str(RECIPE), "--mode", "primary"])
    assert code == 2


def test_missing_key_fails_ingest(monkeypatch) -> None:
    monkeypatch.delenv("WLT_API_KEY", raising=False)
    code = main(["ingest", "--world-id", "world-1"])
    assert code == 2
