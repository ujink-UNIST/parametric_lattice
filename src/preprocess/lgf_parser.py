#lgf_parser.py
"""Parse LGF text into raw preprocessing data."""

from __future__ import annotations

from fractions import Fraction

from core.numeric.point import Point
from core.numeric.raw_edge import RawEdge
from core.numeric.raw_node import RawNode
from preprocess.errors import LatticeJsonError
from core.numeric.raw_beam import RawBeam


def parse_lgf_(
    content: list[str],
) -> tuple[list[RawNode], list[RawEdge], list[RawBeam]]:
    nodes: list[RawNode] = []
    raw_edges: list[tuple[int, int, str]] = []
    beams: list[RawBeam] = []
    has_beam_records = False

    for line_no, line in enumerate(content, start=1):
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        parts = text.split()
        tag = parts[0]

        if tag in {"n", "v"}:
            nodes.append(
                _parse_node(line_no, tag, parts, len(nodes))
            )
        elif tag == "b":
            has_beam_records = True
            beams.append(_parse_beam(line_no, parts))
        elif tag == "e":
            raw_edges.append(_parse_edge(line_no, parts))
        elif len(parts) == 1 and _can_parse_fraction(
            parts[0]
        ):
            continue
        else:
            raise LatticeJsonError(
                f"line {line_no}: record must start with n, v, e, or b"
            )

    edges = _resolve_edges(
        raw_edges, beams, has_beam_records
    )
    return nodes, edges, beams


def _parse_node(
    line_no: int, tag: str, parts: list[str], index: int
) -> RawNode:
    if len(parts) != 4:
        raise LatticeJsonError(
            f"line {line_no}: node record must be: {tag} x y z"
        )
    return RawNode(
        index,
        Point(
            _read_unit_fraction(
                line_no, "node.x", parts[1]
            ),
            _read_unit_fraction(
                line_no, "node.y", parts[2]
            ),
            _read_unit_fraction(
                line_no, "node.z", parts[3]
            ),
        ),
    )


def _parse_beam(line_no: int, parts: list[str]) -> RawBeam:
    if len(parts) != 3:
        raise LatticeJsonError(
            f"line {line_no}: beam record must be: b section_type radius"
        )
    return RawBeam(
        parts[1],
        _read_unit_fraction(
            line_no, "beam.radius", parts[2]
        ),
    )


def _parse_edge(
    line_no: int, parts: list[str]
) -> tuple[int, int, str]:
    if len(parts) != 4:
        raise LatticeJsonError(
            f"line {line_no}: edge record must be: e node0 node1 beam"
        )
    return (
        _read_nonnegative_int(
            line_no, "edge.node0Id", parts[1]
        ),
        _read_nonnegative_int(
            line_no, "edge.node1Id", parts[2]
        ),
        parts[3],
    )


def _resolve_edges(
    raw_edges: list[tuple[int, int, str]],
    beams: list[RawBeam],
    has_beam_records: bool,
) -> list[RawEdge]:
    if has_beam_records:
        return [
            RawEdge(
                n0,
                n1,
                _read_nonnegative_int(
                    0, "edge.beamId", beam
                ),
            )
            for n0, n1, beam in raw_edges
        ]
    beam_ids: dict[Fraction, int] = {}
    for _, _, beam in raw_edges:
        radius = (
            _read_positive_fraction(
                0, "edge.diameter", beam
            )
            / 2
        )
        if radius not in beam_ids:
            beam_ids[radius] = len(beams)
            beams.append(RawBeam("circular", radius))
    return [
        RawEdge(
            n0,
            n1,
            beam_ids[
                _read_positive_fraction(
                    0, "edge.diameter", beam
                )
                / 2
            ],
        )
        for n0, n1, beam in raw_edges
    ]


def _read_unit_fraction(
    line_no: int, name: str, value: str
) -> Fraction:
    parsed = _read_fraction(line_no, name, value)
    if Fraction(0) <= parsed <= Fraction(1):
        return parsed
    raise LatticeJsonError(
        f"line {line_no}: {name} must be in range [0, 1], got {value!r}"
    )


def _read_positive_fraction(
    line_no: int, name: str, value: str
) -> Fraction:
    parsed = _read_fraction(line_no, name, value)
    if parsed > 0:
        return parsed
    raise LatticeJsonError(
        f"line {line_no}: {name} must be greater than 0, got {value!r}"
    )


def _read_fraction(
    line_no: int, name: str, value: str
) -> Fraction:
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as exc:
        raise LatticeJsonError(
            f"line {line_no}: {name} must be a rational number, got {value!r}"
        ) from exc


def _can_parse_fraction(value: str) -> bool:
    try:
        Fraction(value)
        return True
    except (ValueError, ZeroDivisionError):
        return False


def _read_nonnegative_int(
    line_no: int, name: str, value: str
) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise LatticeJsonError(
            f"line {line_no}: {name} must be a non-negative integer"
        ) from exc
    if parsed < 0:
        raise LatticeJsonError(
            f"line {line_no}: {name} must be a non-negative integer"
        )
    return parsed
