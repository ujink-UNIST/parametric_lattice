# line_command.py

from core.apdl_block import (
    apdl_block,
    apdl_comment,
    apdl_inline_comment,
)
from core.apdl_commands import ApdlCommands
from core.parameters.element_type_params import ElementTypeParams
from core.unit_cell import UnitCell


def build_line_commands_(
    unit_cell: UnitCell,
    element_type: ElementTypeParams,
    joint_segments: set[tuple[int, int]] | None = None,
) -> ApdlCommands:
    cmds: list[str] = []
    cmds.extend(apdl_block(f"""
{apdl_comment('Create beam centerlines from lattice edges')}

"""))

    # For solid models we don't use beam centerlines.
    if "SOLID" in element_type.model:
        return ()

    n_nodes = int(unit_cell.nodes.shape[0])
    n_edges = int(unit_cell.edges.shape[0])
    digits = len(str(max(n_edges - 1, 0)))

    # Mid keypoints are created in build_mid_keypoint_commands_ with ids:
    #   start_kp_id = n_nodes + 2*n_edges + 1
    #   edge i => mid_a = start_kp_id + 2*i, mid_b = start_kp_id + 2*i + 1
    mid_start_kp_id = n_nodes + 2 * n_edges + 1

    # 1) Create all non-strengthened (middle) segments first.
    for i, edge in enumerate(unit_cell.edges):
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])
        kp_mid_a = mid_start_kp_id + 2 * i
        kp_mid_b = mid_start_kp_id + 2 * i + 1
        cmds.extend(
            apdl_block(
                f"L,{kp_mid_a},{kp_mid_b} {apdl_inline_comment(f'{i:>{digits}}: mid e {n1_idx} {n2_idx}')}"
            )
        )

    # 2) Then create strengthened end segments.
    # Line numbering will be:
    #   1..E       : mid segments
    #   E+1..2E    : start segments (all starts first)
    #   2E+1..3E   : end segments   (then all ends)

    # 2a) Start segments for every edge.
    for i, edge in enumerate(unit_cell.edges):
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])

        kp1_id = n1_idx + 1
        kp_mid_a = mid_start_kp_id + 2 * i

        seg_start = tuple(sorted((kp1_id, kp_mid_a)))
        if joint_segments is None or seg_start in joint_segments:
            cmds.extend(
                apdl_block(
                    f"L,{kp1_id},{kp_mid_a} {apdl_inline_comment(f'{i:>{digits}}: joint_start e {n1_idx} {n2_idx}')}"
                )
            )

    # 2b) End segments for every edge.
    for i, edge in enumerate(unit_cell.edges):
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])

        kp2_id = n2_idx + 1
        kp_mid_b = mid_start_kp_id + 2 * i + 1

        seg_end = tuple(sorted((kp_mid_b, kp2_id)))
        if joint_segments is None or seg_end in joint_segments:
            cmds.extend(
                apdl_block(
                    f"L,{kp_mid_b},{kp2_id} {apdl_inline_comment(f'{i:>{digits}}: joint_end e {n1_idx} {n2_idx}')}"
                )
            )

    return tuple(cmds)
