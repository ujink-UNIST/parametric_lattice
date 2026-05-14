# point.py

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from core.numeric.direction import Direction


@dataclass(frozen=True, order=True)
class Point:
    x: Fraction
    y: Fraction
    z: Fraction

    def __add__(self, direction: Direction) -> Point:
        return Point(
            x=self.x + direction.x,
            y=self.y + direction.y,
            z=self.z + direction.z,
        )


def coordinate_on(axis: int, point: Point) -> Fraction:
    return (point.x, point.y, point.z)[axis]


def get_direction(start: Point, end: Point) -> Direction:
    return Direction(
        x=end.x - start.x,
        y=end.y - start.y,
        z=end.z - start.z,
    )
