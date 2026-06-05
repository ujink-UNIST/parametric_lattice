#contact_command.py
"""Module for contact command functionality in src.post."""

from __future__ import annotations

"""Contact-derived quantities.

Definitions (mirrors legacy excel_io behavior):
- contact_traction: boundary_force normalized by boundary_touch_area
    ct(face_axis, comp) = bf(face_axis, comp) / A_touch(axis)
  where bf is pp_boundary_force (3x3) and A_touch is (ax,ay,az).

- contact_stress: symmetric Voigt stress derived from traction matrix ct
    [xx,yy,zz, yz, xz, xy] ordering for t_out col=1..6.

Dependencies:
  - boundary_force (MAPDL: pp_boundary_force)
  - boundary_touch_area (Python: from mesh.cdb metadata)
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from custom_io.boundary_touch_area import compute_boundary_touch_area_from_cdb
from custom_io.mesh_io import mesh_db_dir
from post.boundary_force_command import _SIM_TYPE_TO_ROW, _col_index
from post.context import PostprocessContext
from post.row import TOutRow


# t_out col ordering for Vector6-like quantities: [xx,yy,zz,yz,xz,xy]
# from symmetric traction matrix.
_STRESS_COLS: dict[str, int] = {
    "xx": 1,
    "yy": 2,
    "zz": 3,
    "yz": 4,
    "xz": 5,
    "xy": 6,
}


def build_contact_traction_commands_(_: PostprocessContext) -> ApdlCommands:
    # Derived in Python.
    return ()


def build_contact_stress_commands_(_: PostprocessContext) -> ApdlCommands:
    # Derived in Python.
    return ()


def _touch_area_xyz(ctx: PostprocessContext) -> tuple[float, float, float]:
    cdb_path = mesh_db_dir(ctx.sim_case) / "mesh.cdb"
    tol = 1e-6 * float(ctx.sim_case.pre_mesh_spec.meshing.max_element_size)
    res = compute_boundary_touch_area_from_cdb(
        cdb_path=cdb_path,
        size_xyz=ctx.sim_case.pre_mesh_spec.geometry.size,
        tol=tol,
    )
    return float(res.ax), float(res.ay), float(res.az)


def extract_contact_traction_rows(
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
        bf_raw = mapdl.parameters["pp_boundary_force"]
    except Exception:
        return []

    bf = np.asarray(bf_raw, dtype=float).reshape(3, 3)
    ax, ay, az = _touch_area_xyz(ctx)
    if ax <= 0.0 or ay <= 0.0 or az <= 0.0:
        return []

    ct = np.zeros((3, 3), dtype=float)
    ct[0, :] = bf[0, :] / ax
    ct[1, :] = bf[1, :] / ay
    ct[2, :] = bf[2, :] / az

    case_index = int(ctx.sim_case.row_idx) + 1
    rows: list[TOutRow] = []
    for face_axis in range(1, 4):
        for comp in range(1, 4):
            v = float(ct[face_axis - 1, comp - 1])
            if not np.isfinite(v):
                continue
            rows.append(
                TOutRow(
                    index=case_index,
                    hash=case_hash,
                    category="traction.contact.value",
                    row=int(out_row),
                    col=int(_col_index(face_axis, comp)),
                    value=v,
                    unit=unit,
                )
            )

    return rows


def extract_contact_stress_rows(
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
        bf_raw = mapdl.parameters["pp_boundary_force"]
    except Exception:
        return []

    bf = np.asarray(bf_raw, dtype=float).reshape(3, 3)
    ax, ay, az = _touch_area_xyz(ctx)
    if ax <= 0.0 or ay <= 0.0 or az <= 0.0:
        return []

    ct = np.zeros((3, 3), dtype=float)
    ct[0, :] = bf[0, :] / ax
    ct[1, :] = bf[1, :] / ay
    ct[2, :] = bf[2, :] / az

    # Symmetric Voigt-like components
    sxx = float(ct[0, 0])
    syy = float(ct[1, 1])
    szz = float(ct[2, 2])
    sxy = 0.5 * float(ct[0, 1] + ct[1, 0])
    syz = 0.5 * float(ct[1, 2] + ct[2, 1])
    sxz = 0.5 * float(ct[0, 2] + ct[2, 0])

    vals = {
        _STRESS_COLS["xx"]: sxx,
        _STRESS_COLS["yy"]: syy,
        _STRESS_COLS["zz"]: szz,
        _STRESS_COLS["yz"]: syz,
        _STRESS_COLS["xz"]: sxz,
        _STRESS_COLS["xy"]: sxy,
    }

    case_index = int(ctx.sim_case.row_idx) + 1
    rows: list[TOutRow] = []
    for col, v in vals.items():
        if not np.isfinite(v):
            continue
        rows.append(
            TOutRow(
                index=case_index,
                hash=case_hash,
                category="stress.contact.value",
                row=int(out_row),
                col=int(col),
                value=float(v),
                unit=unit,
            )
        )

    return rows
