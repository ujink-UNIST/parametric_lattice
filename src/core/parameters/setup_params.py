# setup_params.py

from dataclasses import dataclass
from typing import Any, Tuple


@dataclass(frozen=True)
class SetupParams:
    sim_type: str
    strain: float
    n_substeps: int = 1

    def to_string(self) -> str:
        return (
            f"SimType:{self.sim_type}"
            f"__Strain:{self.strain:.16e}"
            f"__Substeps:{self.n_substeps}"
        )


def build_setup_params(
    input_header: Tuple[str, ...], row: Tuple[Any, ...]
) -> SetupParams:
    col_idx = {name: i for i, name in enumerate(input_header)}

    return SetupParams(
        sim_type=str(row[col_idx["sim_type"]]),
        strain=float(row[col_idx["strain"]]),
        n_substeps=int(row[col_idx["n_substeps"]]),
    )
