# modal_applicator.py

"""Modal-analysis setup command builder."""

from __future__ import annotations
from typing import Tuple

from core.apdl_commands import ApdlCommands
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)

TANGENT_AXIS = {
    "X": ("Y", "Z"),
    "Y": ("X", "Z"),
    "Z": ("X", "Y"),
}


def modal_ff_commands() -> ApdlCommands:
    """Return setup commands for free-free modal analysis.

    Free-free modal analysis applies no displacement constraints.
    """
    return ()


def periodic_component_name(face: str) -> str:
    """Return periodic node component name for a face string like '+X', '-Y'."""
    sign = "P" if face.startswith("+") else "N"
    axis = face[-1].upper()
    return f"PERIODIC_NODES_{sign}{axis}"


def select_periodic_nodes_commands(
    face: str,
) -> ApdlCommands:
    """Select precomputed periodic nodes for a given face."""
    return (f"CMSEL,S,{periodic_component_name(face)}",)


def _face_pair_periodic_commands(
    negative_cm: str,
    positive_cm: str,
    axis: str,
    ce_dofs: tuple[str, ...],
) -> ApdlCommands:
    """Return APDL commands tying one pair of opposite precomputed periodic faces."""
    tangent_a, tangent_b = TANGENT_AXIS[axis]

    plus_node = f"_NP_{axis}_"
    minus_node = f"_NM_{axis}_"
    count_var = f"_NCOUNT_{axis}_"
    loop_var = f"_I_{axis}_"
    tangent_a_var = f"_{tangent_a}_{axis}_"
    tangent_b_var = f"_{tangent_b}_{axis}_"
    active_cm = f"PBC_{axis}"

    # ce_dofs = ("UX", "UY", "UZ", "ROTX", "ROTY", "ROTZ")

    ce_commands: ApdlCommands = tuple(
        f"CE,NEXT,0,{plus_node},{dof},1,{minus_node},{dof},-1"
        for dof in ce_dofs
    )

    return (
        f"! Periodic constraints for {positive_cm}/{negative_cm}",
        f"CMSEL,S,{positive_cm}",
        f"CM,{active_cm},NODE",
        f"*GET,{count_var},NODE,0,COUNT",
        f"*DO,{loop_var},1,{count_var}",
        f"CMSEL,S,{active_cm}",
        f"*GET,{plus_node},NODE,0,NUM,MIN",
        f"*GET,{tangent_a_var},NODE,{plus_node},LOC,{tangent_a}",
        f"*GET,{tangent_b_var},NODE,{plus_node},LOC,{tangent_b}",
        f"CMSEL,S,{negative_cm}",
        f"NSEL,R,LOC,{tangent_a},{tangent_a_var}",
        f"NSEL,R,LOC,{tangent_b},{tangent_b_var}",
        f"*GET,{minus_node},NODE,0,NUM,MIN",
        *ce_commands,
        f"CMSEL,S,{active_cm}",
        f"NSEL,U,NODE,,{plus_node}",
        f"CM,{active_cm},NODE",
        "*ENDDO",
        "ALLSEL,ALL",
    )


def modal_commands(
    profile_params: ProfileParams,
) -> ApdlCommands:
    """Return periodic boundary-condition commands for modal analysis."""

    cmds: ApdlCommands = ()

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

    for axis in ("X", "Y", "Z"):
        cmds += _face_pair_periodic_commands(
            f"PERIODIC_NODES_N{axis}",
            f"PERIODIC_NODES_P{axis}",
            axis,
            ce_dofs,
        )
    return cmds
