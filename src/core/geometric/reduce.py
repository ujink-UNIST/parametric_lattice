# File: c:\Users\USER\Documents\parametric_lattice\src\core\geometric\reduce.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026
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
