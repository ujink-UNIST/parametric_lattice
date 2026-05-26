from __future__ import annotations

"""Boundary modulus postprocessing.

Derived quantity in Python:
  boundary_modulus = boundary_stress / strain

Dependencies:
  Requires `pp_boundary_stress` to exist.

Output (t_out):
  - category = "boundary_modulus"
  - row = sim_type index (xx..xy -> 1..6)
  - col = 1..6 with ordering: xx,yy,zz,yz,xz,xy
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.context import PostprocessContext
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.row import TOutRow


# APDL Vector6 ordering: [XX, YY, ZZ, XY, YZ, XZ]
# t_out col ordering:     [xx, yy, zz, yz, xz, xy]
_COL_FROM_APDL_INDEX: dict[int, int] = {
    1: 1,  # XX
    2: 2,  # YY
    3: 3,  # ZZ
    5: 4,  # YZ
    6: 5,  # XZ
    4: 6,  # XY
}


def build_boundary_modulus_commands_(_: PostprocessContext) -> ApdlCommands:
    # Derived in Python; no MAPDL commands.
    return ()


def extract_boundary_modulus_rows(
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

    eps = float(ctx.sim_case.post_mesh_spec.setup.strain)
    if eps == 0.0:
        return []

    try:
        raw = mapdl.parameters["pp_boundary_stress"]
    except Exception:
        return []

    s = np.asarray(raw, dtype=float).reshape(-1)
    if s.size != 6:
        return []

    mod = s / eps

    case_index = int(ctx.sim_case.row_idx) + 1
    rows: list[TOutRow] = []
    for apdl_i1 in range(1, 7):
        col = _COL_FROM_APDL_INDEX.get(apdl_i1)
        if col is None:
            continue
        v = float(mod[apdl_i1 - 1])
        if not np.isfinite(v):
            continue
        rows.append(
            TOutRow(
                index=case_index,
                hash=case_hash,
                category="boundary_modulus",
                row=int(out_row),
                col=int(col),
                value=v,
                unit=unit,
            )
        )

    return rows
