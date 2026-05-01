# File: c:\Users\USER\Documents\parametric_lattice\src\core\parameters\results_params.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


from dataclasses import dataclass
from fractions import Fraction


@dataclass(frozen=True)
class ResultsParams:
    value: tuple[str, ...]
    scale_factors: tuple[Fraction, ...]
