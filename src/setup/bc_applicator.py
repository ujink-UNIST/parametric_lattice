# bc_applicator.py

"""Boundary-condition command builders for beam and solid models."""

from __future__ import annotations


from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)
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


def apply_displacement_loop_commands(
    ce_dofs: tuple[str, ...],
) -> ApdlCommands:
    ce_commands: ApdlCommands = tuple(
        f"D,_NID_BC_,{dof},0" for dof in ce_dofs
    )

    return (
        "CMSEL,S,BOUNDARY_NODES",
        f"*GET,_NCOUNT_BC_,NODE,0,COUNT",
        f"*DO,_I_BC_,1,_NCOUNT_BC_",
        f"*GET,_NID_BC_,NODE,0,NUM,MIN",
        f"*GET,_X0_BC_,NODE,_NID_BC_,LOC,X",
        f"*GET,_Y0_BC_,NODE,_NID_BC_,LOC,Y",
        f"*GET,_Z0_BC_,NODE,_NID_BC_,LOC,Z",
        f"_UX_BC_=e_xx*_X0_BC_+e_xy*_Y0_BC_+e_xz*_Z0_BC_",
        f"_UY_BC_=e_yx*_X0_BC_+e_yy*_Y0_BC_+e_yz*_Z0_BC_",
        f"_UZ_BC_=e_zx*_X0_BC_+e_zy*_Y0_BC_+e_zz*_Z0_BC_",
        f"D,_NID_BC_,UX,_UX_BC_",
        f"D,_NID_BC_,UY,_UY_BC_",
        f"D,_NID_BC_,UZ,_UZ_BC_",
        *ce_commands,
        "! Remove the current node so the next NUM,MIN query advances.",
        f"NSEL,U,NODE,,_NID_BC_",
        "*ENDDO",
    )


def bc_commands(
    profile_params: ProfileParams,
    setup_params: SetupParams,
    # boundary_component: str = "BOUNDARY_NODES",
) -> ApdlCommands:
    """Dispatch static boundary-condition commands to beam/solid builders."""

    ce_dofs = (
        "UX",
        "UY",
        "UZ",
    )

    if isinstance(profile_params, BeamProfileParams):
        ce_dofs += (
            "ROTX",
            "ROTY",
            "ROTZ",
        )

    return (
        strain_variable_commands(setup_params)
        + apply_displacement_loop_commands(ce_dofs)
        + ("ALLSEL,ALL",)
    )
