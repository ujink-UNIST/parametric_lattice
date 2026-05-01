# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\lattice_surface_meshing.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from __future__ import annotations

from core.apdl_commands import ApdlCommands
from core.parameters.meshing_params import MeshingParams
from core.unit_cell import UnitCell
from meshing.beam_surface_meshing import (
    build_beam_surface_meshing_commands,
)


def build_lattice_surface_meshing_commands_(
    unit_cell: UnitCell, meshing_params: MeshingParams
) -> ApdlCommands:
    """Return surface-meshing commands for the lattice model."""
    return build_beam_surface_meshing_commands(
        unit_cell, meshing_params
    )
