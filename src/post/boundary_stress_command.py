#boundary_stress_command.py
"""Module for boundary stress command functionality in src.post."""

from __future__ import annotations

"""Boundary stress postprocessing.

Mirrors :mod:`postprocess.boundary_command.build_boundary_stress_commands_`.

Dependency:
  Requires `pp_boundary_traction` to exist.

Storage:
  pp_boundary_stress(6) with APDL Vector6 ordering:
    [XX, YY, ZZ, XY, YZ, XZ]

For t_out we map the 6 components to col=1..6 using project ordering:
  xx->1, yy->2, zz->3, yz->4, xz->5, xy->6
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.context import PostprocessContext
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.row import TOutRow


# APDL Vector6 indices (1-based): XX,YY,ZZ,XY,YZ,XZ
# t_out col ordering (1..6): xx,yy,zz,yz,xz,xy
_COL_FROM_APDL_INDEX: dict[int, int] = {
    1: 1,  # XX
    2: 2,  # YY
    3: 3,  # ZZ
    5: 4,  # YZ
    6: 5,  # XZ
    4: 6,  # XY
}


def build_boundary_stress_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx

    cmd: list[str] = [
        apdl_command("", "post: boundary_stress"),
        apdl_command("*DIM,pp_boundary_stress,ARRAY,6", "[XX,YY,ZZ,XY,YZ,XZ]"),
        apdl_command("pp_boundary_stress(1)=pp_boundary_traction(1,1)", "XX"),
        apdl_command("pp_boundary_stress(2)=pp_boundary_traction(2,2)", "YY"),
        apdl_command("pp_boundary_stress(3)=pp_boundary_traction(3,3)", "ZZ"),
        apdl_command(
            "pp_boundary_stress(4)=(pp_boundary_traction(1,2)+pp_boundary_traction(2,1))/2",
            "XY",
        ),
        apdl_command(
            "pp_boundary_stress(5)=(pp_boundary_traction(2,3)+pp_boundary_traction(3,2))/2",
            "YZ",
        ),
        apdl_command(
            "pp_boundary_stress(6)=(pp_boundary_traction(1,3)+pp_boundary_traction(3,1))/2",
            "XZ",
        ),
    ]

    return tuple(cmd)


def extract_boundary_stress_rows(
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

    try:
        raw = mapdl.parameters["pp_boundary_stress"]
    except Exception:
        return []

    arr = np.asarray(raw, dtype=float).reshape(-1)
    if arr.size != 6:
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    rows: list[TOutRow] = []

    for apdl_i1 in range(1, 7):
        col = _COL_FROM_APDL_INDEX.get(apdl_i1)
        if col is None:
            continue
        v = float(arr[apdl_i1 - 1])
        if not np.isfinite(v):
            continue
        rows.append(
            TOutRow(
                index=case_index,
                hash=case_hash,
                category="stress.boundary.value",
                row=int(out_row),
                col=int(col),
                value=v,
                unit=unit,
            )
        )

    return rows
