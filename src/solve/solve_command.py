#solve_command.py
"""Module for solve command functionality in src.solve."""

from core.apdl_block import apdl_block, apdl_section
from core.apdl_commands import ApdlCommands


def load_solve_commands_() -> ApdlCommands:
    """Return the APDL commands that solve the model and leave the solver."""
    return (apdl_section("SOLVE"),) + apdl_block(
        """
        ! Run the configured analysis.
        SOLVE
        ! Leave the solution processor after the solve completes.
        FINISH
        """
    )
