# canonicalize.py

from __future__ import annotations

from fractions import Fraction
from typing import Sequence


from core.numeric.point import Point
from core.numeric.raw_beam import RawBeam
from core.numeric.raw_edge import RawEdge
from core.numeric.raw_node import RawNode
from core.geometric.reduce import reduce_edges
from core.geometric.merge import merge_edges
from core.geometric.split import split_edges
from core.geometric.sort import sort_edges


def canonicalize_(
    nodes: Sequence[RawNode],
    edges: Sequence[RawEdge],
    beams: Sequence[RawBeam],
) -> tuple[
    list[Point],
    list[tuple[int, int, int]],
    list[tuple[str, Fraction]],
]:
    """Reduce, merge, split, and sort raw lattice data."""
    reduced = reduce_edges(nodes, edges, beams)
    merged = merge_edges(reduced)
    split = split_edges(merged)
    sort = sort_edges(split)
    return sort
