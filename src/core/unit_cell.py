#unit_cell.py
"""Module for unit cell functionality in src.core."""

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

import numpy as np

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

    name: str = ""
    nodes: Nodes = field(
        default_factory=lambda: np.empty((0, 3), dtype=float)
    )
    node_boundaries: NodeBoundaries = field(
        default_factory=lambda: np.empty((0, 3), dtype=int)
    )
    beam_types: Tuple[Dict[str, Any], ...] = ()
    edges: Edges = field(
        default_factory=lambda: np.empty((0, 2), dtype=int)
    )
    edge_beam_type_ids: EdgeTypeIds = field(
        default_factory=lambda: np.empty((0,), dtype=int)
    )
    edge_ratios: EdgeRatios = field(
        default_factory=lambda: np.empty((0,), dtype=float)
    )
    edge_normal_vectors: EdgeNormals = field(
        default_factory=lambda: np.empty((0, 3), dtype=float)
    )
    edge_extend_ids: Tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.edge_extend_ids is None:
            object.__setattr__(
                self,
                "edge_extend_ids",
                tuple([-1] * len(self.edges)),
            )


def unit_cell_from_lattice(
    lattice: Lattice,
    *,
    name: str = "",
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
            [edge["node0_id"], edge["node1_id"]]
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
    edge_extend_ids: Tuple[int, ...] = tuple(
        int(edge["extend_id"]) for edge in lattice["edges"]
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
        edge_extend_ids=edge_extend_ids,
    )
