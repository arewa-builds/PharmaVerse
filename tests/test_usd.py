from __future__ import annotations

import math
from pathlib import Path

from pharmaverse.usd.cli import main
from pharmaverse.usd.compose import attach_marble, compose_usda, focal_length_mm, load_yaml, write_environment
from pharmaverse.usd.convert import ConversionError, ply_to_usdz, threedgrut_available

ROOT = Path(__file__).resolve().parents[1]


def _configs():
    return (
        load_yaml(ROOT / "config" / "taxonomy.yaml"),
        load_yaml(ROOT / "config" / "cameras.yaml"),
        load_yaml(ROOT / "config" / "usd" / "environment_v1.yaml"),
    )


def test_focal_length_matches_horizontal_fov() -> None:
    focal = focal_length_mm(70)
    assert math.isclose(2 * math.atan((20.955 / 2) / focal), math.radians(70), rel_tol=1e-6)


def test_clear_stage_has_required_prims_and_hidden_residuals() -> None:
    taxonomy, cameras, layout = _configs()
    usda = compose_usda(taxonomy=taxonomy, cameras=cameras, layout=layout)
    for path in (
        'def Xform "World"',
        'def Xform "Marble"',
        'def Xform "Splat"',
        'def Xform "Collider"',
        'def Cube "GroundPlane"',
        'def Xform "Equipment"',
        'def Cube "Conveyor"',
        'def Cube "PackagingStation"',
        'def Xform "Zones"',
        'def Cube "packaging_station_01"',
        'def Cube "conveyor_exit"',
        'def Xform "Residuals"',
        'def Cube "Bottle"',
        'def Cube "Carton"',
        'def Camera "cam_overhead"',
        'def Camera "cam_angled"',
        'pending_nurec_conversion',
        'pharmaverse:expectedState = "CLEAR"',
    ):
        assert path in usda
    assert usda.count('token visibility = "invisible"') >= 10
    assert "semanticData = \"bottle\"" in usda
    assert "float focalLength =" in usda
    assert usda.count("{") == usda.count("}")


def test_sample_discrepancy_shows_only_carton() -> None:
    taxonomy, cameras, layout = _configs()
    usda = compose_usda(
        taxonomy=taxonomy,
        cameras=cameras,
        layout=layout,
        sample_discrepancy="carton",
    )
    start = usda.index('def Cube "Carton"')
    end = usda.index('def Cube "', start + 10)
    carton = usda[start:end]
    assert 'token visibility = "inherited"' in carton
    assert 'pharmaverse:expectedState = "DISCREPANCY"' in usda


def test_write_environment_and_cli(tmp_path: Path) -> None:
    output = tmp_path / "environment_v1.usda"
    write_environment(
        output,
        taxonomy_path=ROOT / "config" / "taxonomy.yaml",
        cameras_path=ROOT / "config" / "cameras.yaml",
        layout_path=ROOT / "config" / "usd" / "environment_v1.yaml",
    )
    assert output.is_file()
    assert output.with_suffix(".manifest.json").is_file()
    code = main(["compose", "--output", str(tmp_path / "from_cli.usda")])
    assert code == 0
    assert (tmp_path / "from_cli.usda").is_file()


def test_attach_stamps_live_marble_metadata(tmp_path: Path) -> None:
    metadata = ROOT / "worlds" / "marble" / "metadata" / "packaging_suite_v1__primary__seed1.json"
    output = tmp_path / "environment_v1.usda"
    attach_marble(
        output,
        metadata_path=metadata,
        taxonomy_path=ROOT / "config" / "taxonomy.yaml",
        cameras_path=ROOT / "config" / "cameras.yaml",
        layout_path=ROOT / "config" / "usd" / "environment_v1.yaml",
    )
    text = output.read_text(encoding="utf-8")
    assert "850b4709-cabf-4643-8bf6-5cc187e85fa4" in text
    assert "pending_nurec_conversion" in text
    assert "1.66379" in text
    manifest = output.with_suffix(".manifest.json").read_text(encoding="utf-8")
    assert "850b4709-cabf-4643-8bf6-5cc187e85fa4" in manifest


def test_convert_without_threedgrut(tmp_path: Path) -> None:
    ply = tmp_path / "missing.ply"
    ply.write_bytes(b"ply")
    if threedgrut_available():
        return
    try:
        ply_to_usdz(ply, tmp_path / "out.usdz")
        raise AssertionError("expected ConversionError")
    except ConversionError as exc:
        assert "3DGRUT" in str(exc)
