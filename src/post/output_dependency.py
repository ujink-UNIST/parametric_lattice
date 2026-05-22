"""Post output dependency graph.

This mirrors :mod:`postprocess.output_dependency` so the new post/ pipeline can
resolve prerequisites and compute a safe execution order.

Only the dependency declarations live here.
"""

from __future__ import annotations

# key: output prefix
# value: tuple of prerequisite output prefixes that must be computed first
OUTPUT_DEPENDENCIES: dict[str, tuple[str, ...]] = {
    "boundary_traction": ("boundary_force",),
    "boundary_stress": ("boundary_traction",),
    # Derived in Python but depends on boundary_stress being computed.
    "boundary_modulus": ("boundary_stress",),
    "boundary_modulus_ratio": ("boundary_modulus",),
    "effective_youngs_modulus": ("boundary_modulus",),
    "effective_shear_modulus": ("boundary_modulus",),
    # Mesh-derived (computed in Python). No MAPDL dependency.
    "boundary_touch_area": (),
    "boundary_touch_area_ratio": ("boundary_touch_area",),
    # Contact traction/stress: derived in Python (boundary_force normalized by touch area).
    "contact_traction": ("boundary_force", "boundary_touch_area"),
    "contact_stress": ("contact_traction",),
    # Modal-only
    **{f"res_freq_{i}": () for i in range(1, 21)},
    **{f"part_factor_{i}": () for i in range(1, 21)},
    **{f"eff_modal_mass_{i}": () for i in range(1, 21)},
    "volume_stress": (),
    "volume_energy": (),
    # Volume averages require both the sum and the total volume.
    "volume_avg_stress": ("volume_stress", "volume"),
    "volume_avg_energy": ("volume_energy", "volume"),
    # Intermediate outputs (not written to t_out). Kept here so they can
    # participate in prefix expansion/toposort if requested.
    "elem_sene": (),
    "node_sene": (),
    "node_volmass": (),
    "volume": (),
}
