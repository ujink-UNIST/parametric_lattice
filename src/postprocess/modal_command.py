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
