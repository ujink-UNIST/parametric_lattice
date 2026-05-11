# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\beam_volume_meshing.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from __future__ import annotations

import math
from typing import List
import numpy as np

from core.apdl_block import apdl_block
from core.apdl_commands import ApdlCommands
from core.parameters.meshing_params import MeshingParams
from core.parameters.profile_params import (
    BeamProfileParams,
    ProfileParams,
)
from core.unit_cell import Edges, Nodes, UnitCell


def _build_beam_line_sizing_commands(
    nodes: Nodes,
    edges: Edges,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Return ``LESIZE`` commands for every beam line."""
    cmds: List[str] = []
    for i, edge in enumerate(edges):
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])
        line_num = i + 1
        length = np.linalg.norm(
            nodes[n1_idx] - nodes[n2_idx]
        )
        ndiv = _divisions_for_edge(
            float(length), meshing_params.max_element_size
        )
        cmds.append(f"LESIZE,{line_num},,,{ndiv}")
    return tuple(cmds)


def _divisions_for_edge(
    edge_length: float, max_element_size: float
) -> int:
    """Return the number of line divisions required for an edge."""
    if max_element_size <= 0:
        raise ValueError(
            f"max_element_size must be positive: {max_element_size}"
        )
    return max(1, math.ceil(edge_length / max_element_size))


def build_volume_meshing_commands_(
    unit_cell: UnitCell,
    profile_params: ProfileParams,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    if isinstance(profile_params, BeamProfileParams):
        return (
            ("! --- Beam volume meshing stage ---",)
            + _build_beam_line_sizing_commands(
                unit_cell.nodes,
                unit_cell.edges,
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
