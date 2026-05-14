# split.py

from fractions import Fraction
from typing import Sequence

from core.numeric.direction import parallel
from core.numeric.point import (
    Point,
    get_direction,
    coordinate_on,
)
from core.numeric.reduced_edge import ReducedEdge
from core.numeric.segment import Segment, are_collinear


def split_edges(
    edges: Sequence[ReducedEdge],
) -> list[ReducedEdge]:
    """Split edges at intersections with all other edges."""
    result = []
    for edge in edges:
        points = []
        for other in edges:
            points.extend(
                segment_intersection_points(
                    edge.segment, other.segment
                )
            )
        for segment in split_segment_at_points(
            edge.segment, points
        ):
            result.append(
                ReducedEdge(
                    segment, edge.section_type, edge.radius
                )
            )
    return result


def segment_intersection_points(
    left: Segment, right: Segment
) -> list[Point]:
    """Return every intersection point between two segments."""
    if left.is_zero_length and right.is_zero_length:
        return (
            [left.start]
            if left.start == right.start
            else []
        )
    if left.is_zero_length:
        return (
            [left.start]
            if right.includes(left.start)
            else []
        )
    if right.is_zero_length:
        return (
            [right.start]
            if left.includes(right.start)
            else []
        )

    left_vector = get_direction(left.start, left.end)
    right_vector = get_direction(right.start, right.end)
    if parallel(left_vector, right_vector):
        if not are_collinear(left, right):
            return []
        points = [
            point
            for point in (left.start, left.end)
            if right.includes(point)
        ] + [
            point
            for point in (right.start, right.end)
            if left.includes(point)
        ]
        return sorted(set(points))

    point = _single_intersection_point(left, right)
    return [point] if point is not None else []


def split_segment_at_points(
    segment: Segment, points: Sequence[Point]
) -> list[Segment]:
    """Split a segment at all points that lie on it."""
    axis = get_direction(
        segment.start, segment.end
    ).dominant_axis
    ordered_points = sorted(
        set(
            [segment.start, segment.end]
            + [
                point
                for point in points
                if segment.includes(point)
            ]
        ),
        key=lambda point: coordinate_on(axis, point),
    )
    return [
        split
        for split in (
            Segment(a, b)
            for a, b in zip(
                ordered_points, ordered_points[1:]
            )
        )
        if not split.is_zero_length
    ]


def _single_intersection_point(
    left: Segment, right: Segment
) -> Point | None:
    params = _intersection_parameters(left, right)
    if params is None:
        return None
    t, u = params
    intersection = (
        left.start + get_direction(left.start, left.end) * t
    )
    right_intersection = (
        right.start
        + get_direction(right.start, right.end) * u
    )
    if (
        0 <= t <= 1
        and 0 <= u <= 1
        and intersection == right_intersection
    ):
        return intersection
    return None


def _intersection_parameters(
    left: Segment, right: Segment
) -> tuple[Fraction, Fraction] | None:
    left_start = left.start
    right_start = right.start
    left_vector = get_direction(left.start, left.end)
    right_vector = get_direction(right.start, right.end)
    delta = get_direction(left_start, right_start)
    coordinate_pairs = (
        (
            left_vector.x,
            right_vector.x,
            delta.x,
            left_vector.y,
            right_vector.y,
            delta.y,
        ),
        (
            left_vector.x,
            right_vector.x,
            delta.x,
            left_vector.z,
            right_vector.z,
            delta.z,
        ),
        (
            left_vector.y,
            right_vector.y,
            delta.y,
            left_vector.z,
            right_vector.z,
            delta.z,
        ),
    )
    for (
        left_a,
        right_a,
        delta_a,
        left_b,
        right_b,
        delta_b,
    ) in coordinate_pairs:
        determinant = right_a * left_b - left_a * right_b
        if determinant == 0:
            continue
        return (
            (right_a * delta_b - delta_a * right_b)
            / determinant,
            (left_a * delta_b - delta_a * left_b)
            / determinant,
        )
    return None
