from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from core.floats.vector import Vector3, Vector3x3


def compute_traction(
    force: Vector3,
    area: float,
) -> Vector3:
    return force / area


def average_force(
    plus_force: Vector3,
    minus_force: Vector3,
) -> Vector3:
    return 0.5 * (plus_force - minus_force)


def compute_stress_tensor(
    face_tractions: Dict[str, Vector3],
) -> Vector3x3:
    tx_px, ty_px, tz_px = face_tractions["+x"]
    tx_py, ty_py, tz_py = face_tractions["+y"]
    tx_pz, ty_pz, tz_pz = face_tractions["+z"]

    return np.array(
        [
            [
                tx_px,
                tx_py,
                tx_pz,
            ],  # row x: σ_xx, σ_xy, σ_xz
            [
                ty_px,
                ty_py,
                ty_pz,
            ],  # row y: σ_yx, σ_yy, σ_yz
            [
                tz_px,
                tz_py,
                tz_pz,
            ],  # row z: σ_zx, σ_zy, σ_zz
        ],
        dtype=np.float64,
    )
