# analysis_settings_command.py

"""APDL command builders for the solution stage."""

from __future__ import annotations

from core.apdl_block import apdl_block
from core.apdl_commands import ApdlCommands


def load_modal_settings_command_(
    n_modes: int,
) -> ApdlCommands:
    """Return APDL commands that enter the solver and configure analysis type."""

    return apdl_block(
        f"""
        /SOLU
        ANTYPE,MODAL
        MODOPT,LANB,{int(n_modes)}
        MXPAND,{int(n_modes)},,,,YES
        """
    )


def load_static_settings_command_(
    nlgeom: bool,
) -> ApdlCommands:
    return apdl_block(
        f"""
        /SOLU
        ANTYPE,STATIC
        NLGEOM,{"ON" if nlgeom else "OFF"}
        """
    )
