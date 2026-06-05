#solve_command.py
"""Module for solve command functionality in src.solve."""

from core.apdl_block import apdl_block
from core.apdl_commands import ApdlCommands


def load_solve_commands_() -> ApdlCommands:
    """Return the APDL commands that solve the model and leave the solver."""
    return apdl_block(
        """
        SOLVE
        FINISH
        """
    )
