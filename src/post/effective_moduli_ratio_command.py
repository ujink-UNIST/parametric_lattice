from __future__ import annotations

"""Material-normalized effective moduli ratios.

- effective_youngs_modulus_ratio = effective_youngs_modulus / E
- effective_shear_modulus_ratio  = effective_shear_modulus  / G
  where G = E / (2*(1+nu))

Derived in Python.

t_out:
  category = "effective_youngs_modulus_ratio" or "effective_shear_modulus_ratio"
  row = sim_type index (1..6)
  col:
    - youngs: X=1,Y=2,Z=3
    - shear:  YZ=4,XZ=5,XY=6
  unit = "-"
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


def build_effective_youngs_modulus_ratio_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def build_effective_shear_modulus_ratio_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def extract_effective_youngs_modulus_ratio_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    E = float(ctx.sim_case.post_mesh_spec.material.e_mod)
    if E == 0.0:
        return []

    eff = extract_effective_youngs_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
    out: list[TOutRow] = []
    for r in eff:
        v = float(r.value) / E
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=int(r.index),
                hash=str(r.hash),
                category="effective_youngs_modulus_ratio",
                row=int(r.row),
                col=int(r.col),
                value=float(v),
                unit=unit,
            )
        )
    return out


def extract_effective_shear_modulus_ratio_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    E = float(ctx.sim_case.post_mesh_spec.material.e_mod)
    nu = float(ctx.sim_case.post_mesh_spec.material.nu)
    denom = 2.0 * (1.0 + nu)
    if denom == 0.0:
        return []
    G = E / denom
    if G == 0.0:
        return []

    eff = extract_effective_shear_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
    out: list[TOutRow] = []
    for r in eff:
        v = float(r.value) / G
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=int(r.index),
                hash=str(r.hash),
                category="effective_shear_modulus_ratio",
                row=int(r.row),
                col=int(r.col),
                value=float(v),
                unit=unit,
            )
        )
    return out
