# File: c:\Users\USER\Documents\parametric_lattice\src\core\geometric\transform.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Wed Apr 29 2026
# Modified: Wed Apr 29 2026


import numpy as np

from core.floats.vector import Vector3


def transform_coords(
    node: Vector3, size: Vector3
) -> np.ndarray:
    return (node - 0.5) * size
