#raw_beam.py
"""Module for raw beam functionality in src.core.numeric."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class RawBeam:
    section_type: str
    radius: Fraction
