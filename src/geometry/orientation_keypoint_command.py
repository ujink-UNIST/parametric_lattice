# orientation_keypoint_command.py

from typing import List, cast

import numpy as np

from core.apdl_block import (
    apdl_block,
    apdl_comment,
    apdl_inline_comment,
)
from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.geometric.transform import transform_coords
from core.parameters.geometry_params import GeometryParams
from core.unit_cell import UnitCell


def build_beam_orientation_keypoint_commands_(
    unit_cell: UnitCell, geometry_params: GeometryParams
) -> ApdlCommands:
    """Create orientation keypoints used by ``LATT`` for beam cross-section axes."""
    normals = unit_cell.edge_normal_vectors
    cmds: List[str] = []

    cmds.extend(apdl_block(f"""
{apdl_comment("Create beam orientation keypoints from edge normal vectors")}
"""))

    count: int = unit_cell.edges.shape[0]
    digits = len(str(count - 1))

    for edge_index, (edge, normal) in enumerate(
        zip(unit_cell.edges, normals)
    ):
        n1_idx: int
        n2_idx: int

        n1_idx = int(edge[0])
        n2_idx = int(edge[1])

        start = transform_coords(
            cast(Vector3, unit_cell.nodes[n1_idx]),
            geometry_params.size,
        )
        end = transform_coords(
            cast(Vector3, unit_cell.nodes[n2_idx]),
            geometry_params.size,
        )
        tangent: Vector3 = end - start
        normal = cast(
            Vector3, normal / np.linalg.norm(normal)
        )
        binormal: Vector3 = np.cross(normal, tangent)
        binormal = binormal / np.linalg.norm(binormal)

        length = np.linalg.norm(tangent) * 0.1

        kp_n = start + normal * length
        kp_b = start + binormal * length

        kp_id = len(unit_cell.nodes) + edge_index * 2 + 1

        cmds.extend(apdl_block(f"""
K,{kp_id},{kp_n[0]:.10g},{kp_n[1]:.10g},{kp_n[2]:.10g} {
    apdl_inline_comment(f"{edge_index:>{digits}}: e_n {normal}")}
K,{kp_id + 1},{kp_b[0]:.10g},{kp_b[1]:.10g},{kp_b[2]:.10g} {
    apdl_inline_comment(f"{edge_index:>{digits}}: e_b {binormal}")}
            """))
    return tuple(cmds)
