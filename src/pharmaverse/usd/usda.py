"""Helpers for OpenUSD ASCII emission."""

from __future__ import annotations

from typing import Iterable


def fmt_vec(values: Iterable[float]) -> str:
    parts = []
    for raw in values:
        value = float(raw)
        if abs(value) < 1e-12:
            value = 0.0
        parts.append(f"{value:.6g}")
    return f"({', '.join(parts)})"


def semantic_block(class_name: str, indent: str) -> str:
    return "\n".join(
        [
            f'{indent}token semantic:Semantics:params:semanticType = "class"',
            f'{indent}string semantic:Semantics:params:semanticData = "{class_name}"',
            f'{indent}custom string pharmaverse:semanticClass = "{class_name}"',
        ]
    )


def xform_ops(translate=None, rotate_xyz_deg=None, scale=None, indent: str = "    ", order: list[str] | None = None) -> str:
    lines: list[str] = []
    built: list[str] = []
    if translate is not None:
        lines.append(f"{indent}double3 xformOp:translate = {fmt_vec(translate)}")
        built.append("xformOp:translate")
    if rotate_xyz_deg is not None:
        lines.append(f"{indent}float3 xformOp:rotateXYZ = {fmt_vec(rotate_xyz_deg)}")
        built.append("xformOp:rotateXYZ")
    if scale is not None:
        lines.append(f"{indent}float3 xformOp:scale = {fmt_vec(scale)}")
        built.append("xformOp:scale")
    applied = order or built
    if applied:
        joined = ", ".join(f'"{item}"' for item in applied)
        lines.append(f"{indent}uniform token[] xformOpOrder = [{joined}]")
    return "\n".join(lines)
