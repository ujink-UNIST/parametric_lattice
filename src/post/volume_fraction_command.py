#volume_fraction_command.py
"""Module for volume fraction command functionality in src.post."""

from __future__ import annotations

"""Volume fraction output.

Definition:
  volume_fraction = volume / (cell_size_x * cell_size_y * cell_size_z)

Derived in Python from pp_volume and geometry size.

t_out:
  category = "volume_fraction"
  row = sim_type index (1..6)
  col = 1
  unit = "-"
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.context import PostprocessContext
from post.row import TOutRow


def build_volume_fraction_commands_(_: PostprocessContext) -> ApdlCommands:
    return ()


def extract_volume_fraction_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "-",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    try:
        vol = float(mapdl.parameters["pp_volume"])
    except Exception:
        return []

    size = ctx.sim_case.pre_mesh_spec.geometry.size
    sx, sy, sz = float(size[0]), float(size[1]), float(size[2])
    cell_vol = sx * sy * sz
    if cell_vol == 0.0:
        return []

    vf = vol / cell_vol
    if not np.isfinite(vf):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="volume_fraction.cell.value",
            row=int(out_row),
            col=1,
            value=float(vf),
            unit=unit,
        )
    ]
