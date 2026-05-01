# File: c:\Users\USER\Documents\parametric_lattice\src\core\geometric\merge.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from typing import Sequence

from core.numeric.reduced_edge import ReducedEdge
from core.numeric.segment import (
    Segment,
    are_collinear,
    ranges_touch_or_overlap,
)


def merge_edges(
    edges: Sequence[ReducedEdge],
) -> list[ReducedEdge]:
    """Merge collinear overlapping/touching edges with identical beam properties."""
    groups: list[ReducedEdge] = []
    for edge in edges:
        groups = _insert_or_merge(groups, edge)
    return groups


def _insert_or_merge(
    groups: list[ReducedEdge], edge: ReducedEdge
) -> list[ReducedEdge]:
    if not groups:
        return [edge]

    first, rest = groups[0], groups[1:]
    merged_segment = None
    if (
        first.section_type == edge.section_type
        and first.radius == edge.radius
    ):
        merged_segment = merge_segments(
            first.segment, edge.segment
        )
    if merged_segment is not None:
        return _insert_or_merge(
            rest,
            ReducedEdge(
                merged_segment,
                first.section_type,
                first.radius,
            ),
        )
    return [first] + _insert_or_merge(rest, edge)


def merge_segments(
    left: Segment, right: Segment
) -> Segment | None:
    """Merge collinear touching or overlapping segments when possible."""
    if left.is_zero_length and right.is_zero_length:
        return left if left.start == right.start else None
    if left.is_zero_length:
        return right if right.includes(left.start) else None
    if right.is_zero_length:
        return left if left.includes(right.start) else None
    if not are_collinear(left, right):
        return None
    if not ranges_touch_or_overlap(left, right):
        return None
    points = [left.start, left.end, right.start, right.end]
    return Segment(min(points), max(points))
