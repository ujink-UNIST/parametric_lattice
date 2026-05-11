"""Reaction force extraction utilities using MAPDL FSUM."""

from __future__ import annotations

from typing import Dict, Tuple

from core.apdl_commands import ApdlCommands
from core.geometric.select import (
    SELECTOR_TO_NAME,
    get_boundary_nodes,
)


def get_all_face_forces() -> ApdlCommands:
    all_faces = ("+x", "-x", "+y", "-y", "+z", "-z")
    commands: ApdlCommands = ()

    for face in all_faces:
        commands += _get_face_force(face)

    return commands


def _get_face_force(
    selector: str,
) -> ApdlCommands:
    selection = get_boundary_nodes((selector,))
    return selection + (
        "NFORCE",
        "FSUM",
        f"*GET,FX_{SELECTOR_TO_NAME[selector]},FSUM,0,ITEM,FX",
        f"*GET,FY_{SELECTOR_TO_NAME[selector]},FSUM,0,ITEM,FY",
        f"*GET,FZ_{SELECTOR_TO_NAME[selector]},FSUM,0,ITEM,FZ",
        f"*GET,MX_{SELECTOR_TO_NAME[selector]},FSUM,0,ITEM,MX",
        f"*GET,MY_{SELECTOR_TO_NAME[selector]},FSUM,0,ITEM,MY",
        f"*GET,MZ_{SELECTOR_TO_NAME[selector]},FSUM,0,ITEM,MZ",
    )
