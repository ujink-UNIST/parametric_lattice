# File: c:\Users\USER\Documents\parametric_lattice\src\geometry\orientation_keypoint_command.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from typing import List, cast

import numpy as np

from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.unit_cell import UnitCell


def build_beam_orientation_keypoint_commands_(
    unit_cell: UnitCell,
) -> ApdlCommands:
    """Create orientation keypoints used by ``LATT`` for beam cross-section axes."""
    normals = unit_cell.edge_normal_vectors
    cmds: List[str] = [
        "! Create beam orientation keypoints from edge normal vectors"
    ]
    for edge_index, (edge, normal) in enumerate(
        zip(unit_cell.edges, normals)
    ):
        n1_idx: int
        n2_idx: int

        n1_idx, n2_idx, _ = edge

        start = cast(Vector3, unit_cell.nodes[n1_idx])
        end = cast(Vector3, unit_cell.nodes[n2_idx])
        normal = cast(
            Vector3, normal / np.linalg.norm(normal)
        )

        chord: Vector3 = end - start
        length = np.linalg.norm(chord)

        kp = start + normal * length
        kp_id = _beam_orientation_keypoint_id(
            len(unit_cell.nodes), edge_index
        )
        cmds.append(
            f"K,{kp_id},{kp[0]:.10g},{kp[1]:.10g},{kp[2]:.10g}"
        )
    return tuple(cmds)


def _beam_orientation_keypoint_id(
    node_count: int, edge_index: int
) -> int:
    """Return the keypoint id reserved for one edge's beam orientation."""
    return node_count + edge_index + 1
