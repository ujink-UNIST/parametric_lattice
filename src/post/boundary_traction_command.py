from __future__ import annotations

"""Boundary traction postprocessing.

Mirrors :mod:`postprocess.boundary_command.build_boundary_traction_commands_`.

Dependency:
  Requires `pp_boundary_force` to exist.

Definition:
  traction(face, comp) = boundary_force(face, comp) / A_face

Storage:
  pp_boundary_traction(comp, face) where:
    - row    = traction component (X=1, Y=2, Z=3)
    - column = face normal axis (X=1, Y=2, Z=3)
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.context import PostprocessContext
from post.boundary_force_command import _SIM_TYPE_TO_ROW, _col_index
from post.row import TOutRow


def _face_area(ctx: PostprocessContext, axis: str) -> float:
    size = ctx.sim_case.pre_mesh_spec.geometry.size
    sx, sy, sz = float(size[0]), float(size[1]), float(size[2])
    if axis == "X":
        return sy * sz
    if axis == "Y":
        return sx * sz
    if axis == "Z":
        return sx * sy
    raise ValueError(f"Unknown axis {axis!r}")


def build_boundary_traction_commands_(ctx: PostprocessContext) -> ApdlCommands:
    ax = _face_area(ctx, "X")
    ay = _face_area(ctx, "Y")
    az = _face_area(ctx, "Z")

    cmd: list[str] = [
        apdl_command("", "post: boundary_traction"),
        apdl_command(
            "*DIM,pp_boundary_traction,ARRAY,3,3",
            "(rows: traction X/Y/Z, cols: face X/Y/Z)",
        ),
        apdl_command(f"! Face areas: AX={ax:g}, AY={ay:g}, AZ={az:g}"),
        apdl_command(f"pp_boundary_traction(1,1)=pp_boundary_force(1,1)/{ax:g}"),
        apdl_command(f"pp_boundary_traction(2,1)=pp_boundary_force(1,2)/{ax:g}"),
        apdl_command(f"pp_boundary_traction(3,1)=pp_boundary_force(1,3)/{ax:g}"),
        apdl_command(f"pp_boundary_traction(1,2)=pp_boundary_force(2,1)/{ay:g}"),
        apdl_command(f"pp_boundary_traction(2,2)=pp_boundary_force(2,2)/{ay:g}"),
        apdl_command(f"pp_boundary_traction(3,2)=pp_boundary_force(2,3)/{ay:g}"),
        apdl_command(f"pp_boundary_traction(1,3)=pp_boundary_force(3,1)/{az:g}"),
        apdl_command(f"pp_boundary_traction(2,3)=pp_boundary_force(3,2)/{az:g}"),
        apdl_command(f"pp_boundary_traction(3,3)=pp_boundary_force(3,3)/{az:g}"),
    ]

    return tuple(cmd)


def extract_boundary_traction_rows(
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
        raw = mapdl.parameters["pp_boundary_traction"]
    except Exception:
        return []

    arr = np.asarray(raw, dtype=float).reshape(3, 3)

    case_index = int(ctx.sim_case.row_idx) + 1
    rows: list[TOutRow] = []

    # arr is (traction_comp, face_axis). We map to col using (face_axis, comp).
    for traction_comp in range(1, 4):
        for face_axis in range(1, 4):
            v = float(arr[traction_comp - 1, face_axis - 1])
            if not np.isfinite(v):
                continue
            rows.append(
                TOutRow(
                    index=case_index,
                    hash=case_hash,
                    category="traction.boundary.value",
                    row=int(out_row),
                    col=int(_col_index(face_axis, traction_comp)),
                    value=v,
                    unit=unit,
                )
            )

    return rows
