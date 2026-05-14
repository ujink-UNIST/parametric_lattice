# solve_command.py

from core.apdl_commands import ApdlCommands


def load_solve_commands_() -> ApdlCommands:
    """Return the APDL commands that solve the model and leave the solver."""
    return (
        "SOLVE",
        "FINISH",
    )
