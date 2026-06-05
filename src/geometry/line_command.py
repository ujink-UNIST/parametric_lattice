#line_command.py
"""Module for line command functionality in src.geometry."""

from core.apdl_block import (
    apdl_block,
    apdl_comment,
    apdl_inline_comment,
)
from core.apdl_commands import ApdlCommands
from core.parameters.element_type_params import ElementTypeParams
from core.unit_cell import UnitCell


def build_line_commands_(
    unit_cell: UnitCell,
    element_type: ElementTypeParams,
) -> ApdlCommands:
    cmds: list[str] = []
    cmds.extend(apdl_block(f"""
{apdl_comment('Create beam centerlines from lattice edges')}

"""))

    # For solid models we don't use beam centerlines.
    if "SOLID" in element_type.model:
        return ()

    n_edges = int(unit_cell.edges.shape[0])
    digits = len(str(max(n_edges - 1, 0)))

    # One beam line per original lattice edge. No joint subdivision.
    for i, edge in enumerate(unit_cell.edges):
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])
        kp1_id = n1_idx + 1
        kp2_id = n2_idx + 1
        cmds.extend(
            apdl_block(
                f"L,{kp1_id},{kp2_id} {apdl_inline_comment(f'{i:>{digits}}: e {n1_idx} {n2_idx}')}"
            )
        )

    return tuple(cmds)
