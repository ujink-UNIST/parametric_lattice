# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\line_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from typing import cast

from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3Int
from core.unit_cell import UnitCell


def build_line_commands_(
    unit_cell: UnitCell,
) -> ApdlCommands:
    """Return ``L`` commands for every lattice edge."""
    cmds: list[str] = [
        "! Create beam centerlines from lattice edges"
    ]

    for line_id, row in enumerate(unit_cell.edges, start=1):
        edge: Vector3Int = cast(Vector3Int, row)

        n1_idx = int(edge[0])
        n2_idx = int(edge[1])

        kp1_id = n1_idx + 1
        kp2_id = n2_idx + 1

        cmds.append(f"L,{kp1_id},{kp2_id}")

    return tuple(cmds)
