# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\pipeline.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from core.apdl_block import apdl_block, apdl_section
from core.apdl_commands import ApdlCommands

from core.parameters.geometry_params import GeometryParams
from core.unit_cell import UnitCell


from geometry.keypoint_command import (
    build_keypoint_commands_,
)
from geometry.line_command import build_line_commands_
from geometry.orientation_keypoint_command import (
    build_beam_orientation_keypoint_commands_,
)


def geometry_commands(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
) -> ApdlCommands:
    return (
        (
            "",
            apdl_section("GEOMETRY DEFINITION"),
        )
        + build_keypoint_commands_(
            unit_cell, geometry_params
        )
        + build_beam_orientation_keypoint_commands_(
            unit_cell, geometry_params
        )
        + build_line_commands_(unit_cell)
    )
