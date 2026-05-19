from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def _face_area(ctx: PostprocessContext, axis: str) -> float:
    size = ctx.sim_case.pre_mesh_spec.geometry.size
    sx, sy, sz = float(size[0]), float(size[1]), float(size[2])
    if axis == "X":
        return sy * sz
    if axis == "Y":
        return sx * sz
    if axis == "Z":
        return sx * sy
    raise ValueError(f"Unknown axis {axis!r}")


def build_boundary_traction_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Compute boundary traction from `pp_boundary_force`.

    Dependency:
      This output depends on `boundary_force` having run first, which defines
      `pp_boundary_force(face, comp)` where face={X,Y,Z} and comp={X,Y,Z}.

    Definition:
      traction(face, comp) = boundary_force(face, comp) / A_face

    Storage:
      pp_boundary_traction(comp, face) is kept for backward compatibility with
      existing Excel naming (boundary_traction_XX..ZZ):
        - row    = traction component (X=1, Y=2, Z=3)
        - column = face normal axis (X=1, Y=2, Z=3)
    """

    ax = _face_area(ctx, "X")
    ay = _face_area(ctx, "Y")
    az = _face_area(ctx, "Z")

    cmd: list[str] = [
        apdl_command("/POST1", "postprocess: boundary traction"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL"),
        apdl_command(
            "*DIM,pp_boundary_traction,ARRAY,3,3",
            "(rows: traction X/Y/Z, cols: face X/Y/Z)",
        ),
        apdl_command(
            f"! Face areas from geometry.size: AX={ax:g}, AY={ay:g}, AZ={az:g}"
        ),
        apdl_command("! traction on X faces from pp_boundary_force row 1"),
        apdl_command(f"pp_boundary_traction(1,1)=pp_boundary_force(1,1)/{ax:g}"),
        apdl_command(f"pp_boundary_traction(2,1)=pp_boundary_force(1,2)/{ax:g}"),
        apdl_command(f"pp_boundary_traction(3,1)=pp_boundary_force(1,3)/{ax:g}"),
        apdl_command("! traction on Y faces from pp_boundary_force row 2"),
        apdl_command(f"pp_boundary_traction(1,2)=pp_boundary_force(2,1)/{ay:g}"),
        apdl_command(f"pp_boundary_traction(2,2)=pp_boundary_force(2,2)/{ay:g}"),
        apdl_command(f"pp_boundary_traction(3,2)=pp_boundary_force(2,3)/{ay:g}"),
        apdl_command("! traction on Z faces from pp_boundary_force row 3"),
        apdl_command(f"pp_boundary_traction(1,3)=pp_boundary_force(3,1)/{az:g}"),
        apdl_command(f"pp_boundary_traction(2,3)=pp_boundary_force(3,2)/{az:g}"),
        apdl_command(f"pp_boundary_traction(3,3)=pp_boundary_force(3,3)/{az:g}"),
    ]

    return tuple(cmd)


def build_boundary_stress_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx
    return (apdl_command("", "TODO(postprocess): compute boundary_stress"),)
