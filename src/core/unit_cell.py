# File: c:\Users\USER\Documents\parametric_lattice\src\core\unit_cell.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass
import numpy as np
from typing import Any, Dict, Tuple

from core.floats.unit_cell_layout import (
    EdgeNormals,
    EdgeRatios,
    EdgeTypeIds,
    Edges,
    NodeBoundaries,
    Nodes,
)
from core.lattice import Lattice


@dataclass(frozen=True)
class UnitCell:
    """Geometry and boundary metadata for a parsed lattice unit cell."""

    name: str
    nodes: Nodes
    node_boundaries: NodeBoundaries
    beam_types: Tuple[Dict[str, Any], ...]
    edges: Edges
    edge_beam_type_ids: EdgeTypeIds
    edge_ratios: EdgeRatios
    edge_normal_vectors: EdgeNormals


def unit_cell_from_lattice(
    lattice: Lattice,
    name: str = "unknown",
) -> UnitCell:
    """Convert canonical lattice into an immutable UnitCell."""
    nodes: Nodes = np.array(
        [node["position"] for node in lattice["nodes"]],
        dtype=float,
    )
    node_boundaries: NodeBoundaries = np.array(
        [node["boundary"] for node in lattice["nodes"]],
        dtype=int,
    )
    beam_types = tuple(
        dict(beam) for beam in lattice["beam_types"]
    )

    edges: Edges = np.array(
        [
            [
                edge["node0_id"],
                edge["node1_id"],
                edge["beam_type_id"],
            ]
            for edge in lattice["edges"]
        ],
        dtype=int,
    )
    edge_beam_type_ids: EdgeTypeIds = np.array(
        [edge["beam_type_id"] for edge in lattice["edges"]],
        dtype=int,
    )
    edge_ratios: EdgeRatios = np.array(
        [
            edge["section_ratio"]
            for edge in lattice["edges"]
        ],
        dtype=float,
    )
    edge_normal_vectors: EdgeNormals = np.array(
        [edge["normal"] for edge in lattice["edges"]],
        dtype=float,
    )

    return UnitCell(
        name=name,
        nodes=nodes,
        node_boundaries=node_boundaries,
        beam_types=beam_types,
        edges=edges,
        edge_beam_type_ids=edge_beam_type_ids,
        edge_ratios=edge_ratios,
        edge_normal_vectors=edge_normal_vectors,
    )
