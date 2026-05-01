# File: c:\Users\USER\Documents\parametric_lattice\src\core\geometry_params.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass
from typing import Any, Tuple
import numpy as np

from core.floats.vector import Vector3


def _col_map(header: Tuple[str, ...]) -> dict[str, int]:
    return {name: i for i, name in enumerate(header)}


def _value(
    row: Tuple[Any, ...], col_idx: dict[str, int], name: str
) -> Any:
    if name not in col_idx:
        raise KeyError(f"Missing column {name!r}")
    return row[col_idx[name]]


@dataclass(frozen=True)
class GeometryParams:
    cell_name: str
    model: str
    size: Vector3
    diameter: float


def build_geometry_params(
    input_header: Tuple[str, ...], row: Tuple[Any, ...]
) -> GeometryParams:
    col_idx = _col_map(input_header)

    return GeometryParams(
        cell_name=str(_value(row, col_idx, "cell_name")),
        model=str(_value(row, col_idx, "model")),
        size=np.array(
            [
                float(_value(row, col_idx, "size_x")),
                float(_value(row, col_idx, "size_y")),
                float(_value(row, col_idx, "size_z")),
            ],
            dtype=float,
        ),
        diameter=float(_value(row, col_idx, "diameter")),
    )
