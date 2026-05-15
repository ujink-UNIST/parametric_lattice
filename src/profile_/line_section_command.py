# line_section_command.py

from __future__ import annotations

from core.apdl_commands import ApdlCommands


def build_line_section_commands_(
    *,
    edge_sec_ids: tuple[int, ...] | list[int],
    edge_joint_sec_ids: tuple[int, ...] | list[int],
    orientation_keypoint_start: int,
) -> ApdlCommands:
    """Assign section ids to beam line ids.

    Line numbering convention (see geometry.line_command):
      1..E       : mid segments (normal)
      E+1..2E    : start segments (joint)
      2E+1..3E   : end segments (joint)

    Orientation keypoints are 2 per edge (n,b). Here we use the edge's normal
    keypoint id: orientation_keypoint_start + 2*i - 1.
    """

    if len(edge_sec_ids) != len(edge_joint_sec_ids):
        raise ValueError(
            "edge_sec_ids and edge_joint_sec_ids lengths differ: "
            f"{len(edge_sec_ids)} != {len(edge_joint_sec_ids)}"
        )

    cmds: list[str] = []
    n_edges = len(edge_sec_ids)

    for edge_i0, (sec_mid, sec_joint) in enumerate(
        zip(edge_sec_ids, edge_joint_sec_ids), start=1
    ):
        kb_n = orientation_keypoint_start + 2 * edge_i0 - 1

        line_mid = edge_i0
        line_start = n_edges + edge_i0
        line_end = 2 * n_edges + edge_i0

        cmds.extend(
            (
                f"! Edge {edge_i0}: mid segment section {sec_mid}",
                f"LSEL,S,LINE,,{line_mid}",
                f"LATT,1,,1,,{kb_n},,{sec_mid}",
                f"! Edge {edge_i0}: start segment (joint) section {sec_joint}",
                f"LSEL,S,LINE,,{line_start}",
                f"LATT,1,,1,,{kb_n},,{sec_joint}",
                f"! Edge {edge_i0}: end segment (joint) section {sec_joint}",
                f"LSEL,S,LINE,,{line_end}",
                f"LATT,1,,1,,{kb_n},,{sec_joint}",
            )
        )

    cmds.append("LSEL,ALL")
    return tuple(cmds)
