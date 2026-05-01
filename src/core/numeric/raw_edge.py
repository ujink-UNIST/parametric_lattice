# File: c:\Users\USER\Documents\parametric_lattice\src\core\numeric\raw_edge.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Sun Apr 26 2026
# Modified: Sun Apr 26 2026


from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawEdge:
    node0_id: int
    node1_id: int
    beam_id: int
