# File: c:\Users\USER\Documents\parametric_lattice\src\solve\solve_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from core.apdl_commands import ApdlCommands


def load_solve_commands_() -> ApdlCommands:
    """Return the APDL commands that solve the model and leave the solver."""
    return (
        "SOLVE",
        "FINISH",
    )
