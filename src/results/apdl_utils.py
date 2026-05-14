# apdl_utils.py

"""Shared APDL command-running and logging utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

from io_utils import apdl_io


def append_apdl_log(log_path: Optional[Path], commands: Tuple[str, ...]) -> None:
    """Append APDL command strings to the case log file when provided."""
    if log_path is None:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        for cmd in commands:
            f.write(cmd.rstrip("\r\n") + "\n")


def run_commands(
    mapdl,
    commands: Tuple[str, ...],
    *,
    log_path: Optional[Path] = None,
) -> None:
    """Run APDL commands and mirror them to the case APDL log when available."""
    append_apdl_log(log_path, commands)
    apdl_io.run_commands(mapdl, commands)
