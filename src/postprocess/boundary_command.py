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
    """Compute boundary traction as a 3x3 matrix in MAPDL parameters.

    Definition:
      For each axis A in {X,Y,Z}, compute average traction vector on +A and -A
      periodic faces using nodal reaction force sums:

        tP = FP / A_face
        tN = FN / A_face
        tA = (tP - tN) / 2

      Store into a 3x3 array pp_boundary_traction such that:
        - column = face normal axis (X=1, Y=2, Z=3)
        - row    = traction component (X=1, Y=2, Z=3)

      So pp_boundary_traction(1,1) corresponds to boundary_traction_XX,
      pp_boundary_traction(1,2) to boundary_traction_XY, etc.

    Requirements:
      Node components exist:
        PERIODIC_NODES_PX/NX/PY/NY/PZ/NZ

    Note:
      This function only prepares MAPDL parameters; writing to Excel is handled
      by python (excel_io) after reading these parameters back.
    """

    ax = _face_area(ctx, "X")
    ay = _face_area(ctx, "Y")
    az = _face_area(ctx, "Z")

    cmd: list[str] = []

    cmd += [
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
    ]

    def face_sum(comp: str, tag: str) -> list[str]:
        # tag: e.g. PX, NX ... used for parameter names.
        return [
            apdl_command(f"CMSEL,S,{comp}", f"select {comp}"),
            apdl_command("FSUM", "sum nodal forces"),
            apdl_command(f"*GET,pp_FX_{tag},FSUM,0,ITEM,FX"),
            apdl_command(f"*GET,pp_FY_{tag},FSUM,0,ITEM,FY"),
            apdl_command(f"*GET,pp_FZ_{tag},FSUM,0,ITEM,FZ"),
            apdl_command("ALLSEL,ALL"),
        ]

    # X faces
    cmd += face_sum("PERIODIC_NODES_PX", "PX")
    cmd += face_sum("PERIODIC_NODES_NX", "NX")
    cmd += [
        apdl_command(f"pp_Tx_X = (pp_FX_PX/{ax:g} - pp_FX_NX/{ax:g})/2"),
        apdl_command(f"pp_Ty_X = (pp_FY_PX/{ax:g} - pp_FY_NX/{ax:g})/2"),
        apdl_command(f"pp_Tz_X = (pp_FZ_PX/{ax:g} - pp_FZ_NX/{ax:g})/2"),
        apdl_command("pp_boundary_traction(1,1)=pp_Tx_X"),
        apdl_command("pp_boundary_traction(2,1)=pp_Ty_X"),
        apdl_command("pp_boundary_traction(3,1)=pp_Tz_X"),
    ]

    # Y faces
    cmd += face_sum("PERIODIC_NODES_PY", "PY")
    cmd += face_sum("PERIODIC_NODES_NY", "NY")
    cmd += [
        apdl_command(f"pp_Tx_Y = (pp_FX_PY/{ay:g} - pp_FX_NY/{ay:g})/2"),
        apdl_command(f"pp_Ty_Y = (pp_FY_PY/{ay:g} - pp_FY_NY/{ay:g})/2"),
        apdl_command(f"pp_Tz_Y = (pp_FZ_PY/{ay:g} - pp_FZ_NY/{ay:g})/2"),
        apdl_command("pp_boundary_traction(1,2)=pp_Tx_Y"),
        apdl_command("pp_boundary_traction(2,2)=pp_Ty_Y"),
        apdl_command("pp_boundary_traction(3,2)=pp_Tz_Y"),
    ]

    # Z faces
    cmd += face_sum("PERIODIC_NODES_PZ", "PZ")
    cmd += face_sum("PERIODIC_NODES_NZ", "NZ")
    cmd += [
        apdl_command(f"pp_Tx_Z = (pp_FX_PZ/{az:g} - pp_FX_NZ/{az:g})/2"),
        apdl_command(f"pp_Ty_Z = (pp_FY_PZ/{az:g} - pp_FY_NZ/{az:g})/2"),
        apdl_command(f"pp_Tz_Z = (pp_FZ_PZ/{az:g} - pp_FZ_NZ/{az:g})/2"),
        apdl_command("pp_boundary_traction(1,3)=pp_Tx_Z"),
        apdl_command("pp_boundary_traction(2,3)=pp_Ty_Z"),
        apdl_command("pp_boundary_traction(3,3)=pp_Tz_Z"),
    ]

    return tuple(cmd)


def build_boundary_stress_commands_(ctx: PostprocessContext) -> ApdlCommands:
    _ = ctx
    return (apdl_command("", "TODO(postprocess): compute boundary_stress"),)
