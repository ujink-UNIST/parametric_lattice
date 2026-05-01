"""Pure math helpers for homogenized stress extraction."""

from __future__ import annotations

from typing import Dict, Tuple

from core.types_ import StressTensor9


def compute_traction(
    force: Tuple[float, float, float],
    area: float,
) -> Tuple[float, float, float]:
    """Convert a resultant face force into a traction vector."""
    return (
        force[0] / area,
        force[1] / area,
        force[2] / area,
    )


def average_force(
    plus_force: Tuple[float, float, float],
    minus_force: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """Average opposite-face forces to reduce numerical imbalance noise."""
    return (
        0.5 * (plus_force[0] - minus_force[0]),
        0.5 * (plus_force[1] - minus_force[1]),
        0.5 * (plus_force[2] - minus_force[2]),
    )


def compute_stress_tensor(
    face_tractions: Dict[str, Tuple[float, float, float]],
) -> StressTensor9:
    """Map positive-face traction vectors into the project's stress layout."""
    tx_px, ty_px, tz_px = face_tractions["+x"]
    tx_py, ty_py, tz_py = face_tractions["+y"]
    tx_pz, ty_pz, tz_pz = face_tractions["+z"]

    return StressTensor9(
        xx=tx_px,
        yx=ty_px,
        zx=tz_px,
        xy=tx_py,
        yy=ty_py,
        zy=tz_py,
        xz=tx_pz,
        yz=ty_pz,
        zz=tz_pz,
    )


def check_force_balance(
    face_forces: Dict[str, Tuple[float, float, float]],
    tol: float = 1e-3,
) -> Dict[str, float]:
    """Return normalized force-imbalance metrics for each Cartesian axis."""
    del tol
    axes = {"x": 0, "y": 1, "z": 2}
    result = {}
    global_max = (
        max(abs(face_forces[face][i]) for face in face_forces for i in range(3))
        or 1.0
    )
    for axis_name, idx in axes.items():
        total = sum(face_forces[face][idx] for face in face_forces)
        result[axis_name] = abs(total) / global_max
    return result
