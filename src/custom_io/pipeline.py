#pipeline.py
"""Module for pipeline functionality in src.custom_io."""

from __future__ import annotations

from typing import Any

from core.apdl_commands import ApdlCommands
from custom_io import apdl_io


def run_apdl_commands(
    commands: ApdlCommands,
    **launch_kwargs: Any,
) -> None:
    mapdl = apdl_io.start_mapdl(**launch_kwargs)
    apdl_io.run_commands(mapdl, commands)
    apdl_io.stop_mapdl(mapdl)
