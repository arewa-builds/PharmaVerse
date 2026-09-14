from __future__ import annotations

from pathlib import Path

from pharmaverse.sim.cli import main
from pharmaverse.sim.scene import isaac_available, load_sim_config, verify_usda, verify_stage_file

ROOT = Path(__file__).resolve().parents[1]


def test_isaac_not_required_for_static_checks() -> None:
    assert isaac_available() is False
    config = load_sim_config()
    assert config["prims"]["residuals"] == "/World/Residuals"
    assert len(config["checklist"]) >= 8


def test_verify_environment_usda() -> None:
    usda = (ROOT / "worlds" / "usd" / "environment_v1" / "environment_v1.usda").read_text()
    results = verify_usda(usda)
    assert all(item["ok"] for item in results)


def test_verify_cli() -> None:
    code = main(["verify", "--usda", str(ROOT / "worlds" / "usd" / "environment_v1" / "environment_v1.usda")])
    assert code == 0


def test_checklist_cli(capsys) -> None:
    code = main(["checklist"])
    assert code == 0
    assert "open_stage" in capsys.readouterr().out


def test_verify_stage_file_missing(tmp_path: Path) -> None:
    report = verify_stage_file(tmp_path / "missing.usda")
    assert report["ok"] is False
