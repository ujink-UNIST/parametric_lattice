#outres_command.py
"""Module for outres command functionality in src.solve."""

from core.apdl_block import apdl_block
from core.apdl_commands import ApdlCommands


def load_outres_commands_() -> ApdlCommands:
    """Return APDL commands that request the solver outputs used downstream."""
    return apdl_block(
        """
        OUTRES,ALL,NONE
        OUTRES,NSOL,ALL
        OUTRES,RSOL,ALL
        OUTRES,NLOAD,ALL
        OUTRES,STRS,ALL
        OUTRES,EPEL,ALL
        OUTRES,VENG,ALL
        """
    )
