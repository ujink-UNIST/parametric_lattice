# File: c:\Users\USER\Documents\parametric_lattice\src\core\parameters\material_params.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class MaterialParams:
    e_mod: float
    nu: float
    density: float


def build_material_params(
    input_header: Tuple[str, ...], row: Tuple[Any, ...]
) -> MaterialParams:
    col_idx = {name: i for i, name in enumerate(input_header)}

    return MaterialParams(
        e_mod=float(row[col_idx["e_mod"]]),
        nu=float(row[col_idx["nu"]]),
        density=float(row[col_idx["density"]]),
    )
