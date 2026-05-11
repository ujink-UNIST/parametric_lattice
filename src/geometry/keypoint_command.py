# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\keypoint_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from typing import cast

import numpy as np

from core.apdl_block import (
    apdl_block,
    apdl_comment,
    apdl_inline_comment,
)
from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.geometric.transform import transform_coords
from core.parameters.geometry_params import GeometryParams
from core.unit_cell import UnitCell


def build_keypoint_commands_(
    unit_cell: UnitCell, geometry_commands: GeometryParams
) -> ApdlCommands:
    cmds: list[str] = []

    cmds.extend(apdl_block(f"""
{apdl_comment("Create keypoints")}

"""))

    size = geometry_commands.size

    count: int = unit_cell.nodes.shape[0]
    digits = len(str(count - 1))

    for kp_id, row in enumerate(unit_cell.nodes, start=1):
        node: Vector3 = transform_coords(
            cast(Vector3, row), size
        )

        index = kp_id - 1

        cmds.extend(
            apdl_block(
                f"""K,{kp_id},{node[0]:.10g},{node[1]:.10g},{node[2]:.10g} {apdl_inline_comment(
                    f"{index:>{digits}}: n {row[0]} {row[1]} {row[2]}")}"""
            )
        )

    return tuple(cmds)
