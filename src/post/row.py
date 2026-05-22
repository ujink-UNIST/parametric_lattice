from __future__ import annotations

from dataclasses import dataclass
from typing import Any

T_OUT_COLUMNS: tuple[str, ...] = (
    "index",
    "hash",
    "category",
    "metric",
    "component",
    "value",
    "unit",
)


@dataclass(frozen=True, slots=True)
class TOutRow:
    """One record (one line) in the long-format t_out output.

    Conventions (project-wide):
      - Scalar metrics MUST use component == "".
      - Missing metrics are represented by *absence of a row* (do not emit NA).
      - unit is a plain string following the model unit system (no conversion).
    """

    index: int
    hash: str
    category: str
    metric: str
    component: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"index must be >= 0: {self.index}")
        if not isinstance(self.component, str):
            raise TypeError("component must be a string")
        # Enforce scalar convention at the type level as much as possible.
        # (Vector/tensor rows should supply a non-empty component explicitly.)
        if self.component is None:  # type: ignore[truthy-bool]
            raise ValueError('component must be "" for scalars or a non-empty string')

    def as_dict(self) -> dict[str, Any]:
        return {
            "index": int(self.index),
            "hash": str(self.hash),
            "category": str(self.category),
            "metric": str(self.metric),
            "component": str(self.component),
            "value": float(self.value),
            "unit": str(self.unit),
        }
