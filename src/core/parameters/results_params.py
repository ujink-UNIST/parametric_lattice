# results_params.py

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class ResultsParams:
    value: tuple[str, ...]

    def to_string(self) -> str:
        # Example: "stress_xx__stress_xy__force_z" ...
        return "__".join(self.value)
