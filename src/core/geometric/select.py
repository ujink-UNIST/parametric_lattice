#select.py
"""Module for select functionality in src.core.geometric."""

from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.geometric.transform import transform_coords
from core.parameters.geometry_params import GeometryParams
from core.unit_cell import UnitCell

SELECTOR_TO_NAME: dict[str, str] = {
    # Face-only selections (exclude edges/corners by also restricting the other
    # two axes). This avoids double-counting when a boundary node lies on more
    # than one face.
    "+x": "BOUNDARY_FACE_PX",
    "-x": "BOUNDARY_FACE_NX",
    "+y": "BOUNDARY_FACE_PY",
    "-y": "BOUNDARY_FACE_NY",
    "+z": "BOUNDARY_FACE_PZ",
    "-z": "BOUNDARY_FACE_NZ",
    "all": "BOUNDARY_NODES",
}


def get_all_boundary_nodes(
    geometry_params: GeometryParams,
) -> ApdlCommands:
    size: Vector3 = geometry_params.size
    half_size = size / 2

    eps = min(size[0], size[1], size[2]) * 1e-6

    return (
        "NSEL,NONE",
        f"NSEL,S,LOC,X,{-half_size[0]-eps:.10g},{-half_size[0]+eps:.10g}",
        f"NSEL,A,LOC,X,{half_size[0]-eps:.10g},{half_size[0]+eps:.10g}",
        f"NSEL,A,LOC,Y,{-half_size[1]-eps:.10g},{-half_size[1]+eps:.10g}",
        f"NSEL,A,LOC,Y,{half_size[1]-eps:.10g},{half_size[1]+eps:.10g}",
        f"NSEL,A,LOC,Z,{-half_size[2]-eps:.10g},{-half_size[2]+eps:.10g}",
        f"NSEL,A,LOC,Z,{half_size[2]-eps:.10g},{half_size[2]+eps:.10g}",
        "CM,BOUNDARY_NODES,NODE",
        "NSEL,ALL",
    )


def boundary_index_from_triplet(
    triplet: tuple[int, int, int],
) -> int:
    """Encode (-1/0/+1) boundary triplet into index 0..26.

    Encoding:
      code(-1)=0, code(0)=1, code(+1)=2
      idx = code(x) + 3*code(y) + 9*code(z)
    """

    x, y, z = triplet
    return (x + 1) + 3 * (y + 1) + 9 * (z + 1)


def get_boundary_index_nodes(
    geometry_params: GeometryParams,
) -> ApdlCommands:
    size: Vector3 = geometry_params.size
    half = size / 2
    eps = min(size[0], size[1], size[2]) * 1e-6

    def _axis_filter(axis: str, value: int) -> list[str]:
        h = {"X": half[0], "Y": half[1], "Z": half[2]}[axis]
        if value < 0:
            return [
                f"NSEL,R,LOC,{axis},{-h-eps:.10g},{-h+eps:.10g}",
            ]
        if value > 0:
            return [
                f"NSEL,R,LOC,{axis},{h-eps:.10g},{h+eps:.10g}",
            ]
        # value == 0: exclude both faces on this axis
        return [
            f"NSEL,U,LOC,{axis},{-h-eps:.10g},{-h+eps:.10g}",
            f"NSEL,U,LOC,{axis},{h-eps:.10g},{h+eps:.10g}",
        ]

    cmds: list[str] = ["NSEL,NONE"]

    for idx in range(27):
        x, y, z = boundary_triplet_from_index(idx)

        # Start from endpoint nodes, then apply X->Y->Z filters.
        cmds.append("NSEL,ALL")
        cmds.extend(_axis_filter("X", x))
        cmds.extend(_axis_filter("Y", y))
        cmds.extend(_axis_filter("Z", z))
        cmds.append(f"CM,BOUNDARY_IDX_{idx},NODE")
        cmds.append("NSEL,ALL")

    return tuple(cmds)


# def get_boundary_endpoint_nodes(
#     unit_cell: UnitCell,
#     geometry_params: GeometryParams,
# ) -> ApdlCommands:
#     size: Vector3 = geometry_params.size
#     eps = min(size[0], size[1], size[2]) * 1e-6

#     boundary_node_ids = [
#         node_id
#         for node_id, boundary in enumerate(
#             unit_cell.node_boundaries, start=1
#         )
#         if any(value != 0 for value in boundary)
#     ]

#     if not boundary_node_ids:
#         return ()

#     cmds: list[str] = []
#     temp_components: list[str] = []

#     for node_id in boundary_node_ids:
#         node = transform_coords(
#             unit_cell.nodes[node_id - 1], size
#         )
#         temp_name = f"_BOUNDARY_ENDPOINT_{node_id}"
#         temp_components.append(temp_name)
#         cmds.extend(
#             (
#                 f"NSEL,S,LOC,X,{node[0]-eps:.10g},{node[0]+eps:.10g}",
#                 f"NSEL,R,LOC,Y,{node[1]-eps:.10g},{node[1]+eps:.10g}",
#                 f"NSEL,R,LOC,Z,{node[2]-eps:.10g},{node[2]+eps:.10g}",
#                 f"CM,{temp_name},NODE",
#             )
#         )

#     for i, temp_name in enumerate(temp_components):
#         mode = "S" if i == 0 else "A"
#         cmds.append(f"CMSEL,{mode},{temp_name}")

