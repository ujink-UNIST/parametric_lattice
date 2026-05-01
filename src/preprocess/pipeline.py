# File: c:\Users\USER\Documents\parametric_lattice\src\preprocess\pipeline.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Sun Apr 26 2026
# Modified: Sun Apr 26 2026


from __future__ import annotations


from core.lattice import Lattice, sorted_to_lattice
from preprocess.lgf_parser import parse_lgf_
from preprocess.verify import validate_raw_lattice_
from preprocess.canonicalize import canonicalize_
from core.unit_cell import UnitCell, unit_cell_from_lattice


def parse_lgf_unit_cell(
    content: str, name: str = "unknown"
) -> UnitCell:
    """Parse LGF through canonical JSON and return a solver ``UnitCell``."""
    nodes, edges, beams = parse_lgf_(content)
    validate_raw_lattice_(nodes, edges, beams)
    sorted_nodes, sorted_edges, sorted_beams = (
        canonicalize_(nodes, edges, beams)
    )
    lattice: Lattice = sorted_to_lattice(
        sorted_nodes, sorted_beams, sorted_edges
    )
    return unit_cell_from_lattice(lattice, name)
