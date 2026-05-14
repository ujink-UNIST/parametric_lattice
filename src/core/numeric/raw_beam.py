# raw_beam.py

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class RawBeam:
    section_type: str
    radius: Fraction
