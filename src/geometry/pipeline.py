# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\pipeline.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.unit_cell import UnitCell
from core.parameters.material_params import MaterialParams


from geometry.section_command import build_section_commands_
from geometry.keypoint_command import (
    build_keypoint_commands_,
)
from geometry.line_command import build_line_commands_
from geometry.orientation_keypoint_command import (
    build_beam_orientation_keypoint_commands_,
)

from geometry.line_section_command import (
    build_line_section_commands_,
)


def geometry_commands(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    material_params: MaterialParams,
) -> ApdlCommands:
    sec_cmds, edge_sec_ids = build_section_commands_(
        unit_cell, material_params
    )
    orientation_keypoint_start = len(unit_cell.nodes)

    return (
        ("! --- Common lattice topology geometry ---",)
        + build_keypoint_commands_(
            unit_cell, geometry_params
        )
        + build_line_commands_(unit_cell)
        + build_beam_orientation_keypoint_commands_(
            unit_cell
        )
        + (
            "! --- Beam element, material, and section setup ---",
        )
        + sec_cmds
        + build_line_section_commands_(
            edge_sec_ids,
            orientation_keypoint_start,
        )
    )
