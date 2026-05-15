from __future__ import annotations

from core.apdl_commands import ApdlCommands, apdl_command
from postprocess.context import PostprocessContext


def build_boundary_force_moment_commands_(ctx: PostprocessContext) -> ApdlCommands:
    """Compute boundary resultant force/moment as 3x3 matrices.

    Convention for both outputs (matches requested Excel naming):
      - first index: face normal axis  (X=1, Y=2, Z=3)
      - second index: vector component (X=1, Y=2, Z=3)

    So:
      pp_boundary_force(1,2)  => boundary_force_XY (Y-force associated with X-faces)
      pp_boundary_moment(3,1) => boundary_moment_ZX (X-moment associated with Z-faces)

    We compute per-axis resultant using periodic face components:
      F_A = (F_{+A} - F_{-A})/2
      M_A = (M_{+A} - M_{-A})/2

    Requirements:
      Node components exist:
        PERIODIC_NODES_PX/NX/PY/NY/PZ/NZ
    """

    _ = ctx

    cmd: list[str] = [
        apdl_command("/POST1", "postprocess: boundary force/moment"),
        apdl_command("SET,LAST", "use last substep"),
        apdl_command("ALLSEL,ALL"),
        apdl_command(
            "*DIM,pp_boundary_force,ARRAY,3,3",
            "(rows: face X/Y/Z, cols: force X/Y/Z)",
        ),
        apdl_command(
            "*DIM,pp_boundary_moment,ARRAY,3,3",
            "(rows: face X/Y/Z, cols: moment X/Y/Z)",
        ),
    ]

    def face_sum(comp: str, tag: str) -> list[str]:
        return [
            apdl_command(f"CMSEL,S,{comp}", f"select {comp}"),
            apdl_command("FSUM", "sum nodal forces"),
            apdl_command(f"*GET,pp_FX_{tag},FSUM,0,ITEM,FX"),
            apdl_command(f"*GET,pp_FY_{tag},FSUM,0,ITEM,FY"),
            apdl_command(f"*GET,pp_FZ_{tag},FSUM,0,ITEM,FZ"),
            apdl_command(f"*GET,pp_MX_{tag},FSUM,0,ITEM,MX"),
            apdl_command(f"*GET,pp_MY_{tag},FSUM,0,ITEM,MY"),
            apdl_command(f"*GET,pp_MZ_{tag},FSUM,0,ITEM,MZ"),
            apdl_command("ALLSEL,ALL"),
        ]

    # X faces
    cmd += face_sum("PERIODIC_NODES_PX", "PX")
    cmd += face_sum("PERIODIC_NODES_NX", "NX")
    cmd += [
        apdl_command("pp_boundary_force(1,1)=(pp_FX_PX-pp_FX_NX)/2"),
        apdl_command("pp_boundary_force(1,2)=(pp_FY_PX-pp_FY_NX)/2"),
        apdl_command("pp_boundary_force(1,3)=(pp_FZ_PX-pp_FZ_NX)/2"),
        apdl_command("pp_boundary_moment(1,1)=(pp_MX_PX-pp_MX_NX)/2"),
        apdl_command("pp_boundary_moment(1,2)=(pp_MY_PX-pp_MY_NX)/2"),
        apdl_command("pp_boundary_moment(1,3)=(pp_MZ_PX-pp_MZ_NX)/2"),
    ]

    # Y faces
    cmd += face_sum("PERIODIC_NODES_PY", "PY")
    cmd += face_sum("PERIODIC_NODES_NY", "NY")
    cmd += [
        apdl_command("pp_boundary_force(2,1)=(pp_FX_PY-pp_FX_NY)/2"),
        apdl_command("pp_boundary_force(2,2)=(pp_FY_PY-pp_FY_NY)/2"),
        apdl_command("pp_boundary_force(2,3)=(pp_FZ_PY-pp_FZ_NY)/2"),
        apdl_command("pp_boundary_moment(2,1)=(pp_MX_PY-pp_MX_NY)/2"),
        apdl_command("pp_boundary_moment(2,2)=(pp_MY_PY-pp_MY_NY)/2"),
        apdl_command("pp_boundary_moment(2,3)=(pp_MZ_PY-pp_MZ_NY)/2"),
    ]

    # Z faces
    cmd += face_sum("PERIODIC_NODES_PZ", "PZ")
    cmd += face_sum("PERIODIC_NODES_NZ", "NZ")
    cmd += [
        apdl_command("pp_boundary_force(3,1)=(pp_FX_PZ-pp_FX_NZ)/2"),
        apdl_command("pp_boundary_force(3,2)=(pp_FY_PZ-pp_FY_NZ)/2"),
        apdl_command("pp_boundary_force(3,3)=(pp_FZ_PZ-pp_FZ_NZ)/2"),
        apdl_command("pp_boundary_moment(3,1)=(pp_MX_PZ-pp_MX_NZ)/2"),
        apdl_command("pp_boundary_moment(3,2)=(pp_MY_PZ-pp_MY_NZ)/2"),
        apdl_command("pp_boundary_moment(3,3)=(pp_MZ_PZ-pp_MZ_NZ)/2"),
    ]

    return tuple(cmd)
