"""Convert Marble Gaussian splat PLY files to USDZ via NVIDIA 3DGRUT / NuRec."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


class ConversionError(RuntimeError):
    pass


def threedgrut_available() -> bool:
    return importlib.util.find_spec("threedgrut") is not None


def ply_to_usdz(ply_path: str | Path, usdz_path: str | Path) -> Path:
    """Run NVIDIA's documented Marble PLY → USDZ conversion.

    Requires 3DGRUT: https://github.com/nv-tlabs/3dgrut
    Command: python -m threedgrut.export.scripts.ply_to_usd SCENE.ply --output_file SCENE.usdz
    """
    ply = Path(ply_path)
    usdz = Path(usdz_path)
    if not ply.is_file():
        raise ConversionError(f"PLY not found: {ply}")
    if not threedgrut_available():
        raise ConversionError(
            "NVIDIA 3DGRUT is not installed, so PLY cannot be converted to USDZ. "
            "Clone https://github.com/nv-tlabs/3dgrut, install it, then rerun "
            f"`python -m threedgrut.export.scripts.ply_to_usd {ply} --output_file {usdz}`."
        )
    usdz.parent.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "threedgrut.export.scripts.ply_to_usd",
        str(ply),
        "--output_file",
        str(usdz),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise ConversionError(
            "3DGRUT ply_to_usd failed:\n"
            f"{completed.stdout}\n{completed.stderr}"
        )
    if not usdz.is_file():
        raise ConversionError(f"3DGRUT reported success but {usdz} was not written")
    return usdz
