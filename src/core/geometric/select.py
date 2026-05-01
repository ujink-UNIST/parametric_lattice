from core.apdl_commands import ApdlCommands
from core.floats.vector import Vector3
from core.parameters.geometry_params import GeometryParams

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
