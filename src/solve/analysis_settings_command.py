# File: c:\Users\USER\Documents\parametric_lattice\src\solve\analysis_settings_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


"""APDL command builders for the solution stage."""

from __future__ import annotations

from core.apdl_commands import ApdlCommands


def load_modal_settings_command_(
    n_modes: int,
) -> ApdlCommands:
    """Return APDL commands that enter the solver and configure analysis type."""

    return (
        "/SOLU",
        "ANTYPE,MODAL",
        f"MODOPT,LANB,{int(n_modes)}",
        f"MXPAND,{int(n_modes)},,,,YES",
    )


def load_static_settings_command_(
    nlgeom: bool,
) -> ApdlCommands:
    return (
        "/SOLU",
        "ANTYPE,STATIC",
        f"NLGEOM,{'ON' if nlgeom else 'OFF'}",
    )
