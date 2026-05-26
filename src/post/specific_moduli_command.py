from __future__ import annotations

"""Specific stiffness-like outputs.

- specific_youngs_modulus = effective_youngs_modulus / density
- specific_shear_modulus  = effective_shear_modulus  / density

These are derived in Python.

t_out:
  category = "specific_youngs_modulus" or "specific_shear_modulus"
  row = sim_type index (1..6)
  col matches the effective modulus col:
    - youngs: X=1,Y=2,Z=3
    - shear:  YZ=4,XZ=5,XY=6

Unit convention (when using N-mm-s with density in kg/mm^3):
  (MPa) / (kg/mm^3) = (N/mm^2) / (kg/mm^3) = mm^2/s^2
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.context import PostprocessContext
from post.effective_moduli_command import (
    extract_effective_shear_modulus_rows,
    extract_effective_youngs_modulus_rows,
)
from post.row import TOutRow


def build_specific_youngs_modulus_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def build_specific_shear_modulus_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def extract_specific_youngs_modulus_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mm^2/s^2",
) -> List[TOutRow]:
    rho = float(ctx.sim_case.post_mesh_spec.material.density)
    if rho == 0.0:
        return []

    eff = extract_effective_youngs_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
    out: list[TOutRow] = []
    for r in eff:
        v = float(r.value) / rho
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=int(r.index),
                hash=str(r.hash),
                category="specific_youngs_modulus",
                row=int(r.row),
                col=int(r.col),
                value=float(v),
                unit=unit,
            )
        )
    return out


def extract_specific_shear_modulus_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mm^2/s^2",
) -> List[TOutRow]:
    rho = float(ctx.sim_case.post_mesh_spec.material.density)
    if rho == 0.0:
        return []

    eff = extract_effective_shear_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
    out: list[TOutRow] = []
    for r in eff:
        v = float(r.value) / rho
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=int(r.index),
                hash=str(r.hash),
                category="specific_shear_modulus",
                row=int(r.row),
                col=int(r.col),
                value=float(v),
                unit=unit,
            )
        )
    return out
