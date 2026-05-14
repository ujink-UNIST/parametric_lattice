# sort.py

from fractions import Fraction
from typing import Iterable, Sequence

from core.numeric.point import Point
from core.numeric.reduced_edge import ReducedEdge


def sort_edges(
    edges: Sequence[ReducedEdge],
) -> tuple[
    list[Point],
    list[tuple[int, int, int]],
    list[tuple[str, Fraction]],
]:
    """Assign canonical node/beam ids and sort edges ascending by ids."""
    points = sorted(
        set(_edge_points(edges)), key=_node_sort_key
    )
    beams = sorted(
        {(edge.section_type, edge.radius) for edge in edges}
    )
    node_ids = {
        point: idx for idx, point in enumerate(points)
    }
    beam_ids = {beam: idx for idx, beam in enumerate(beams)}

    sorted_edges = []
    for edge in edges:
        start_id = node_ids[edge.segment.start]
        end_id = node_ids[edge.segment.end]
        sorted_edges.append(
            (
                min(start_id, end_id),
                max(start_id, end_id),
                beam_ids[(edge.section_type, edge.radius)],
            )
        )
    sorted_edges.sort(
        key=lambda item: (item[0], item[1], item[2])
    )
    return points, sorted_edges, beams


def _edge_points(
    edges: Iterable[ReducedEdge],
) -> list[Point]:
    points = []
    for edge in edges:
        points.extend(
            (edge.segment.start, edge.segment.end)
        )
    return points


def _node_sort_key(
    point: Point,
) -> tuple[Fraction, Fraction, Fraction]:
    return (
        point.x + 2 * point.y + 4 * point.z,
        point.x,
        point.y,
    )
