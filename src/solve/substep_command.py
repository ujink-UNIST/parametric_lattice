# substep_command.py

from core.apdl_block import apdl_block
from core.apdl_commands import ApdlCommands


def load_substep_commands(nsubst: int = 1) -> ApdlCommands:
    """Return APDL commands that configure the load-step discretization."""
    return apdl_block(
        f"""
        NSUBST,{int(nsubst)},1,1
        TIME,1.0
        """
    )
