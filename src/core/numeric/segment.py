#segment.py
"""Module for segment functionality in src.core.numeric."""

from __future__ import annotations

from dataclasses import dataclass
from src.core.numeric.point import (
    Point,
    coordinate_on,
    get_direction,
)
from src.core.numeric.direction import cross
from fractions import Fraction


@dataclass(frozen=True, order=True)
class Segment:
    start: Point
    end: Point

    @property
    def is_zero_length(self) -> bool:
        return self.start == self.end

    def includes(self, point: Point) -> bool:
        if self.is_zero_length:
            return point == self.start
        axis = get_direction(
            self.start, self.end
        ).dominant_axis
        low, high = _ordered_range(axis, self)
        coordinate = coordinate_on(axis, point)
        return (
            are_collinear(self, Segment(point, point))
            and low <= coordinate <= high
        )


def are_collinear(base: Segment, other: Segment) -> bool:
    base_vector = get_direction(base.start, base.end)
    start_vector = get_direction(base.start, other.start)
    end_vector = get_direction(base.start, other.end)
    return cross(base_vector, start_vector) == (
        0,
        0,
        0,
    ) and cross(base_vector, end_vector) == (0, 0, 0)


def ranges_touch_or_overlap(
    left: Segment, right: Segment
) -> bool:
    axis = get_direction(left.start, left.end).dominant_axis
    left_min, left_max = _ordered_range(axis, left)
    right_min, right_max = _ordered_range(axis, right)
    return max(left_min, right_min) <= min(
        left_max, right_max
    )


def _ordered_range(
    axis: int, segment: Segment
) -> tuple[Fraction, Fraction]:
    start = coordinate_on(axis, segment.start)
    end = coordinate_on(axis, segment.end)
    return (start, end) if start <= end else (end, start)
