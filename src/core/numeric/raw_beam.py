# File: c:\Users\USER\Documents\parametric_lattice\src\core\numeric\Fractions.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Sun Apr 26 2026
# Modified: Sun Apr 26 2026


from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class RawBeam:
    section_type: str
    radius: Fraction
