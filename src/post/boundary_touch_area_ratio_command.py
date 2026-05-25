from __future__ import annotations

"""Boundary touch area ratio output.

Definition:
  boundary_touch_area_ratio_axis = touch_area_axis / full_face_area_axis

Derived in Python.

t_out:
  category = "boundary_touch_area_ratio"
  row = sim_type index (1..6)
  col = 1..3 for X,Y,Z
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.boundary_touch_area_command import extract_boundary_touch_area_rows
from post.context import PostprocessContext
from post.row import TOutRow


def build_boundary_touch_area_ratio_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def extract_boundary_touch_area_ratio_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    _ = mapdl

    size = ctx.sim_case.pre_mesh_spec.geometry.size
    sx, sy, sz = float(size[0]), float(size[1]), float(size[2])
    full = {
        1: sy * sz,  # X
        2: sx * sz,  # Y
        3: sx * sy,  # Z
    }

    touch = extract_boundary_touch_area_rows(ctx=ctx, mapdl=mapdl, case_hash=case_hash, unit="mm^2")

    out: list[TOutRow] = []
    for r in touch:
        denom = float(full.get(int(r.col), 0.0))
        if denom == 0.0:
            continue
        v = float(r.value) / denom
        if not np.isfinite(v):
            continue
        out.append(
            TOutRow(
                index=int(r.index),
                hash=str(r.hash),
                category="boundary_touch_area_ratio",
                row=int(r.row),
                col=int(r.col),
                value=float(v),
                unit=unit,
            )
        )
    return out
