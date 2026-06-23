#pipeline.py
"""Module for pipeline functionality in src.solve."""

from core.apdl_block import apdl_section
from core.apdl_commands import ApdlCommands
from core.parameters.setup_params import SetupParams
from solve.outres_command import load_outres_commands_
from solve.solve_command import load_solve_commands_
from solve.analysis_settings_command import (
    load_modal_settings_command_,
    load_static_settings_command_,
)
from solve.substep_command import load_substep_commands


def solver_commands(
    setup_params: SetupParams,
    nlgeom: bool = False,
    nsubst: int = 1,
    *,
    modal_n_modes: int = 10,
) -> ApdlCommands:
    """Return the full solution-stage APDL pipeline for one simulation case."""
    sim_type = setup_params.sim_type
    if sim_type in ("modal", "modal_ff"):
        return (
            (apdl_section("SOLUTION PIPELINE"),)
            + load_modal_settings_command_(
                n_modes=modal_n_modes
            )
            + load_solve_commands_()
        )
    return (
        (apdl_section("SOLUTION PIPELINE"),)
        + load_static_settings_command_(nlgeom)
        + load_outres_commands_()
        + load_substep_commands(nsubst)
        + load_solve_commands_()
    )
