#lattice.py
"""Module for lattice functionality in src.core."""

from fractions import Fraction
import math
from typing import List, Sequence, Tuple, TypedDict

from core.numeric.direction import (
    FORWARD,
    RIGHT,
    UP,
    Direction,
    absolute,
    parallel,
)
from core.numeric.point import Point, get_direction


class Node(TypedDict):
    id: int
    position: list[float]
    boundary: list[int]


class BeamType(TypedDict):
    id: int
    section_type: str
    radius_ratio: float


class Edge(TypedDict):
    id: int
    node0_id: int
    node1_id: int
    normal: list[float]
    beam_type_id: int
    section_ratio: float
    extend_id: int


class Lattice(TypedDict):
    nodes: list[Node]
    beam_types: list[BeamType]
    edges: list[Edge]


def sorted_to_lattice(
    sorted_nodes: List[Point],
    sorted_beams: List[Tuple[str, Fraction]],
    sorted_edges: List[Tuple[int, ...]],
) -> Lattice:
    nodes: list[Node] = [
        {
            "id": index,
            "position": [
                float(point.x),
                float(point.y),
                float(point.z),
            ],
            "boundary": [
                _get_boundary_value(point.x),
                _get_boundary_value(point.y),
                _get_boundary_value(point.z),
            ],
        }
        for index, point in enumerate(sorted_nodes)
    ]
    lattice: Lattice = {
        "nodes": nodes,
        "beam_types": [
            {
                "id": index,
                "section_type": beam[0],
                "radius_ratio": float(beam[1]),
            }
            for index, beam in enumerate(sorted_beams)
        ],
        "edges": [
            {
                "id": index,
                "node0_id": edge[0],
                "node1_id": edge[1],
                "beam_type_id": edge[2],
                "normal": _get_normal(
                    sorted_nodes[edge[0]],
                    sorted_nodes[edge[1]],
                ),
                "section_ratio": _get_section_ratio(
                    nodes[edge[0]]["boundary"],
                    nodes[edge[1]]["boundary"],
                ),
                "extend_id": _get_extend_id(
                    index, edge, sorted_nodes, sorted_edges
                ),
            }
            for index, edge in enumerate(sorted_edges)
        ],
    }

    return lattice


def _get_boundary_value(value: Fraction) -> int:
    if value == 0:
        return -1
    if value == 1:
        return 1
    return 0


def _get_normal(left: Point, right: Point) -> List[float]:
    dv: Direction = get_direction(left, right)
    da = absolute(dv)

    if da.x <= da.y and da.x <= da.z:
        ref = RIGHT
    elif da.y <= da.x and da.y <= da.z:
        ref = UP
    else:
        ref = FORWARD

    nx: Fraction = dv.y * ref.z - dv.z * ref.y
    ny: Fraction = dv.z * ref.x - dv.x * ref.z
    nz: Fraction = dv.x * ref.y - dv.y * ref.x

    norm2 = nx * nx + ny * ny + nz * nz

    if norm2 == 0:
        return [0, 0, 1]

    norm = math.sqrt(float(norm2))

    return [
        float(nx) / norm,
        float(ny) / norm,
        float(nz) / norm,
    ]


def _get_section_ratio(
    left_boundary: Sequence[int],
    right_boundary: Sequence[int],
) -> float:
    matches = sum(
        1
        for left, right in zip(
            left_boundary, right_boundary
        )
        if left != 0 and left == right
    )
    if matches == 0:
        return 1.0
    if matches == 1:
        return 0.5
    return 0.25


def _get_extend_id(
    index: int,
    edge_data: Tuple[int, ...],
    sorted_nodes: List[Point],
    sorted_edges: List[Tuple[int, ...]],
) -> int:
    node0_id = edge_data[0]
    node1_id = edge_data[1]

    node0: Point = sorted_nodes[node0_id]
    node1: Point = sorted_nodes[node1_id]
    dir0: Direction = get_direction(node0, node1)

    for idx, edge in enumerate(sorted_edges):
        if (
            edge[0] == node0_id
            or edge[0] == node1_id
            or edge[1] == node0_id
            or edge[1] == node1_id
        ):
            dir1: Direction = get_direction(
                sorted_nodes[edge[0]],
                sorted_nodes[edge[1]],
            )
            if parallel(dir0, dir1) and index < idx:
                return idx
    return -1
