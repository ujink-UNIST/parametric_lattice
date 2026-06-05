#boundary_moment_command.py
"""Module for boundary moment command functionality in src.post."""

from __future__ import annotations

"""Boundary moment postprocessing.

Mirrors the legacy moment computation in :mod:`postprocess.force_command`.

Definitions:
  - pp_boundary_moment(face, comp) is a 3x3 matrix
      face: X=1, Y=2, Z=3
      comp: X=1, Y=2, Z=3
  - Resultant is computed from periodic face node components via:
      M_A = (M_{-A} - M_{+A})/2

Requirements:
  Node components exist:
    PERIODIC_NODES_PX/NX/PY/NY/PZ/NZ
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.context import PostprocessContext
from post.boundary_force_command import _SIM_TYPE_TO_ROW, _col_index
from post.row import TOutRow


def build_boundary_moment_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx

    cmd: list[str] = [
        apdl_command("", "post: boundary_moment"),
        apdl_command(
            "*DIM,pp_boundary_moment,ARRAY,3,3",
            "(rows: face X/Y/Z, cols: moment X/Y/Z)",
        ),
    ]

    def face_sum(comp: str, tag: str) -> list[str]:
        return [
            apdl_command(f"CMSEL,S,{comp}", f"select {comp}"),
            apdl_command("FSUM", "sum nodal forces/moments"),
            apdl_command(f"*GET,pp_MX_{tag},FSUM,0,ITEM,MX"),
            apdl_command(f"*GET,pp_MY_{tag},FSUM,0,ITEM,MY"),
            apdl_command(f"*GET,pp_MZ_{tag},FSUM,0,ITEM,MZ"),
            apdl_command("ALLSEL,ALL"),
        ]

    # X faces
    cmd += face_sum("PERIODIC_NODES_PX", "PX")
    cmd += face_sum("PERIODIC_NODES_NX", "NX")
    cmd += [
        apdl_command("pp_boundary_moment(1,1)=(pp_MX_NX-pp_MX_PX)/2"),
        apdl_command("pp_boundary_moment(1,2)=(pp_MY_NX-pp_MY_PX)/2"),
        apdl_command("pp_boundary_moment(1,3)=(pp_MZ_NX-pp_MZ_PX)/2"),
    ]

    # Y faces
    cmd += face_sum("PERIODIC_NODES_PY", "PY")
    cmd += face_sum("PERIODIC_NODES_NY", "NY")
    cmd += [
        apdl_command("pp_boundary_moment(2,1)=(pp_MX_NY-pp_MX_PY)/2"),
        apdl_command("pp_boundary_moment(2,2)=(pp_MY_NY-pp_MY_PY)/2"),
        apdl_command("pp_boundary_moment(2,3)=(pp_MZ_NY-pp_MZ_PY)/2"),
    ]

    # Z faces
    cmd += face_sum("PERIODIC_NODES_PZ", "PZ")
    cmd += face_sum("PERIODIC_NODES_NZ", "NZ")
    cmd += [
        apdl_command("pp_boundary_moment(3,1)=(pp_MX_NZ-pp_MX_PZ)/2"),
        apdl_command("pp_boundary_moment(3,2)=(pp_MY_NZ-pp_MY_PZ)/2"),
        apdl_command("pp_boundary_moment(3,3)=(pp_MZ_NZ-pp_MZ_PZ)/2"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)


def extract_boundary_moment_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "N*mm",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    try:
        raw = mapdl.parameters["pp_boundary_moment"]
    except Exception:
        return []

    arr = np.asarray(raw, dtype=float).reshape(3, 3)

    case_index = int(ctx.sim_case.row_idx) + 1
    rows: list[TOutRow] = []
    for face_axis in range(1, 4):
        for comp in range(1, 4):
            v = float(arr[face_axis - 1, comp - 1])
            if not np.isfinite(v):
                continue
            rows.append(
                TOutRow(
                    index=case_index,
                    hash=case_hash,
                    category="moment.boundary.value",
                    row=int(out_row),
                    col=int(_col_index(face_axis, comp)),
                    value=v,
                    unit=unit,
                )
            )

    return rows
