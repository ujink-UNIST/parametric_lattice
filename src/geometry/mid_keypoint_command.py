# mid_keypoint_command.py

from __future__ import annotations

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
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)
from core.unit_cell import UnitCell


def _get_edge_radius_ratio(
    edge: np.ndarray,
    beam_type_id: int,
    unit_cell: UnitCell,
) -> float:
    """Match the same radius-ratio lookup used by beam section definition."""

    # Allow future/alternate edge formats that carry a per-edge radius ratio.
    if len(edge) >= 3:
        return float(edge[2])

    beam_type = unit_cell.beam_types[beam_type_id]
    radius_ratio = beam_type.get("radius_ratio")
    if radius_ratio is None:
        raise KeyError(f"Beam type {beam_type_id} is missing 'radius_ratio'")
    return float(radius_ratio)


def edge_radius(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: BeamProfileParams,
    edge_index: int,
    edge: np.ndarray,
) -> float:
    """Return physical radius used for a given edge (same logic as solid stage)."""

    beam_type_id = int(unit_cell.edge_beam_type_ids[edge_index])
    radius_ratio = _get_edge_radius_ratio(edge, beam_type_id, unit_cell)
    return float(
        profile_params.radius * radius_ratio * float(np.min(geometry_params.size))
    )


def build_mid_keypoint_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
) -> tuple[ApdlCommands, set[tuple[int, int]]]:
    """Create 2 mid keypoints per edge and return joint-segment endpoints.

    For each original edge (kp1 -> kp2), we create two interior keypoints:
      - mid_a at distance r from kp1 along the strut
      - mid_b at distance r from kp2 along the strut

    These are intended to create 3 beam line segments later:
      (kp1 -> mid_a)  [joint-strengthened]
      (mid_a -> mid_b) [normal]
      (mid_b -> kp2)  [joint-strengthened]

    Returns:
      (commands, joint_segments)

    where joint_segments is a set of normalized keypoint endpoint pairs
    (min(k1,k2), max(k1,k2)) for the two strengthened end segments per strut.

    Keypoint id allocation:
      Starts after existing lattice node keypoints (N) and beam orientation
      keypoints (2*E):
        start_kp_id = N + 2*E + 1

    If an edge is too short (2r > L), r is clamped to 0.49*L.
    """

    if not isinstance(profile_params, BeamProfileParams):
        return (), set()

    cmds: List[str] = []
    cmds.extend(apdl_block(f"""
{apdl_comment('Create mid keypoints for joint strengthening (2 per edge)')}

"""))

    n_nodes = int(unit_cell.nodes.shape[0])
    n_edges = int(unit_cell.edges.shape[0])

    # Existing keypoints:
    #   1..n_nodes                     : lattice nodes
    #   n_nodes+1 .. n_nodes+2*n_edges : orientation keypoints (2 per edge)
    start_kp_id = n_nodes + 2 * n_edges + 1

    count: int = unit_cell.edges.shape[0]
    digits = len(str(max(count - 1, 0)))

    joint_segments: set[tuple[int, int]] = set()

    for edge_index, edge in enumerate(unit_cell.edges):
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])

        kp1_id = n1_idx + 1
        kp2_id = n2_idx + 1

        start = transform_coords(
            cast(Vector3, unit_cell.nodes[n1_idx]),
            geometry_params.size,
        )
        end = transform_coords(
            cast(Vector3, unit_cell.nodes[n2_idx]),
            geometry_params.size,
        )

        tangent: Vector3 = end - start
        length = float(np.linalg.norm(tangent))
        if length <= 0:
            continue

        t_hat: Vector3 = cast(Vector3, tangent / length)

        r = float(
            edge_radius(
                unit_cell,
                geometry_params,
                profile_params,
                edge_index,
                edge,
            )
            * profile_params.joint_length_factor
        )
        r_eff = min(r, 0.49 * length)

        kp_a = start + t_hat * r_eff
        kp_b = end - t_hat * r_eff

        kp_id_a = start_kp_id + 2 * edge_index
        kp_id_b = start_kp_id + 2 * edge_index + 1

        # Record strengthened end segments by keypoint endpoints.
        sorted_a = tuple(sorted((kp1_id, kp_id_a)))
        sorted_b = tuple(sorted((kp_id_b, kp2_id)))
        joint_segments.add((sorted_a[0], sorted_a[1]))
        joint_segments.add((sorted_b[0], sorted_b[1]))

        cmds.extend(
            apdl_block(
                f"""K,{kp_id_a},{kp_a[0]:.10g},{kp_a[1]:.10g},{kp_a[2]:.10g} {apdl_inline_comment(f'{edge_index:>{digits}}: mid_a r={r_eff:.6g}')}
K,{kp_id_b},{kp_b[0]:.10g},{kp_b[1]:.10g},{kp_b[2]:.10g} {apdl_inline_comment(f'{edge_index:>{digits}}: mid_b r={r_eff:.6g}')}"""
            )
        )

    return tuple(cmds), joint_segments
