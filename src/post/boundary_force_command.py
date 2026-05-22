from __future__ import annotations

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.context import PostprocessContext
from post.row import TOutRow


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
    start_index: int = 0,
    unit: str = "N",
) -> List[TOutRow]:
    """Extract boundary_force rows from MAPDL parameters.

    Missing values are represented by absence of rows.

    component convention: "ij" where i=face axis (1..3), j=force component (1..3).
    metric convention: "boundary_force.<sim_type>".
    """

    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type)
    metric = f"boundary_force.{sim_type}"

    raw = mapdl.parameters.get("pp_boundary_force", None)
    if raw is None:
        return []

    arr = np.asarray(raw, dtype=float).reshape(3, 3)

    rows: list[TOutRow] = []
    k = int(start_index)
    for i in range(3):
        for j in range(3):
            v = float(arr[i, j])
            if not np.isfinite(v):
                continue
            comp = f"{i+1}{j+1}"
            rows.append(
                TOutRow(
                    index=k,
                    hash=case_hash,
                    category="boundary_force",
                    metric=metric,
                    component=comp,
                    value=v,
                    unit=unit,
                )
            )
            k += 1

    return rows
