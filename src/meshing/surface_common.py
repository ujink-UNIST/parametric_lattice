#surface_common.py
"""Shared helpers for surface meshing command builders."""

from __future__ import annotations

import numpy as np

from core.parameters.geometry_params import GeometryParams

Axis = str
Translation = tuple[float, float, float]


def surface_matching_tolerance(geometry_params: GeometryParams) -> float:
    """Return the tolerance used for midpoint/centroid matching."""
    return float(np.linalg.norm(geometry_params.size) * 0.005)


def half_sizes(geometry_params: GeometryParams) -> tuple[float, float, float]:
    """Return unit-cell half lengths as plain Python floats."""
    hx, hy, hz = geometry_params.size / 2
    return float(hx), float(hy), float(hz)


def translation_from_axes(offsets: dict[Axis, float]) -> Translation:
    """Convert an axis-to-offset mapping into APDL MSHCOPY translation values."""
    return (
        float(offsets.get("X", 0.0)),
        float(offsets.get("Y", 0.0)),
        float(offsets.get("Z", 0.0)),
    )
