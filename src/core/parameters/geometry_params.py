# File: c:\Users\USER\Documents\parametric_lattice\src\core\parameters\geometry_params.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

import numpy as np

from core.floats.vector import Vector3


@dataclass(frozen=True)
class GeometryParams:
    cell_name: str
    size: Vector3


def build_geometry_params(
    input_header: Tuple[str, ...], row: Tuple[Any, ...]
) -> GeometryParams:
    """Build GeometryParams from an excel-style (header, row) tuple."""

    col_idx = {name: i for i, name in enumerate(input_header)}

    size = np.array(
        [
            float(row[col_idx["size_x"]]),
            float(row[col_idx["size_y"]]),
            float(row[col_idx["size_z"]]),
        ],
        dtype=float,
    )

    return GeometryParams(
        cell_name=str(row[col_idx["cell_name"]]),
        size=size,
    )
