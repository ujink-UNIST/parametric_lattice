#results_params.py
"""Module for results params functionality in src.core.parameters."""

from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class ResultsParams:
    value: tuple[str, ...]

    def to_string(self) -> str:
        # Example: "stress_xx__stress_xy__force_z" ...
        return "__".join(self.value)
