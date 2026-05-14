# sim_result.py

from dataclasses import dataclass


from core.floats.vector import OutputNumericValue


@dataclass
class SimResult:
    status: str
    error_msg: str
    results: dict[str, OutputNumericValue]
