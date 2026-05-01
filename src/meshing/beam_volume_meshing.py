# File: c:\Users\USER\Documents\parametric_lattice\src\meshing\beam_volume_meshing.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from __future__ import annotations

import math
from typing import List
import numpy as np

from core.apdl_commands import ApdlCommands
from core.parameters.geometry_params import GeometryParams
from core.parameters.material_params import MaterialParams
from core.parameters.meshing_params import MeshingParams
from core.unit_cell import Edges, Nodes, UnitCell
from meshing.element_type_command import (
    build_element_type_commands_,
)


def _build_beam_line_sizing_commands(
    nodes: Nodes,
    edges: Edges,
    meshing_params: MeshingParams,
) -> ApdlCommands:
    """Return ``LESIZE`` commands for every beam line."""
    cmds: List[str] = []
    for i, (n1_idx, n2_idx, _) in enumerate(edges):
        line_num = i + 1
        length = np.linalg.norm(
            nodes[n1_idx] - nodes[n2_idx]
        )
        ndiv = _divisions_for_edge(
            float(length), meshing_params.max_element_size
        )
        cmds.append(f"LESIZE,{line_num},,,{ndiv}")
    return tuple(cmds)


def _build_beam_line_mesh_commands() -> ApdlCommands:
    """Return commands that mesh all selected beam lines."""
    return (
        "! Mesh all beam lines",
        "LMESH,ALL",
    )


def build_beam_volume_meshing_commands_(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
    meshing_params: MeshingParams,
    material_params: MaterialParams,
) -> ApdlCommands:
    """Return beam meshing commands for the lattice volume stage."""
    return (
        ("! --- Beam volume meshing stage ---",)
        + _build_beam_line_sizing_commands(
            unit_cell.nodes, unit_cell.edges, meshing_params
        )
        + build_element_type_commands_(
            geometry_params.model, material_params
        )
        + _build_beam_line_mesh_commands()
    )


def _divisions_for_edge(
    edge_length: float, max_element_size: float
) -> int:
    """Return the number of line divisions required for an edge."""
    if max_element_size <= 0:
        raise ValueError(
            f"max_element_size must be positive: {max_element_size}"
        )
    return max(1, math.ceil(edge_length / max_element_size))
