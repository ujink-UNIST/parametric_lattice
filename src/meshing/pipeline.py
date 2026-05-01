# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\pipeline.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from __future__ import annotations

from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams
from core.unit_cell import UnitCell
from meshing.lattice_surface_meshing import (
    build_lattice_surface_meshing_commands_,
)
from meshing.lattice_volume_meshing import (
    build_lattice_volume_meshing_commands_,
)


def meshing_commands(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    meshing_params: MeshingParams,
    material_params: MaterialParams,
) -> ApdlCommands:
    """Return the complete lattice meshing command sequence."""
    return (
        ("! --- Lattice meshing pipeline ---",)
        + build_lattice_surface_meshing_commands_(
            unit_cell, meshing_params
        )
        + build_lattice_volume_meshing_commands_(
            unit_cell,
            geometry_params,
            meshing_params,
            material_params,
        )
    )
