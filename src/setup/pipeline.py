# pipeline.py

"""Setup-stage command dispatcher."""

from __future__ import annotations

from core.apdl_commands import ApdlCommands
from core.geometric.select import (
    get_all_boundary_nodes,
    get_all_periodic_nodes,
)
from core.parameters.geometry_params import GeometryParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)
from core.parameters.setup_params import SetupParams
from core.unit_cell import UnitCell
from setup.bc_applicator import bc_commands
from setup.modal_applicator import (
    modal_commands,
    modal_ff_commands,
)


def setup_commands(
    unit_cell: UnitCell,
    profile_params: ProfileParams,
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
        return naming + modal_commands(profile_params)

    return naming + bc_commands(
        profile_params,
        setup_params,
    )
