# File: c:\Users\USER\Documents\parametric_lattice\src\core\sim_result.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass


from core.floats.vector import OutputNumericValue


@dataclass
class SimResult:
    status: str
    error_msg: str
    results: dict[str, OutputNumericValue]
