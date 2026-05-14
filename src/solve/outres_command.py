# outres_command.py

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
        "OUTRES,VENG,ALL",
    )
