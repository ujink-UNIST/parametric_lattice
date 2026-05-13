# File: c:\Users\USER\Documents\parametric_lattice\src\core\parameters\meshing_params.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class MeshingParams:
    max_element_size: float

    def to_string(self) -> str:
        return f"MaxElementSize:{self.max_element_size:.6f}"


def build_meshing_params(
    input_header: Tuple[str, ...], row: Tuple[Any, ...]
) -> MeshingParams:
    col_idx = {name: i for i, name in enumerate(input_header)}

    return MeshingParams(
        max_element_size=float(row[col_idx["max_element_size"]]),
    )
