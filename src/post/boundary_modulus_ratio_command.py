from __future__ import annotations

"""Boundary modulus ratio output.

Definition:
  boundary_modulus_ratio = boundary_modulus / E

Derived in Python.

t_out:
  category = "boundary_modulus_ratio"
  row = sim_type index (1..6)
  col = 1..6 ordering [xx,yy,zz,yz,xz,xy]
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.boundary_modulus_command import extract_boundary_modulus_rows
from post.context import PostprocessContext
from post.row import TOutRow


def build_boundary_modulus_ratio_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def extract_boundary_modulus_ratio_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    E = float(ctx.sim_case.post_mesh_spec.material.e_mod)
    if E == 0.0:
        return []

    mods = extract_boundary_modulus_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="MPa")
    out: list[TOutRow] = []
    for r in mods:
        v = float(r.value) / E
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=int(r.index),
                hash=str(r.hash),
                category="boundary_modulus_ratio",
                row=int(r.row),
                col=int(r.col),
                value=float(v),
                unit=unit,
            )
        )
    return out
