#substep_command.py
"""Module for substep command functionality in src.solve."""

from core.apdl_block import apdl_block, apdl_section
from core.apdl_commands import ApdlCommands


def load_substep_commands(nsubst: int = 1) -> ApdlCommands:
    """Return APDL commands that configure the load-step discretization."""
    return (apdl_section("LOAD STEP CONTROLS"),) + apdl_block(
        f"""
        ! Use a fixed number of substeps for reproducible result sampling.
        NSUBST,{int(nsubst)},1,1
        ! Normalize the load-step end time to 1.0.
        TIME,1.0
        """
    )
