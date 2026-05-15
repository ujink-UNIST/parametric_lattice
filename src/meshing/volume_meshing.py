# volume_meshing.py

from __future__ import annotations

import math
from typing import List
import numpy as np

from core.apdl_block import apdl_block
from core.apdl_commands import ApdlCommands
from core.geometric.transform import transform_coords
from core.parameters.geometry_params import GeometryParams
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)
from core.unit_cell import Edges, Nodes, UnitCell
from geometry.mid_keypoint_command import edge_radius


def _build_beam_line_sizing_commands(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: BeamProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Return ``LESIZE`` commands for beam lines (mid + joint segments).

    Line numbering convention (see geometry.line_command / profile_.line_section_command):
      1..E       : mid segments
      E+1..2E    : start joint segments
      2E+1..3E   : end joint segments

    We size *all* segments:
      - joint segments get divisions based on r_eff
      - mid segments get divisions based on (L - 2*r_eff)

    where r_eff = min(r, 0.49*L) to match the mid-keypoint clamping logic.
    """

    cmds: List[str] = []
    n_edges = len(unit_cell.edges)

    for edge_index, edge in enumerate(unit_cell.edges):
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])

        start = transform_coords(unit_cell.nodes[n1_idx], geometry_params.size)
        end = transform_coords(unit_cell.nodes[n2_idx], geometry_params.size)
        length = float(np.linalg.norm(start - end))
        if length <= 0:
            cmds.append(f"! LESIZE skipped: degenerate edge (edge_index={edge_index}, length=0)")
            continue

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

        joint_len = float(r_eff)
        mid_len = float(max(length - 2.0 * r_eff, 0.0))

        ndiv_joint = _divisions_for_edge(joint_len, meshing_params.max_element_size)
        ndiv_mid = _divisions_for_edge(mid_len, meshing_params.max_element_size)

        line_mid = edge_index + 1
        line_start = n_edges + (edge_index + 1)
        line_end = 2 * n_edges + (edge_index + 1)

        cmds.append(
            f"! LESIZE edge {edge_index + 1}: L={length:.6g}, r_eff={r_eff:.6g}, "
            f"mid_len={mid_len:.6g}, joint_len={joint_len:.6g}"
        )
        cmds.append(f"LESIZE,{line_mid},,,{ndiv_mid}")
        cmds.append(f"LESIZE,{line_start},,,{ndiv_joint}")
        cmds.append(f"LESIZE,{line_end},,,{ndiv_joint}")

    return tuple(cmds)


def _divisions_for_edge(edge_length: float, max_element_size: float) -> int:
    """Return the number of line divisions required for an edge."""
    if max_element_size <= 0:
        raise ValueError(f"max_element_size must be positive: {max_element_size}")
    return max(1, math.ceil(edge_length / max_element_size))


def build_volume_meshing_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return (
            ("! --- Beam volume meshing stage ---",)
            + _build_beam_line_sizing_commands(
                unit_cell,
                geometry_params,
                profile_params,
                meshing_params,
            )
            + ("LMESH,ALL",)
        )

    return (
        "! --- Solid volume meshing stage ---",
        "ET,1,187",
        "TYPE,1",
        f"AESIZE,ALL,{meshing_params.max_element_size}",
        "AMESH,ALL",
        "MSHAPE,1,3D,",
        "MSHKEY,0",
        "VMESH,ALL",
    )
