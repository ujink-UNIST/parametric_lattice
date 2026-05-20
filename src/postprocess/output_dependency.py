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
    # node_sene currently has no prerequisites (kept here so it can participate
    # in prefix expansion/toposort if requested).
    "node_sene": (),
    "node_volmass": (),
    "volume": (),
}
