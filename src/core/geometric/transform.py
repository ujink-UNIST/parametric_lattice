#transform.py
"""Module for transform functionality in src.core.geometric."""

import numpy as np

from core.floats.vector import Vector3


def transform_coords(
    node: Vector3, size: Vector3
) -> np.ndarray:
    return (node - 0.5) * size
