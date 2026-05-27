from __future__ import annotations

"""Total volume postprocessing.

Mirrors :mod:`postprocess.volume_command.build_volume_commands_`.

Output MAPDL parameter:
  - pp_volume (scalar)
"""

from typing import List

import numpy as np

from core.apdl_commands import ApdlCommands, Mapdl, apdl_command
from post.context import PostprocessContext
from post.boundary_force_command import _SIM_TYPE_TO_ROW
from post.row import TOutRow


def build_volume_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx

    cmd: list[str] = [
        apdl_command("", "post: volume"),
        apdl_command("ETABLE,pp__VOLU,VOLU", "element volume"),
        apdl_command("pp_volume=0", "init total volume"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__evol,ELEM,pp__eid,ETAB,pp__VOLU", "element volume"),
        apdl_command("  pp_volume=pp_volume+pp__evol", "accumulate"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)


def extract_volume_rows(
    *,
    ctx: PostprocessContext,
    mapdl: Mapdl,
    case_hash: str,
    unit: str = "mm^3",
) -> List[TOutRow]:
    sim_type = str(ctx.sim_case.post_mesh_spec.setup.sim_type).strip().lower()
    out_row = _SIM_TYPE_TO_ROW.get(sim_type)
    if out_row is None:
        return []

    try:
        v = float(mapdl.parameters["pp_volume"])
    except Exception:
        return []

    if not np.isfinite(v):
        return []

    case_index = int(ctx.sim_case.row_idx) + 1
    return [
        TOutRow(
            index=case_index,
            hash=case_hash,
            category="volume.solid.value",
            row=int(out_row),
            col=1,
            value=float(v),
            unit=unit,
        )
    ]
