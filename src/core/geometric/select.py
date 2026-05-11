from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.geometric.transform import transform_coords
from core.parameters.geometry_params import GeometryParams
from core.unit_cell import UnitCell

SELECTOR_TO_NAME: dict[str, str] = {
    "+x": "PERIODIC_NODES_PX",
    "-x": "PERIODIC_NODES_NX",
    "+y": "PERIODIC_NODES_PY",
    "-y": "PERIODIC_NODES_NY",
    "+z": "PERIODIC_NODES_PZ",
    "-z": "PERIODIC_NODES_NZ",
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


def get_boundary_endpoint_nodes(
    unit_cell: UnitCell,
    geometry_params: GeometryParams,
) -> ApdlCommands:
    size: Vector3 = geometry_params.size
    eps = min(size[0], size[1], size[2]) * 1e-6

    boundary_node_ids = [
        node_id
        for node_id, boundary in enumerate(
            unit_cell.node_boundaries, start=1
        )
        if any(value != 0 for value in boundary)
    ]

    if not boundary_node_ids:
        return ()

    cmds: list[str] = []
    temp_components: list[str] = []

    for node_id in boundary_node_ids:
        node = transform_coords(
            unit_cell.nodes[node_id - 1], size
        )
        temp_name = f"_BOUNDARY_ENDPOINT_{node_id}"
        temp_components.append(temp_name)
        cmds.extend(
            (
                f"NSEL,S,LOC,X,{node[0]-eps:.10g},{node[0]+eps:.10g}",
                f"NSEL,R,LOC,Y,{node[1]-eps:.10g},{node[1]+eps:.10g}",
                f"NSEL,R,LOC,Z,{node[2]-eps:.10g},{node[2]+eps:.10g}",
                f"CM,{temp_name},NODE",
            )
        )

    for i, temp_name in enumerate(temp_components):
        mode = "S" if i == 0 else "A"
        cmds.append(f"CMSEL,{mode},{temp_name}")

    cmds.extend(
        (
            "CM,BOUNDARY_ENDPOINT_NODES,NODE",
            "NSEL,ALL",
        )
    )
    return tuple(cmds)


def get_all_periodic_nodes(
    geometry_params: GeometryParams,
) -> ApdlCommands:
    size: Vector3 = geometry_params.size
    half_size = size / 2

    eps = min(size[0], size[1], size[2]) * 1e-6

    return (
        "NSEL,NONE",
        f"NSEL,S,LOC,X,{-half_size[0]-eps:.10g},{-half_size[0]+eps:.10g}",
        "CM, PERIODIC_NODES_NX, NODE",
        f"NSEL,S,LOC,X,{half_size[0]-eps:.10g},{half_size[0]+eps:.10g}",
        "CM, PERIODIC_NODES_PX, NODE",
        f"NSEL,S,LOC,Y,{-half_size[1]-eps:.10g},{-half_size[1]+eps:.10g}",
        "CM, PERIODIC_NODES_NY, NODE",
        f"NSEL,S,LOC,Y,{half_size[1]-eps:.10g},{half_size[1]+eps:.10g}",
        "CM, PERIODIC_NODES_PY, NODE",
        f"NSEL,S,LOC,Z,{-half_size[2]-eps:.10g},{-half_size[2]+eps:.10g}",
        "CM, PERIODIC_NODES_NZ, NODE",
        f"NSEL,S,LOC,Z,{half_size[2]-eps:.10g},{half_size[2]+eps:.10g}",
        "CM, PERIODIC_NODES_PZ, NODE",
        "NSEL,ALL",
    )


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
