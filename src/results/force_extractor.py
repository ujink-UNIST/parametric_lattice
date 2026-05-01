"""Reaction force extraction utilities using MAPDL FSUM."""

from __future__ import annotations

from typing import Dict, Tuple

from core.types_ import UnitCell
from io_utils import apdl_io
from results.node_selector import face_node_ids, select_nodes


def fsum_resultant(mapdl, node_ids: Tuple[int, ...]) -> Tuple[float, float, float]:
    """Compute resultant force for an explicit node set using FSUM."""
    if len(node_ids) == 0:
        raise ValueError("No nodes were selected for FSUM.")

    mapdl.esel("ALL")
    select_nodes(mapdl, node_ids)
    mapdl.fsum()
    force = (
        float(mapdl.get("FSX", "FSUM", 0, "ITEM", "FX")),
        float(mapdl.get("FSY", "FSUM", 0, "ITEM", "FY")),
        float(mapdl.get("FSZ", "FSUM", 0, "ITEM", "FZ")),
    )
    mapdl.nsel("ALL")
    return force


def read_face_force(
    mapdl,
    face: str,
    model: str,
    unit_cell: UnitCell,
) -> Tuple[float, float, float]:
    """Read the resultant reaction force for one boundary face."""
    node_ids = face_node_ids(mapdl, unit_cell, face, model)
    selected_nodes = len(node_ids)
    print(
        f"[force_extractor] face={face} model={model} "
        f"selected_nodes={selected_nodes} before FSUM"
    )
    force = fsum_resultant(mapdl, node_ids)
    print(f"[force_extractor] face={face} FSUM={force}")
    apdl_io.select_all(mapdl)
    return force


def extract_face_forces(
    mapdl,
    model: str,
    unit_cell: UnitCell,
) -> Dict[str, Tuple[float, float, float]]:
    """Extract resultant reaction forces for all six boundary faces."""
    all_faces = ("+x", "-x", "+y", "-y", "+z", "-z")
    face_forces: Dict[str, Tuple[float, float, float]] = {}
    for face in all_faces:
        face_forces[face] = read_face_force(mapdl, face, model, unit_cell)
    return face_forces
