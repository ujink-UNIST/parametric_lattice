from __future__ import annotations

from dataclasses import dataclass
from typing import Any

T_OUT_COLUMNS: tuple[str, ...] = (
    "index",
    "hash",
    "category",
    "row",
    "col",
    "value",
    "unit",
)


@dataclass(frozen=True, slots=True)
class TOutRow:
    """One record (one line) in the long-format t_out output.

    Conventions (project-wide):
      - Missing metrics are represented by *absence of a row* (do not emit NA).
      - unit is a plain string following the model unit system (no conversion).

    index: 1-based case index (from SimCase.row_idx + 1)
    row/col: integer indices used for tensor assembly.
    """

    index: int
    hash: str
    category: str
    row: int
    col: int
    value: float
    unit: str

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"index must be >= 0: {self.index}")
        if self.row <= 0:
            raise ValueError(f"row must be >= 1: {self.row}")
        if self.col <= 0:
            raise ValueError(f"col must be >= 1: {self.col}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": int(self.index),
            "hash": str(self.hash),
            "category": str(self.category),
            "row": int(self.row),
            "col": int(self.col),
            "value": float(self.value),
            "unit": str(self.unit),
        }
