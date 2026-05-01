# File: c:\Users\USER\Documents\parametric_lattice\src\solve\outres_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from core.apdl_commands import ApdlCommands


def load_outres_commands_() -> ApdlCommands:
    """Return APDL commands that request the solver outputs used downstream."""
    return (
        "OUTRES,ALL,NONE",
        "OUTRES,NSOL,ALL",
        "OUTRES,RSOL,ALL",
        "OUTRES,NLOAD,ALL",
        "OUTRES,STRS,ALL",
        "OUTRES,EPEL,ALL",
        "OUTRES,SENE,ALL",
        "OUTRES,VENG,ALL",
    )
