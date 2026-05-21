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
    "volume_stress": 6,
    "volume_avg_stress": 6,
    "volume_energy": 1,
    "volume_avg_energy": 1,
    "volume": 1,
}