#     cmds.extend(
#         (
#             "CM,BOUNDARY_ENDPOINT_NODES,NODE",
#             "NSEL,ALL",
#         )
#     )
#     return tuple(cmds)


def get_all_periodic_nodes(
    geometry_params: GeometryParams,
) -> ApdlCommands:
    """Create node components for periodic faces and for "pure" boundary faces.

    Components created:
      - PERIODIC_NODES_{N/P}{X/Y/Z}: full face (includes edges/corners). Used by
        periodic constraint builders (e.g. setup.modal_applicator).
      - BOUNDARY_FACE_{N/P}{X/Y/Z}: face interior only (excludes edges/corners)
        by restricting the other two axes away from their ±half faces.
        Intended for "boundary name" selection to avoid overlap between faces.
    """

    size: Vector3 = geometry_params.size
    half_size = size / 2

    eps = min(size[0], size[1], size[2]) * 1e-6

    hx, hy, hz = float(half_size[0]), float(half_size[1]), float(half_size[2])

    def _restrict_other_axes(other_a: str, ha: float, other_b: str, hb: float) -> tuple[str, ...]:
        """Constrain the other two coordinates to lie within the cell bounds.

        This is intentionally inclusive of edges/corners; it just prevents
        selecting nodes that numerically drift slightly outside the box.
        """
        return (
            f"NSEL,R,LOC,{other_a},{-ha-eps:.10g},{ha+eps:.10g}",
            f"NSEL,R,LOC,{other_b},{-hb-eps:.10g},{hb+eps:.10g}",
        )

    return (
        "NSEL,NONE",
        # Full periodic faces (no exclusions)
        f"NSEL,S,LOC,X,{-hx-eps:.10g},{-hx+eps:.10g}",
        "CM, PERIODIC_NODES_NX, NODE",
        f"NSEL,S,LOC,X,{hx-eps:.10g},{hx+eps:.10g}",
        "CM, PERIODIC_NODES_PX, NODE",
        f"NSEL,S,LOC,Y,{-hy-eps:.10g},{-hy+eps:.10g}",
        "CM, PERIODIC_NODES_NY, NODE",
        f"NSEL,S,LOC,Y,{hy-eps:.10g},{hy+eps:.10g}",
        "CM, PERIODIC_NODES_PY, NODE",
        f"NSEL,S,LOC,Z,{-hz-eps:.10g},{-hz+eps:.10g}",
        "CM, PERIODIC_NODES_NZ, NODE",
        f"NSEL,S,LOC,Z,{hz-eps:.10g},{hz+eps:.10g}",
        "CM, PERIODIC_NODES_PZ, NODE",
        # Boundary face components with explicit constraints on the other axes
        # (your requested behavior: when selecting i-face, restrict j,k to
        # [-h-eps, +h+eps]).
        f"NSEL,S,LOC,X,{-hx-eps:.10g},{-hx+eps:.10g}",
        *_restrict_other_axes("Y", hy, "Z", hz),
        "CM, BOUNDARY_FACE_NX, NODE",
        f"NSEL,S,LOC,X,{hx-eps:.10g},{hx+eps:.10g}",
        *_restrict_other_axes("Y", hy, "Z", hz),
        "CM, BOUNDARY_FACE_PX, NODE",
        f"NSEL,S,LOC,Y,{-hy-eps:.10g},{-hy+eps:.10g}",
        *_restrict_other_axes("X", hx, "Z", hz),
        "CM, BOUNDARY_FACE_NY, NODE",
        f"NSEL,S,LOC,Y,{hy-eps:.10g},{hy+eps:.10g}",
        *_restrict_other_axes("X", hx, "Z", hz),
        "CM, BOUNDARY_FACE_PY, NODE",
        f"NSEL,S,LOC,Z,{-hz-eps:.10g},{-hz+eps:.10g}",
        *_restrict_other_axes("X", hx, "Y", hy),
        "CM, BOUNDARY_FACE_NZ, NODE",
        f"NSEL,S,LOC,Z,{hz-eps:.10g},{hz+eps:.10g}",
        *_restrict_other_axes("X", hx, "Y", hy),
        "CM, BOUNDARY_FACE_PZ, NODE",
        "NSEL,ALL",
    )


def boundary_triplet_from_index(
    idx: int,
) -> tuple[int, int, int]:
    """Decode a boundary index (0..26) into a (-1/0/+1) triplet.

    Encoding (see setup.modal_applicator):
      code(-1)=0, code(0)=1, code(+1)=2
      idx = code(x) + 3*code(y) + 9*code(z)

    Returns:
      (x, y, z) where each entry is in {-1, 0, +1}.
    """

    if not (0 <= idx <= 26):
        raise ValueError(
            f"boundary index out of range: {idx}"
        )

    x_code = idx % 3
    y_code = (idx // 3) % 3
    z_code = (idx // 9) % 3

    def decode(code: int) -> int:
        return (-1, 0, 1)[code]

    return (decode(x_code), decode(y_code), decode(z_code))


def get_boundary_nodes(
    selectors: tuple[str, ...],
) -> ApdlCommands:
    cmds: ApdlCommands = ()

    for i, selector in enumerate(selectors):
        mode = "S" if i == 0 else "A"
        cmds += (
            f"CMSEL,{mode},{SELECTOR_TO_NAME[selector]}",
        )

    return cmds
