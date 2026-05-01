# File: c:\Users\USER\Documents\parametric_lattice\src\solve\substep_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from core.apdl_commands import ApdlCommands


def load_substep_commands(nsubst: int = 1) -> ApdlCommands:
    """Return APDL commands that configure the load-step discretization."""
    return (
        f"NSUBST,{nsubst},1,1",
        "TIME,1.0",
    )
