#apdl_commands.py
"""Module for apdl commands functionality in src.core."""

from typing import Tuple

from ansys.mapdl.core.mapdl_console import MapdlConsole
from ansys.mapdl.core.mapdl_grpc import MapdlGrpc

Mapdl = MapdlGrpc | MapdlConsole

ApdlCommands = Tuple[str, ...]
"""Immutable tuple of APDL command strings that can be concatenated safely."""


COMMENT_STOPS = (32, 48, 64, 80, 96, 112)


def _comment_column(code_len: int) -> int:
    for stop in COMMENT_STOPS:
        if code_len < stop:
            return stop

    return COMMENT_STOPS[-1]


def apdl_command(
    code: str,
    comment: str | None = None,
) -> str:
    code = code.rstrip()
    if comment is None:
        return code
    if not code:
        return f"! {comment.rstrip()}"

    column = _comment_column(len(code))
    return f"{code:<{column}}! {comment.rstrip()}"
