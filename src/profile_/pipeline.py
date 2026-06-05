#pipeline.py
"""Module for pipeline functionality in src.profile_."""

from core.apdl_block import apdl_section
from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
    SolidProfileParams,
)
from core.unit_cell import UnitCell

from profile_.line_section_command import (
    build_line_section_commands_,
)
from profile_.section_command import build_section_commands_
from profile_.solid_section_command import (
    build_geometry_trim_commands_,
    build_solid_section_commands_,
    build_solid_sphere_commands_,
    merge_solid_all_commands_,
    merge_solid_extending_sections_commands_,
)


def profile_commands(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
) -> ApdlCommands:
    sec_cmds, edge_section_ids = build_section_commands_(
        unit_cell,
        geometry_params,
        profile_params,
    )

    return (
        (
            "",
            apdl_section("SECTION DEFINITION"),
        )
        + sec_cmds
        + (
            build_line_section_commands_(
                edge_sec_ids=edge_section_ids,
                orientation_keypoint_start=len(unit_cell.nodes),
            )
            if edge_section_ids
            else ()
        )
        + (
            build_solid_section_commands_(
                unit_cell, geometry_params, profile_params
            )
            + merge_solid_extending_sections_commands_(
                unit_cell, profile_params
            )
            + merge_solid_all_commands_(profile_params)
            + build_solid_sphere_commands_(
                unit_cell,
                geometry_params,
                profile_params,
                11 + len(unit_cell.edges),
            )
            + merge_solid_all_commands_(profile_params)
            + build_geometry_trim_commands_(
                unit_cell, geometry_params, profile_params
            )
            if isinstance(profile_params, SolidProfileParams)
            else ()
        )
    )
