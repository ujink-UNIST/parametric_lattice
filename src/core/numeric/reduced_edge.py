#reduced_edge.py
"""Module for reduced edge functionality in src.core.numeric."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from src.core.numeric.segment import Segment


@dataclass(frozen=True)
class ReducedEdge:
    segment: Segment
    section_type: str
    radius: Fraction
