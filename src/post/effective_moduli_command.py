from __future__ import annotations

"""Effective moduli outputs.

These are derived in Python from boundary_modulus (= boundary_stress / strain).

- effective_youngs_modulus: scalar modulus for normal cases xx/yy/zz.
  Output columns (t_out col):
    1 -> X, 2 -> Y, 3 -> Z

- effective_shear_modulus: scalar modulus for shear cases xy/yz/xz.
  Uses sigma_ij = 2 G epsilon_ij.
  Output columns (t_out col):
    4 -> YZ, 5 -> XZ, 6 -> XY

Row index is always the load-case index derived from sim_type (xx..xy -> 1..6).
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.boundary_modulus_command import extract_boundary_modulus_rows
from post.context import PostprocessContext
from post.row import TOutRow


def build_effective_youngs_modulus_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def build_effective_shear_modulus_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def extract_effective_youngs_modulus_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "MPa",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    # Only for normal cases.
    col_map = {"xx": 1, "yy": 2, "zz": 3}
    out_col = col_map.get(sim_type)
    if out_col is None:
        return []

    eps = float(ctx.sim_case.post_mesh_spec.setup.strain)
    if eps == 0.0:
        return []

    # Reuse boundary_modulus extraction to ensure consistent mapping.
    mod_rows = extract_boundary_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit=unit)
    # Find the matching modulus component: xx/yy/zz correspond to col 1/2/3.
    val: float | None = None
    for r in mod_rows:
        if r.col == out_col:
            val = float(r.value)
            break
    if val is None or not np.isfinite(val):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="modulus.effective.youngs",
            row=int(out_row),
            col=int(out_col),
            value=float(val),
            unit=unit,
        )
    ]


def extract_effective_shear_modulus_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "MPa",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    # Only for shear cases.
    # Map sim_type -> (boundary_modulus col, output col)
    # boundary_modulus col ordering: [xx,yy,zz,yz,xz,xy]
    # We align output cols with boundary_stress convention:
    #   col 4 -> YZ, col 5 -> XZ, col 6 -> XY
    shear_map = {
        "yz": (4, 4),
        "xz": (5, 5),
        "xy": (6, 6),
    }
    info = shear_map.get(sim_type)
    if info is None:
        return []
    mod_col, out_col = info

    eps = float(ctx.sim_case.post_mesh_spec.setup.strain)
    if eps == 0.0:
        return []

    mod_rows = extract_boundary_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit=unit)
    val: float | None = None
    for r in mod_rows:
        if r.col == mod_col:
            val = float(r.value)
            break
    if val is None or not np.isfinite(val):
        return []

    # sigma_ij = 2 G epsilon_ij  => G = (sigma/epsilon)/2
    g = float(val) / 2.0
    if not np.isfinite(g):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="modulus.effective.shear",
            row=int(out_row),
            col=int(out_col),
            value=float(g),
            unit=unit,
        )
    ]
