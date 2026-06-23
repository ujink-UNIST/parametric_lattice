#analysis_settings_command.py
"""APDL command builders for the solution stage."""

from __future__ import annotations

from core.apdl_block import apdl_block, apdl_section
from core.apdl_commands import ApdlCommands


def load_modal_settings_command_(
    n_modes: int,
) -> ApdlCommands:
    """Return APDL commands that enter the solver and configure analysis type."""

    return (apdl_section("MODAL ANALYSIS SETTINGS"),) + apdl_block(
        f"""
        ! Enter the solution processor.
        /SOLU
        ! Select modal analysis and use the Block Lanczos eigensolver.
        ANTYPE,MODAL
        MODOPT,LANB,{int(n_modes)}
        ! Expand mode shapes so downstream post-processing can read them.
        MXPAND,{int(n_modes)},,,,YES
        """
    )


def load_static_settings_command_(
    nlgeom: bool,
) -> ApdlCommands:
    return (apdl_section("STATIC ANALYSIS SETTINGS"),) + apdl_block(
        f"""
        ! Enter the solution processor.
        /SOLU
        ! Select a static structural analysis.
        ANTYPE,STATIC
        ! Enable or disable large-deformation effects for this load step.
        NLGEOM,{"ON" if nlgeom else "OFF"}
        """
    )
