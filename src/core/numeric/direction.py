#direction.py
"""Module for direction functionality in src.core.numeric."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True, order=True)
class Direction:
    x: Fraction
    y: Fraction
    z: Fraction

    @property
    def dominant_axis(self) -> int:
        if abs(self.x) >= abs(self.y) and abs(
            self.x
        ) >= abs(self.z):
            return 0
        if abs(self.y) >= abs(self.z):
            return 1
        return 2

    def __mul__(self, a: Fraction) -> Direction:
        return Direction(
            x=self.x * a, y=self.y * a, z=self.z * a
        )


RIGHT = Direction(Fraction(1), Fraction(0), Fraction(0))
UP = Direction(Fraction(0), Fraction(1), Fraction(0))
FORWARD = Direction(Fraction(0), Fraction(0), Fraction(1))


def absolute(v: Direction) -> Direction:
    return Direction(
        x=v.x if v.x >= 0 else -v.x,
        y=v.y if v.y >= 0 else -v.y,
        z=v.z if v.z >= 0 else -v.z,
    )


def parallel(a: Direction, b: Direction) -> bool:
    return cross(a, b) == Direction(
        x=Fraction.from_float(0),
        y=Fraction.from_float(0),
        z=Fraction.from_float(0),
    )


def cross(a: Direction, b: Direction) -> Direction:
    ax, ay, az = a.x, a.y, a.z
    bx, by, bz = b.x, b.y, b.z
    return Direction(
        x=ay * bz - az * by,
        y=az * bx - ax * bz,
        z=ax * by - ay * bx,
    )
