# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\pipeline.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from __future__ import annotations

from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import ProfileParams
from core.unit_cell import UnitCell
from meshing.surface_meshing import (
    build_surface_area_meshing_commands_,
    build_surface_line_meshing_commands_,
)
from meshing.volume_meshing import (
    build_volume_meshing_commands_,
)


def meshing_commands(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Return the complete lattice meshing command sequence."""
    return (
        ("! --- Lattice meshing pipeline ---",)
        + build_surface_line_meshing_commands_(
            geometry_params,
            profile_params,
            meshing_params,
        )
        + build_surface_area_meshing_commands_(
            geometry_params,
            profile_params,
            meshing_params,
        )
        + build_volume_meshing_commands_(
            unit_cell,
            profile_params,
            meshing_params,
        )
    )
