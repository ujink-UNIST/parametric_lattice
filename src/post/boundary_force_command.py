#boundary_force_command.py
"""Module for boundary force command functionality in src.post."""

from __future__ import annotations

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.context import PostprocessContext
from post.row import TOutRow


_SIM_TYPE_TO_ROW: dict[str, int] = {
    "xx": 1,
    "yy": 2,
    "zz": 3,
    "yz": 4,
    "xz": 5,
    "xy": 6,
    "xyz": 7,
}


def _col_index(face_axis: int, force_comp: int) -> int:
    """Map (face_axis, force_comp) in 1..3 to 1..9.

    Ordering: XX, XY, XZ, YX, YY, YZ, ZX, ZY, ZZ
    i.e. row-major over face axis then component.
    """

    if not (1 <= face_axis <= 3 and 1 <= force_comp <= 3):
        raise ValueError(f"invalid indices: face_axis={face_axis} force_comp={force_comp}")
    return (face_axis - 1) * 3 + force_comp


def build_boundary_force_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx

    cmd: list[str] = [
        apdl_command("", "post: boundary_force"),
        apdl_command(
            "*DIM,pp_boundary_force,ARRAY,3,3",
            "(rows: face X/Y/Z, cols: force X/Y/Z)",
        ),
    ]

    def face_sum(comp: str, tag: str) -> list[str]:
        return [
            apdl_command(f"CMSEL,S,{comp}", f"select {comp}"),
            apdl_command("FSUM", "sum nodal forces"),
            apdl_command(f"*GET,pp_FX_{tag},FSUM,0,ITEM,FX"),
            apdl_command(f"*GET,pp_FY_{tag},FSUM,0,ITEM,FY"),
            apdl_command(f"*GET,pp_FZ_{tag},FSUM,0,ITEM,FZ"),
            apdl_command("ALLSEL,ALL"),
        ]

    # X faces
    cmd += face_sum("PERIODIC_NODES_PX", "PX")
    cmd += face_sum("PERIODIC_NODES_NX", "NX")
    cmd += [
        apdl_command("pp_boundary_force(1,1)=(pp_FX_NX-pp_FX_PX)/2"),
        apdl_command("pp_boundary_force(1,2)=(pp_FY_NX-pp_FY_PX)/2"),
        apdl_command("pp_boundary_force(1,3)=(pp_FZ_NX-pp_FZ_PX)/2"),
    ]

    # Y faces
    cmd += face_sum("PERIODIC_NODES_PY", "PY")
    cmd += face_sum("PERIODIC_NODES_NY", "NY")
    cmd += [
        apdl_command("pp_boundary_force(2,1)=(pp_FX_NY-pp_FX_PY)/2"),
        apdl_command("pp_boundary_force(2,2)=(pp_FY_NY-pp_FY_PY)/2"),
        apdl_command("pp_boundary_force(2,3)=(pp_FZ_NY-pp_FZ_PY)/2"),
    ]

    # Z faces
    cmd += face_sum("PERIODIC_NODES_PZ", "PZ")
    cmd += face_sum("PERIODIC_NODES_NZ", "NZ")
    cmd += [
        apdl_command("pp_boundary_force(3,1)=(pp_FX_NZ-pp_FX_PZ)/2"),
        apdl_command("pp_boundary_force(3,2)=(pp_FY_NZ-pp_FY_PZ)/2"),
        apdl_command("pp_boundary_force(3,3)=(pp_FZ_NZ-pp_FZ_PZ)/2"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)


def extract_boundary_force_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "N",
) -> List[TOutRow]:
    """Extract boundary_force rows from MAPDL parameters.

    Missing values are represented by absence of rows.

    Output conventions (t_out):
      - category = "boundary_force"
      - index = sim_case.row_idx + 1 (1-based)
      - row = load-case index from sim_type: xx=1,yy=2,zz=3,yz=4,xz=5,xy=6
      - col = 1..9 for (face_axis, force_comp) in ordering:
              XX,XY,XZ,YX,YY,YZ,ZX,ZY,ZZ
    """

    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    # MAPDL parameters behaves like a mapping but does not implement .get().
    try:
        raw = mapdl.parameters["pp_boundary_force"]
    except Exception:
        return []

    arr = np.asarray(raw, dtype=float).reshape(3, 3)

    rows: list[TOutRow] = []
    case_index = int(ctx.sim_case.row_idx) + 1  # 1-based case index
    for face_axis in range(1, 4):
        for force_comp in range(1, 4):
            v = float(arr[face_axis - 1, force_comp - 1])
            if not np.isfinite(v):
                continue
            rows.append(
                TOutRow(
                    index=case_index,
                    hash=case_hash,
                    category="force.boundary.value",
                    row=int(out_row),
                    col=int(_col_index(face_axis, force_comp)),
                    value=v,
                    unit=unit,
                )
            )
    return rows
