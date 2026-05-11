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
    values = {
        "xx": 0.0,
        "yy": 0.0,
        "zz": 0.0,
        "xy": 0.0,
        "yx": 0.0,
        "yz": 0.0,
        "zy": 0.0,
        "xz": 0.0,
        "zx": 0.0,
    }

    if sim_type in ("xy", "yx"):
        values["xy"] = strain
        values["yx"] = strain
    elif sim_type in ("yz", "zy"):
        values["yz"] = strain
        values["zy"] = strain
    elif sim_type in ("xz", "zx"):
        values["xz"] = strain
        values["zx"] = strain
    else:
        values[sim_type] = strain

    keys = (
        "xx",
        "yy",
        "zz",
        "xy",
        "yx",
        "yz",
        "zy",
        "xz",
        "zx",
    )
    return tuple(
        f"*SET,e_{key},{values[key]:.10g}" for key in keys
    )


def select_boundary_nodes_commands(
    component_name: str = "BOUNDARY_NODES",
) -> ApdlCommands:
    return (f"CMSEL,S,{component_name}",)


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


def bc_commands(
    setup_params: SetupParams,
    boundary_component: str = "BOUNDARY_NODES",
) -> ApdlCommands:
    """Dispatch static boundary-condition commands to beam/solid builders."""

    return (
        strain_variable_commands(setup_params)
        + select_boundary_nodes_commands(boundary_component)
        + apply_displacement_loop_commands()
        + ("ALLSEL,ALL",)
    )
