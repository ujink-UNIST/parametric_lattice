# verify.py

from __future__ import annotations

from typing import Sequence

from core.numeric.raw_beam import RawBeam
from core.numeric.raw_edge import RawEdge
from core.numeric.raw_node import RawNode
from preprocess.errors import LatticeJsonError


def validate_raw_lattice_(
    nodes: Sequence[RawNode],
    edges: Sequence[RawEdge],
    beams: Sequence[RawBeam],
) -> None:
    _validate_nodes(nodes)
    _validate_beams(beams)
    _validate_edges(
        edges, {node.id for node in nodes}, len(beams)
    )


def _validate_nodes(nodes: Sequence[RawNode]) -> None:
    seen: set[int] = set()
    for node in nodes:
        if node.id in seen:
            raise LatticeJsonError(
                "node ids must be unique"
            )
        seen.add(node.id)


def _validate_beams(beams: Sequence[RawBeam]) -> None:
    for beam in beams:
        if not beam.section_type:
            raise LatticeJsonError(
                "beam type must not be empty"
            )
        if beam.radius <= 0:
            raise LatticeJsonError(
                "beam radius must be greater than 0"
            )


def _validate_edges(
    edges: Sequence[RawEdge],
    node_ids: set[int],
    beam_count: int,
) -> None:
    for edge in edges:
        if edge.node0_id == edge.node1_id:
            raise LatticeJsonError(
                "edge endpoints must be different"
            )
        if (
            edge.node0_id not in node_ids
            or edge.node1_id not in node_ids
        ):
            raise LatticeJsonError(
                "edge node id must reference an existing node"
            )
        if not 0 <= edge.beam_id < beam_count:
            raise LatticeJsonError(
                "edge beam id must reference an existing beam"
            )
