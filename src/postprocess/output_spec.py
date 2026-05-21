"""Postprocess output specification.

This module defines which output *prefixes* are supported by the postprocess
pipeline and how many components each prefix must produce.

Excel `t_output` columns are expected to follow:
- Scalars: `<prefix>`
- Vector/tensor components: `<prefix>_<COMP>` where COMP is one of
  X,Y,Z,XX,XY,XZ,YX,YY,YZ,ZX,ZY,ZZ.

The excel integration validates the header against this spec.
"""

from __future__ import annotations

# NOTE: Extend this dict when you add new postprocess outputs.
# Values must be one of: 1, 3, 6, 9.
POSTPROCESS_OUTPUT_SPEC: dict[str, int] = {
    "index": 1,
    "hash": 1,
    "boundary_traction": 9,
    "boundary_force": 9,
    "boundary_moment": 9,
    "boundary_stress": 6,
    # Derived (Python) outputs
    "boundary_modulus": 6,
    "boundary_modulus_ratio": 6,
    "effective_youngs_modulus": 3,
    "effective_shear_modulus": 3,
    "volume_stress": 6,
    "volume_avg_stress": 6,
    "volume_energy": 1,
    "volume_avg_energy": 1,
    "volume": 1,
    # Modal resonant frequencies (scalar columns res_freq_1 .. res_freq_20)
    **{f"res_freq_{i}": 1 for i in range(1, 21)},
}

# Output availability by simulation_type (from Excel t_input.simulation_type).
# Policy:
# - volume: available for all simulation types (modal/modal_ff + xx..xz)
# - everything else in this postprocess module: only for xx/yy/zz/xy/yz/xz
_SIM_TYPES_MODAL: frozenset[str] = frozenset({"modal", "modal_ff"})

# Static solve types (strain-driven macro deformation cases)
_SIM_TYPES_STATIC_NORMAL: frozenset[str] = frozenset({"xx", "yy", "zz"})
_SIM_TYPES_STATIC_SHEAR: frozenset[str] = frozenset({"xy", "yz", "xz"})
_SIM_TYPES_STATIC: frozenset[str] = _SIM_TYPES_STATIC_NORMAL | _SIM_TYPES_STATIC_SHEAR

_SIM_TYPES_ALL: frozenset[str] = _SIM_TYPES_MODAL | _SIM_TYPES_STATIC

POSTPROCESS_OUTPUT_ALLOWED_SIM_TYPES: dict[str, frozenset[str]] = {
    # Excel-written scalars: always allowed
    "index": _SIM_TYPES_ALL,
    "hash": _SIM_TYPES_ALL,
    # Volume is always available
    "volume": _SIM_TYPES_ALL,
    # Modal-only outputs
    **{f"res_freq_{i}": _SIM_TYPES_MODAL for i in range(1, 21)},
    # Everything else: only xx..xz
    "boundary_traction": _SIM_TYPES_STATIC,
    "boundary_force": _SIM_TYPES_STATIC,
    "boundary_moment": _SIM_TYPES_STATIC,
    "boundary_stress": _SIM_TYPES_STATIC,
    "boundary_modulus": _SIM_TYPES_STATIC,
    "boundary_modulus_ratio": _SIM_TYPES_STATIC,
    "effective_youngs_modulus": _SIM_TYPES_STATIC_NORMAL,
    "effective_shear_modulus": _SIM_TYPES_STATIC_SHEAR,
    "volume_stress": _SIM_TYPES_STATIC,
    "volume_avg_stress": _SIM_TYPES_STATIC,
    "volume_energy": _SIM_TYPES_STATIC,
    "volume_avg_energy": _SIM_TYPES_STATIC,
}


def is_postprocess_output_allowed(prefix: str, simulation_type: str) -> bool:
    allowed = POSTPROCESS_OUTPUT_ALLOWED_SIM_TYPES.get(prefix)
    if allowed is None:
        # Unknown prefix: let existing validation raise elsewhere.
        return True
    return simulation_type in allowed
