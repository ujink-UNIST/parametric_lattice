# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\keypoint_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from typing import cast

from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.geometric.transform import transform_coords
from core.parameters.geometry_params import GeometryParams
from core.unit_cell import UnitCell


def build_keypoint_commands_(
    unit_cell: UnitCell, geometry_commands: GeometryParams
) -> ApdlCommands:
    """Return ``K`` commands for every lattice node."""
    cmds: list[str] = [
        "! Create lattice keypoints from unit-cell nodes"
    ]

    size = geometry_commands.size

    for kp_id, row in enumerate(unit_cell.nodes, start=1):
        node: Vector3 = transform_coords(
            cast(Vector3, row), size
        )
        cmds.append(
            f"K,{kp_id},{node[0]:.10g},{node[1]:.10g},{node[2]:.10g}"
        )

    return tuple(cmds)
