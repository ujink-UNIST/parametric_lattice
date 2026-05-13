# File: c:\Users\USER\Documents\parametric_lattice\src\core\parameters\setup_params.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


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
            f"__Strain:{self.strain:.6f}"
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
