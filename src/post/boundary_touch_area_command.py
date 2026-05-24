from __future__ import annotations

"""Boundary touch area output.

This is mesh-derived metadata stored in artifacts/mesh_db/<mesh_hash>/mesh.cdb
as /COM lines (PP_TOUCH_AX/AY/AZ). We read it in Python.

Output (t_out):
  - category = "boundary_touch_area"
  - row = sim_type index (xx..xy -> 1..6)
  - col = 1..3 for X,Y,Z
"""

from pathlib import Path
from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from custom_io.boundary_touch_area import compute_boundary_touch_area_from_cdb
from custom_io.mesh_io import mesh_db_dir
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.context import PostprocessContext
from post.row import TOutRow


def build_boundary_touch_area_commands_(_: PostprocessContext) -> ApdlCommands:
    # Derived in Python (from mesh.cdb metadata).
    return ()


def extract_boundary_touch_area_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mm^2",
) -> List[TOutRow]:
    _ = mapdl  # unused

    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    cdb_path: Path = mesh_db_dir(ctx.sim_case) / "mesh.cdb"
    tol = 1e-6 * float(ctx.sim_case.pre_mesh_spec.meshing.max_element_size)

    res = compute_boundary_touch_area_from_cdb(
        cdb_path=cdb_path,
        size_xyz=ctx.sim_case.pre_mesh_spec.geometry.size,
        tol=tol,
    )

    ax, ay, az = float(res.ax), float(res.ay), float(res.az)

    case_index = int(ctx.sim_case.row_idx) + 1
    vals = [ax, ay, az]
    rows: list[TOutRow] = []
    for col, v in enumerate(vals, start=1):
        if not np.isfinite(v):
            continue
        rows.append(
            TOutRow(
                index=case_index,
                hash=case_hash,
                category="boundary_touch_area",
                row=int(out_row),
                col=int(col),
                value=float(v),
                unit=unit,
            )
        )

    return rows
