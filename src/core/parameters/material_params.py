# material_params.py

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class MaterialParams:
    e_mod: float
    nu: float
    density: float

    def to_string(self) -> str:
        return (
            f"E:{self.e_mod:.6f}"
            f"__Nu:{self.nu:.6f}"
            f"__Density:{self.density:.6f}"
        )


def build_material_params(
    input_header: Tuple[str, ...], row: Tuple[Any, ...]
) -> MaterialParams:
    col_idx = {name: i for i, name in enumerate(input_header)}

    return MaterialParams(
        e_mod=float(row[col_idx["e_mod"]]),
        nu=float(row[col_idx["nu"]]),
        density=float(row[col_idx["density"]]),
    )
