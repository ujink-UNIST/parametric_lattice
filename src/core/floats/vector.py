# File: c:\Users\USER\Documents\parametric_lattice\src\core\floats\vector3.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


import numpy as np
from jaxtyping import Float, Int

Vector3 = Float[np.ndarray, "3"]
Vector3Int = Int[np.ndarray, "3"]

Vector6 = Float[np.ndarray, "6"]
Vector3x3 = Float[np.ndarray, "3 3"]

OutputNumericValue = (
    int | float | Vector3 | Vector6 | Vector3x3
)
