#raw_node.py
"""Module for raw node functionality in src.core.numeric."""

from __future__ import annotations

from dataclasses import dataclass
from src.core.numeric.point import Point


@dataclass(frozen=True)
class RawNode:
    id: int
    point: Point
