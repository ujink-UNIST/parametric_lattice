# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\line_section_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from typing import List, Tuple

from core.apdl_commands import ApdlCommands


def build_line_section_commands_(
    edge_sec_ids: Tuple[int, ...],
    orientation_keypoint_start: int | None = None,
) -> ApdlCommands:
    """Assign the generated section ids to the corresponding lines."""
    cmds: List[str] = []
    for i, sec_id in enumerate(edge_sec_ids, start=1):
        kb = (
            ""
            if orientation_keypoint_start is None
            else str(orientation_keypoint_start + i)
        )

        cmds.extend(
            [
                f"! Assign section {sec_id} to beam line {i}",
                f"LSEL,S,LINE,,{i}",
                f"LATT,1,,1,,{kb},,{sec_id}",
            ]
        )

    cmds.append("LSEL,ALL")
    return tuple(cmds)
