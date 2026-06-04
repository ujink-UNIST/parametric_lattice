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
_SIM_TYPES_STATIC_BULK: frozenset[str] = frozenset({"xyz"})
_SIM_TYPES_STATIC: frozenset[str] = _SIM_TYPES_STATIC_NORMAL | _SIM_TYPES_STATIC_SHEAR | _SIM_TYPES_STATIC_BULK
_SIM_TYPES_ALL: frozenset[str] = _SIM_TYPES_MODAL | _SIM_TYPES_STATIC

# Output availability by simulation type.
# Keys are output prefixes used by the post pipeline.
POST_OUTPUT_ALLOWED_SIM_TYPES: dict[str, frozenset[str]] = {
    # Always allowed identifiers
    "id.index": _SIM_TYPES_ALL,
    "id.hash": _SIM_TYPES_ALL,

    # Volume: static only
    "volume.solid.value": _SIM_TYPES_STATIC,
    "mass.solid.value": _SIM_TYPES_STATIC,
    "volume_fraction.cell.value": _SIM_TYPES_STATIC,
    "element.count": _SIM_TYPES_STATIC,

    # Modal-only outputs
    **{f"res_freq_{i}": _SIM_TYPES_MODAL for i in range(1, 11)},
    **{f"part_factor_{i}": _SIM_TYPES_MODAL for i in range(1, 11)},
    **{f"eff_modal_mass_{i}": _SIM_TYPES_MODAL for i in range(1, 11)},

    # Static-only outputs
    "traction.boundary.value": _SIM_TYPES_STATIC,
    "force.boundary.value": _SIM_TYPES_STATIC,
    "moment.boundary.value": _SIM_TYPES_STATIC,
    "stress.boundary.value": _SIM_TYPES_STATIC,
    "modulus.boundary.value": _SIM_TYPES_STATIC,
    "modulus.boundary.ratio": _SIM_TYPES_STATIC,
    "area.boundary_contact.ratio": _SIM_TYPES_STATIC,

    "modulus.effective.youngs": _SIM_TYPES_STATIC_NORMAL,
    "modulus.effective.shear": _SIM_TYPES_STATIC_SHEAR,
    "modulus.effective.bulk": _SIM_TYPES_STATIC_BULK,

    "modulus.effective.youngs.specific": _SIM_TYPES_STATIC_NORMAL,
    "modulus.effective.shear.specific": _SIM_TYPES_STATIC_SHEAR,

    "modulus.effective.youngs.ratio": _SIM_TYPES_STATIC_NORMAL,
    "modulus.effective.shear.ratio": _SIM_TYPES_STATIC_SHEAR,

    "area.boundary_contact.value": _SIM_TYPES_STATIC,
    "area.boundary_contact.ratio": _SIM_TYPES_STATIC,

    "traction.contact.value": _SIM_TYPES_STATIC,
    "stress.contact.value": _SIM_TYPES_STATIC,

    "stress.volume.sum": _SIM_TYPES_STATIC,
    "stress.volume.avg": _SIM_TYPES_STATIC,
    "energy.strain.total": _SIM_TYPES_STATIC,
    "energy.strain_density": _SIM_TYPES_STATIC,
    "energy.strain_density.reference": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized": _SIM_TYPES_STATIC,
    "energy.strain_density.mean": _SIM_TYPES_STATIC,
    "energy.strain_density.std": _SIM_TYPES_STATIC,
    "energy.strain_density.median": _SIM_TYPES_STATIC,
    "energy.strain_density.min": _SIM_TYPES_STATIC,
    "energy.strain_density.max": _SIM_TYPES_STATIC,
    "energy.strain_density.range": _SIM_TYPES_STATIC,
    "energy.strain_density.p95": _SIM_TYPES_STATIC,
    "energy.strain_density.p99": _SIM_TYPES_STATIC,
    "energy.strain_density.cv": _SIM_TYPES_STATIC,
    "energy.strain_density.skewness": _SIM_TYPES_STATIC,
    "energy.strain_density.kurtosis": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.mean": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.std": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.median": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.min": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.max": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.range": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.p95": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.p99": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.cv": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.skewness": _SIM_TYPES_STATIC,
    "energy.strain_density.normalized.kurtosis": _SIM_TYPES_STATIC,
}


def is_post_output_allowed(prefix: str, sim_type: str) -> bool:
    """Return True if output `prefix` is allowed for the given sim_type."""

    allowed = POST_OUTPUT_ALLOWED_SIM_TYPES.get(prefix)
    if allowed is None:
        # Unknown prefix: let upstream validation decide.
        return True
    return sim_type in allowed
