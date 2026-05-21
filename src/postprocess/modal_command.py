from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def build_resonant_frequency_command_(
    ctx: PostprocessContext,
    *,
    mode_index: int,
) -> ApdlCommands:
    """Extract resonant frequency for a single mode.

    Produces MAPDL scalar parameter:
      pp_res_freq_<mode_index>

    Notes:
      - Requires a modal results file to be attached in POST1.
      - Uses *GET,...,MODE,<i>,FREQ.
    """

    _ = ctx

    i = int(mode_index)
    return (
        apdl_command("", f"postprocess: resonant frequency (mode {i})"),
        apdl_command(f"*GET,pp_res_freq_{i},MODE,{i},FREQ", f"mode {i} freq"),
    )


def build_modal_participation_commands_(
    ctx: PostprocessContext,
    *,
    mode_index: int,
) -> ApdlCommands:
    """Extract modal participation factors (X/Y/Z) for a single mode.

    Produces MAPDL scalar parameters:
      pp_part_factor_<i>_X, _Y, _Z

    Uses *GET,...,MODE,i,PFAC,<dir>.
    """

    _ = ctx
    i = int(mode_index)
    return (
        apdl_command("", f"postprocess: participation factors (mode {i})"),
        apdl_command(f"*GET,pp_part_factor_{i}_X,MODE,{i},PFAC,X"),
        apdl_command(f"*GET,pp_part_factor_{i}_Y,MODE,{i},PFAC,Y"),
        apdl_command(f"*GET,pp_part_factor_{i}_Z,MODE,{i},PFAC,Z"),
    )


def build_modal_effective_mass_commands_(
    ctx: PostprocessContext,
    *,
    mode_index: int,
) -> ApdlCommands:
    """Extract effective modal mass (X/Y/Z) for a single mode.

    Produces MAPDL scalar parameters:
      pp_eff_modal_mass_<i>_X, _Y, _Z

    Uses *GET,...,MODE,i,EFFM,<dir>.
    """

    _ = ctx
    i = int(mode_index)
    return (
        apdl_command("", f"postprocess: effective modal mass (mode {i})"),
        apdl_command(f"*GET,pp_eff_modal_mass_{i}_X,MODE,{i},EFFM,X"),
        apdl_command(f"*GET,pp_eff_modal_mass_{i}_Y,MODE,{i},EFFM,Y"),
        apdl_command(f"*GET,pp_eff_modal_mass_{i}_Z,MODE,{i},EFFM,Z"),
    )
