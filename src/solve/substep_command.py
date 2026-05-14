# substep_command.py

from core.apdl_commands import ApdlCommands


def load_substep_commands(nsubst: int = 1) -> ApdlCommands:
    """Return APDL commands that configure the load-step discretization."""
    return (
        f"NSUBST,{nsubst},1,1",
        "TIME,1.0",
    )
