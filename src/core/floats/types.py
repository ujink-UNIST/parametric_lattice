# types.py

"""Centralized numeric type aliases.

These are lightweight *type hints* (mainly for NumPy arrays) used across the
project. Keeping them here avoids ad-hoc aliases spread throughout the codebase.

Runtime impact: none.
"""

from __future__ import annotations

import numpy as np
from jaxtyping import Float, Int

# Generic vectors / matrices
Vector3 = Float[np.ndarray, "3"]
Vector3Int = Int[np.ndarray, "3"]
Vector6 = Float[np.ndarray, "6"]
Vector3x3 = Float[np.ndarray, "3 3"]

# Unit-cell layout arrays
Nodes = Float[np.ndarray, "N 3"]
NodeBoundaries = Int[np.ndarray, "N 3"]
Edges = Int[np.ndarray, "E 2"]
EdgeTypeIds = Int[np.ndarray, "E"]
EdgeRatios = Float[np.ndarray, "E"]
EdgeNormals = Float[np.ndarray, "E 3"]

OutputNumericValue = int | float | Vector3 | Vector6 | Vector3x3

__all__ = [
    "Vector3",
    "Vector3Int",
    "Vector6",
    "Vector3x3",
    "Nodes",
    "NodeBoundaries",
    "Edges",
    "EdgeTypeIds",
    "EdgeRatios",
    "EdgeNormals",
    "OutputNumericValue",
]
