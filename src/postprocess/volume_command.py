from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def build_volume_stress_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx
    return (apdl_command("", "TODO(postprocess): compute volume_stress"),)
