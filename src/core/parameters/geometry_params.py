# geometry_params.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Tuple

import numpy as np

from core.floats.vector import Vector3


@dataclass(frozen=True)
class GeometryParams:
    cell_name: str
    size: Vector3

    def to_string(self) -> str:
        sx, sy, sz = (float(self.size[0]), float(self.size[1]), float(self.size[2]))
        return (
            f"Cell:{self.cell_name}"
            f"__Size:{sx:.6f},{sy:.6f},{sz:.6f}"
        )


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
