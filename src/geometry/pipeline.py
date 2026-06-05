#pipeline.py
"""Module for pipeline functionality in src.geometry."""

from core.apdl_block import apdl_block, apdl_section
from core.apdl_commands import ApdlCommands

from core.parameters.element_type_params import ElementTypeParams
from core.parameters.geometry_params import GeometryParams
from core.parameters.profile_params import ProfileParams
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
    element_type: ElementTypeParams,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
) -> ApdlCommands:

    return (
        (
            "",
            apdl_section("GEOMETRY DEFINITION"),
        )
        + build_keypoint_commands_(unit_cell, geometry_params)
        + build_beam_orientation_keypoint_commands_(unit_cell, geometry_params)
        + build_line_commands_(unit_cell, element_type)
    )
