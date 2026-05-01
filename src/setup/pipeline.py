# File: c:\Users\USER\Documents\parametric_lattice\src\setup\pipeline.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


"""Setup-stage command dispatcher."""

from __future__ import annotations

from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.geometric.select import (
    get_all_boundary_nodes,
    get_all_periodic_nodes,
)
from core.parameters.geometry_params import GeometryParams
from core.parameters.setup_params import SetupParams
from setup.bc_applicator import bc_commands
from setup.modal_applicator import (
    modal_commands,
    modal_ff_commands,
)


def setup_commands(
    geometry_params: GeometryParams,
    setup_params: SetupParams,
) -> ApdlCommands:
    """Return setup commands for the selected analysis path."""
    key = setup_params.sim_type

    naming: ApdlCommands = get_all_boundary_nodes(
        geometry_params
    ) + get_all_periodic_nodes(geometry_params)

    if key == "modal_ff":
        return naming + modal_ff_commands()
    if key == "modal":
        return naming + modal_commands()

    return naming + bc_commands(setup_params)
