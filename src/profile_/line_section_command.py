# line_section_command.py

from __future__ import annotations

from core.apdl_commands import ApdlCommands


def build_line_section_commands_(
    *,
    edge_sec_ids: tuple[int, ...] | list[int],
    orientation_keypoint_start: int,
) -> ApdlCommands:
    """Assign section ids to line ids.

    This helper is intentionally small/pure so unit tests can validate the exact
    APDL emitted.
    """

    cmds: list[str] = []
    for i, sec_id in enumerate(edge_sec_ids, start=1):
        kb_n = orientation_keypoint_start + i
        cmds.extend(
            (
                f"! Assign section {sec_id} to beam line {i}",
                f"LSEL,S,LINE,,{i}",
                f"LATT,1,,1,,{kb_n},,{sec_id}",
            )
        )

    cmds.append("LSEL,ALL")
    return tuple(cmds)
