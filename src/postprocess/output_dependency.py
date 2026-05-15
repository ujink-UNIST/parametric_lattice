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
    # boundary_traction is derived from boundary_force (+ geometry face areas)
    "boundary_traction": ("boundary_force",),
    # boundary_stress can only be computed if boundary_traction is available
    "boundary_stress": ("boundary_traction",),
}
