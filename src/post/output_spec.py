"""Post output specification (long-format t_out).

Unlike the legacy Excel wide-format `t_output` spec, the long-format `t_out`
uses a fixed column set (see :data:`post.row.T_OUT_COLUMNS`). Therefore, this
module primarily exists to validate *availability* of a requested output prefix
based on the simulation type (sim_case.post_mesh_spec.setup.sim_type).

This mirrors the simulation-type policy from :mod:`postprocess.output_spec`.
"""

from __future__ import annotations

# Simulation types
_SIM_TYPES_MODAL: frozenset[str] = frozenset({"modal", "modal_ff"})
_SIM_TYPES_STATIC_NORMAL: frozenset[str] = frozenset({"xx", "yy", "zz"})
_SIM_TYPES_STATIC_SHEAR: frozenset[str] = frozenset({"xy", "yz", "xz"})
_SIM_TYPES_STATIC: frozenset[str] = _SIM_TYPES_STATIC_NORMAL | _SIM_TYPES_STATIC_SHEAR
_SIM_TYPES_ALL: frozenset[str] = _SIM_TYPES_MODAL | _SIM_TYPES_STATIC

# Output availability by simulation type.
# Keys are output prefixes used by the post pipeline.
POST_OUTPUT_ALLOWED_SIM_TYPES: dict[str, frozenset[str]] = {
    # Always allowed identifiers
    "index": _SIM_TYPES_ALL,
    "hash": _SIM_TYPES_ALL,
    # Volume: static only
    "volume": _SIM_TYPES_STATIC,
    "mass": _SIM_TYPES_STATIC,
    # Modal-only outputs
    **{f"res_freq_{i}": _SIM_TYPES_MODAL for i in range(1, 21)},
    **{f"part_factor_{i}": _SIM_TYPES_MODAL for i in range(1, 21)},
    **{f"eff_modal_mass_{i}": _SIM_TYPES_MODAL for i in range(1, 21)},
    # Static-only outputs
    "boundary_traction": _SIM_TYPES_STATIC,
    "boundary_force": _SIM_TYPES_STATIC,
    "boundary_moment": _SIM_TYPES_STATIC,
    "boundary_stress": _SIM_TYPES_STATIC,
    "boundary_modulus": _SIM_TYPES_STATIC,
    "boundary_modulus_ratio": _SIM_TYPES_STATIC,
    "effective_youngs_modulus": _SIM_TYPES_STATIC_NORMAL,
    "effective_shear_modulus": _SIM_TYPES_STATIC_SHEAR,
    "specific_youngs_modulus": _SIM_TYPES_STATIC_NORMAL,
    "specific_shear_modulus": _SIM_TYPES_STATIC_SHEAR,
    "boundary_touch_area": _SIM_TYPES_STATIC,
    "boundary_touch_area_ratio": _SIM_TYPES_STATIC,
    "contact_traction": _SIM_TYPES_STATIC,
    "contact_stress": _SIM_TYPES_STATIC,
    "volume_stress": _SIM_TYPES_STATIC,
    "volume_avg_stress": _SIM_TYPES_STATIC,
    "volume_energy": _SIM_TYPES_STATIC,
    "volume_avg_energy": _SIM_TYPES_STATIC,
}


def is_post_output_allowed(prefix: str, sim_type: str) -> bool:
    """Return True if output `prefix` is allowed for the given sim_type."""

    allowed = POST_OUTPUT_ALLOWED_SIM_TYPES.get(prefix)
    if allowed is None:
        # Unknown prefix: let upstream validation decide.
        return True
    return sim_type in allowed
