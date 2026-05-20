from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def build_volume_stress_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx
    return (apdl_command("", "TODO(postprocess): compute volume_stress"),)


def build_volume_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Compute total volume of all selected elements.

    Output MAPDL parameters:
      - pp_volume: scalar

    Notes:
      - Uses ETABLE item VOLU (element volume). This should work for solid
        elements and for element types where MAPDL reports VOLU.
    """

    _ = ctx

    cmd: list[str] = [
        apdl_command("/POST1", "postprocess: total volume"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL"),
        apdl_command("ESEL,ALL"),
        apdl_command("ETABLE,pp__VOLU,VOLU", "element volume"),
        apdl_command("pp_volume=0", "init total volume"),
        apdl_command("*GET,pp__eid,ELEM,0,NUM,MIN", "first selected element"),
        apdl_command("*DOWHILE,pp__eid,GT,0"),
        apdl_command("  *GET,pp__evol,ELEM,pp__eid,ETAB,pp__VOLU", "element volume"),
        apdl_command("  pp_volume=pp_volume+pp__evol", "accumulate"),
        apdl_command("  *GET,pp__eid,ELEM,pp__eid,NXTH"),
        apdl_command("*ENDDO"),
        apdl_command("ALLSEL,ALL"),
    ]

    return tuple(cmd)
