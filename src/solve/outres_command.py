#outres_command.py
"""Module for outres command functionality in src.solve."""

from core.apdl_block import apdl_block, apdl_section
from core.apdl_commands import ApdlCommands


def load_outres_commands_() -> ApdlCommands:
    """Return APDL commands that request the solver outputs used downstream."""
    return (apdl_section("RESULT OUTPUT REQUESTS"),) + apdl_block(
        """
        ! Start from a clean output request set.
        OUTRES,ALL,NONE
        ! Store nodal displacements and rotations at every substep.
        OUTRES,NSOL,ALL
        ! Store reaction forces for boundary-condition post-processing.
        OUTRES,RSOL,ALL
        ! Store applied nodal loads when present.
        OUTRES,NLOAD,ALL
        ! Store element stresses and elastic strains.
        OUTRES,STRS,ALL
        OUTRES,EPEL,ALL
        ! Store element energy terms used by derived metrics.
        OUTRES,VENG,ALL
        """
    )
