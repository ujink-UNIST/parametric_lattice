#meshing_params.py
"""Module for meshing params functionality in src.core.parameters."""

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class MeshingParams:
    max_element_size: float

    def to_string(self) -> str:
        return f"MaxElementSize:{self.max_element_size:.16e}"


def build_meshing_params(
    input_header: Tuple[str, ...], row: Tuple[Any, ...]
) -> MeshingParams:
    col_idx = {name: i for i, name in enumerate(input_header)}

    return MeshingParams(
        max_element_size=float(row[col_idx["max_element_size"]]),
    )
