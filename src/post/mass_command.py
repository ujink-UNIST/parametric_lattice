from __future__ import annotations

"""Mass output.

Derived in Python:
  mass = density * volume

Dependency:
  requires pp_volume (volume output).

t_out:
  category = "mass"
  row = sim_type index (1..6)
  col = 1
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.context import PostprocessContext
from post.row import TOutRow


def build_mass_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def extract_mass_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "kg",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    rho = float(ctx.sim_case.post_mesh_spec.material.density)
    try:
        vol = float(mapdl.parameters["pp_volume"])
    except Exception:
        return []

    m = rho * vol
    if not np.isfinite(m):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="mass",
            row=int(out_row),
            col=1,
            value=float(m),
            unit=unit,
        )
    ]
