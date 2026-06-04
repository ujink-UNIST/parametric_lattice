# line_section_command.py

from __future__ import annotations

from core.apdl_commands import ApdlCommands


def build_line_section_commands_(
    *,
    edge_sec_ids: tuple[int, ...] | list[int],
    orientation_keypoint_start: int,
) -> ApdlCommands:
    """Assign section ids to beam line ids.

    Line numbering convention (see geometry.line_command):
      1..E : one line per original lattice edge

    Orientation keypoints are still generated but currently not assigned in LATT.
    """

    _ = orientation_keypoint_start

    cmds: list[str] = []

    for edge_i0, sec_id in enumerate(edge_sec_ids, start=1):
        cmds.extend(
            (
                f"! Edge {edge_i0}: beam section {sec_id}",
                f"LSEL,S,LINE,,{edge_i0}",
                f"LATT,1,,1,,,,{sec_id}",
            )
        )

    cmds.append("LSEL,ALL")
    return tuple(cmds)
