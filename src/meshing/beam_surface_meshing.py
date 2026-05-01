# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\beam_surface_meshing.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


"""Beam surface meshing command builders."""

from __future__ import annotations

from core.apdl_commands import ApdlCommands
from core.parameters.meshing_params import MeshingParams
from core.unit_cell import UnitCell


def build_beam_surface_meshing_commands(
    unit_cell: UnitCell, meshing_params: MeshingParams
) -> ApdlCommands:
    """Return beam surface meshing commands.

    Beam elements have no independent surface mesh stage, so this is a no-op.
    """
    del unit_cell, meshing_params
    return (
        "! Beam surface meshing stage: no surface mesh required",
    )
