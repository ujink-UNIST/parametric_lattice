"""Post output dependency graph.

This mirrors :mod:`postprocess.output_dependency` so the new post/ pipeline can
resolve prerequisites and compute a safe execution order.

Only the dependency declarations live here.
"""

from __future__ import annotations

# key: output prefix
# value: tuple of prerequisite output prefixes that must be computed first


OUTPUT_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "traction.boundary.value": ("force.boundary.value",),
    "stress.boundary.value": ("traction.boundary.value",),

    # Derived in Python but depends on boundary_stress being computed.
    "modulus.boundary.value": ("stress.boundary.value",),
    "modulus.boundary.ratio": ("modulus.boundary.value",),

    "modulus.effective.youngs": ("modulus.boundary.value",),
    "modulus.effective.shear": ("modulus.boundary.value",),
    "modulus.effective.bulk": ("stress.boundary.value",),

    # Specific moduli (divide by density)
    "modulus.effective.youngs.specific": ("modulus.effective.youngs",),
    "modulus.effective.shear.specific": ("modulus.effective.shear",),

    "modulus.effective.youngs.ratio": ("modulus.effective.youngs",),
    "modulus.effective.shear.ratio": ("modulus.effective.shear",),

    # Mesh-derived (computed in Python). No MAPDL dependency.
    "area.boundary_contact.value": (),
    "area.boundary_contact.ratio": ("area.boundary_contact.value",),

    # Contact traction/stress: derived in Python (boundary_force normalized by touch area).
    "traction.contact.value": ("force.boundary.value", "area.boundary_contact.value"),
    "stress.contact.value": ("traction.contact.value",),

    # Modal-only (kept as-is; categories are modal.* and handled elsewhere)
    **{f"res_freq_{i}": () for i in range(1, 21)},
    **{f"part_factor_{i}": () for i in range(1, 21)},
    **{f"eff_modal_mass_{i}": () for i in range(1, 21)},

    "stress.volume.sum": (),
    "energy.strain.total": (),
    # Volume averages require both the sum and the total volume.
    "stress.volume.avg": ("stress.volume.sum", "volume.solid.value"),
    "energy.strain_density.avg": ("energy.strain.total", "volume.solid.value"),

    "mass.solid.value": ("volume.solid.value",),
    "volume_fraction.cell.value": ("volume.solid.value",),

    # Intermediate outputs (not written to t_out). Kept here so they can
    # participate in prefix expansion/toposort if requested.
    "elem_sene": (),
    "node_sene": (),
    "node_volmass": (),
    "volume.solid.value": (),
}
