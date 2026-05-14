# line_command.py

from core.apdl_block import (
    apdl_block,
    apdl_comment,
    apdl_inline_comment,
)
from core.apdl_commands import ApdlCommands
from core.unit_cell import UnitCell


def build_line_commands_(
    unit_cell: UnitCell,
) -> ApdlCommands:
    cmds: list[str] = []
    cmds.extend(apdl_block(f"""
{apdl_comment("Create beam centerlines from lattice edges")}

"""))

    count: int = unit_cell.edges.shape[0]
    digits = len(str(count - 1))

    for i, edge in enumerate(unit_cell.edges):
        # Some test fixtures carry extra per-edge metadata in additional columns.
        n1_idx = int(edge[0])
        n2_idx = int(edge[1])

        kp1_id = n1_idx + 1
        kp2_id = n2_idx + 1
        cmds.extend(
            apdl_block(
                f"""L,{kp1_id},{kp2_id} {apdl_inline_comment(
                    f"{i:>{digits}}: e {n1_idx} {n2_idx}")}"""
            )
        )

    return tuple(cmds)
