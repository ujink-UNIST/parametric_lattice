#reduce.py
"""Module for reduce functionality in src.core.geometric."""

from typing import Sequence

from core.numeric.raw_beam import RawBeam
from core.numeric.raw_edge import RawEdge
from core.numeric.raw_node import RawNode
from core.numeric.reduced_edge import ReducedEdge
from core.numeric.segment import Segment


def reduce_edges(
    nodes: Sequence[RawNode],
    edges: Sequence[RawEdge],
    beams: Sequence[RawBeam],
) -> list[ReducedEdge]:
    """Resolve edge endpoint and beam ids into segments with beam properties."""
    nodes_by_id = {node.id: node for node in nodes}
    reduced = []
    for edge in edges:
        beam = beams[edge.beam_id]
        reduced.append(
            ReducedEdge(
                Segment(
                    nodes_by_id[edge.node0_id].point,
                    nodes_by_id[edge.node1_id].point,
                ),
                beam.section_type,
                beam.radius,
            )
        )
    return reduced
