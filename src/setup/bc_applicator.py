# File: c:\Users\USER\Documents\parametric_lattice\src\setup\bc_applicator.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


"""Boundary-condition command builders for beam and solid models."""

from __future__ import annotations


from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.setup_params import SetupParams


def strain_variable_commands(
    setup_params: SetupParams,
) -> ApdlCommands:
    sim_type = setup_params.sim_type
    strain = setup_params.strain
    keys = ("xx", "yy", "zz", "xy", "yz", "xz")

    return tuple(
        (
            f"*SET,e_{k},{strain:.10g}"
            if k == sim_type
            else f"*SET,e_{k},0"
        )
        for k in keys
    )


def select_all_boundary_nodes_commands() -> ApdlCommands:
    return ("CMSEL,S,BOUNDARY_NODES",)


def apply_displacement_loop_commands(
    has_rotation_dof: bool = False,
) -> ApdlCommands:
    """Apply affine displacement boundary conditions to the currently selected nodes."""
    LOOP_VAR = "_I_BC_"
    COUNT_VAR = "_NCOUNT_BC_"
    NODE_VAR = "_NID_BC_"
    X_VAR = "_X0_BC_"
    Y_VAR = "_Y0_BC_"
    Z_BAR = "_Z0_BC_"
    UX_VAR = "_UX_BC_"
    UY_VAR = "_UY_BC_"
    UZ_VAR = "_UZ_BC_"

    rot_cmds = (
        (
            f"D,{NODE_VAR},ROTX,0",
            f"D,{NODE_VAR},ROTY,0",
            f"D,{NODE_VAR},ROTZ,0",
        )
        if has_rotation_dof
        else ()
    )

    return (
        f"*GET,{COUNT_VAR},NODE,0,COUNT",
        f"*DO,{LOOP_VAR},1,{COUNT_VAR}",
        f"*GET,{NODE_VAR},NODE,0,NUM,MIN",
        f"*GET,{X_VAR},NODE,{NODE_VAR},LOC,X",
        f"*GET,{Y_VAR},NODE,{NODE_VAR},LOC,Y",
        f"*GET,{Z_BAR},NODE,{NODE_VAR},LOC,Z",
        f"{UX_VAR}=e_xx*{X_VAR}+e_xy*{Y_VAR}+e_xz*{Z_BAR}",
        f"{UY_VAR}=e_yx*{X_VAR}+e_yy*{Y_VAR}+e_yz*{Z_BAR}",
        f"{UZ_VAR}=e_zx*{X_VAR}+e_zy*{Y_VAR}+e_zz*{Z_BAR}",
        f"D,{NODE_VAR},UX,{UX_VAR}",
        f"D,{NODE_VAR},UY,{UY_VAR}",
        f"D,{NODE_VAR},UZ,{UZ_VAR}",
        *rot_cmds,
        "! Remove the current node so the next NUM,MIN query advances.",
        f"NSEL,U,NODE,,{NODE_VAR}",
        "*ENDDO",
    )


def bc_commands(setup_params: SetupParams) -> ApdlCommands:
    """Dispatch static boundary-condition commands to beam/solid builders."""

    return (
        strain_variable_commands(setup_params)
        + select_all_boundary_nodes_commands()
        + apply_displacement_loop_commands()
        + ("ALLSET,ALL",)
    )
