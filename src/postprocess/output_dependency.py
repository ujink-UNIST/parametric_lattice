"""Postprocess output dependency graph.

Defines dependencies between postprocess output *prefixes*.

Example:
  boundary_stress depends on boundary_traction

This is intended to be used by the postprocess pipeline to:
- expand requested outputs to include prerequisites
- derive a safe computation order (topological sort)

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
    "volume_stress": (),
    "volume_energy": (),
    # Volume averages require both the sum and the total volume.
    "volume_avg_stress": ("volume_stress", "volume"),
    "volume_avg_energy": ("volume_energy", "volume"),
    # Intermediate outputs (not written to Excel). Kept here so they can
    # participate in prefix expansion/toposort if requested.
    "elem_sene": (),
    "node_sene": (),
    "node_volmass": (),
    "volume": (),
}
