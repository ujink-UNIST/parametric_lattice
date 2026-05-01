# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\lattice_volume_meshing.py
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
from meshing.beam_volume_meshing import (
    build_beam_volume_meshing_commands_,
)


def build_lattice_volume_meshing_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    meshing_params: MeshingParams,
    material_params: MaterialParams,
) -> ApdlCommands:
    """Return volume-meshing commands for the lattice model."""
    return build_beam_volume_meshing_commands_(
        unit_cell,
        geometry_params,
        meshing_params,
        material_params,
    )
