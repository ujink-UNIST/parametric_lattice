from __future__ import annotations

"""Mesh-derived boundary touch area for SOLID meshes.

We compute, for each axis A in {X,Y,Z}, the average exterior surface area on the
+A and -A boundary planes:
  A_X = (A_PX + A_NX) / 2, etc.

This is intended for solid meshes (e.g. SOLID187 tetra). The implementation is
based on reading the exported mesh archive (mesh.cdb) from artifacts/mesh_db.

Assumptions (current implementation):
- Element type is tetrahedral (SOLID187), and we approximate face area using the
  4 corner nodes (ignore midside nodes).
- mesh.cdb was written using CDWRITE,GEOM,...,BLOCKED.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


_NUM_RE = re.compile(r"[-+]?\d*\.\d+(?:[Ee][-+]?\d+)?|[-+]?\d+(?:[Ee][-+]?\d+)?")


@dataclass(frozen=True, slots=True)
class TouchAreaResult:
    ax: float
    ay: float
    az: float


def _nums(line: str) -> list[str]:
    return _NUM_RE.findall(line)


def _parse_cdb_nodes(path: Path) -> dict[int, np.ndarray]:
    nodes: dict[int, np.ndarray] = {}
    in_nblock = False

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        u = line.upper()
        if u.startswith("NBLOCK"):
            in_nblock = True
            continue
        if in_nblock:
            # NBLOCK ends with a line containing -1
            if line.startswith("-1"):
                in_nblock = False
                continue
            if line.startswith("("):
                # format line
                continue
            vals = _nums(line)
            if len(vals) < 4:
                continue
            # Heuristic: node id is the first integer-like token.
            nid = int(float(vals[0]))
            # Coordinates are the last 3 tokens.
            x, y, z = (float(vals[-3]), float(vals[-2]), float(vals[-1]))
            nodes[nid] = np.array([x, y, z], dtype=float)

    return nodes


def _parse_cdb_tet_elements(path: Path) -> list[tuple[int, int, int, int]]:
    """Return list of tet corner node tuples (n1,n2,n3,n4).

    EBLOCK records are fixed-length integer records (e.g. EBLOCK,19,...) but are
    commonly wrapped across multiple lines. We therefore must reconstruct each
    element record by chunking the EBLOCK integer stream.

    This implementation targets meshes written by ``CDWRITE,GEOM,...,BLOCKED``.

    For SOLID187 (tet10) with EBLOCK,19, the last 10 integers of each record are
    typically the node connectivity (10 nodes). Corner nodes are the first 4 of
    those 10.
    """

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()

    in_eblock = False
    nint: int | None = None
    ints: list[int] = []

    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        u = line.upper()

        if u.startswith("EBLOCK"):
            in_eblock = True
            # EBLOCK,<nint>,...
            try:
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 2:
                    nint = int(parts[1])
            except Exception:
                nint = None
            continue

        if not in_eblock:
            continue

        if line.startswith("-1"):
            break

        if line.startswith("("):
            continue

        for tok in _nums(line):
            try:
                ints.append(int(float(tok)))
            except Exception:
                continue

    if not ints:
        return []

    if nint is None or nint <= 0:
        nint = 19

    elems: list[tuple[int, int, int, int]] = []
    nrec = len(ints) // nint

    for r in range(nrec):
        rec = ints[r * nint : (r + 1) * nint]
        if len(rec) != nint:
            continue

        # Connectivity is at the end.
        conn = rec[-10:] if len(rec) >= 10 else rec
        if len(conn) < 4:
            continue

        n1, n2, n3, n4 = conn[0], conn[1], conn[2], conn[3]
        if n1 > 0 and n2 > 0 and n3 > 0 and n4 > 0:
            elems.append((n1, n2, n3, n4))

    return elems


def _tri_area(p1: np.ndarray, p2: np.ndarray, p3: np.ndarray) -> float:
    return 0.5 * float(np.linalg.norm(np.cross(p2 - p1, p3 - p1)))


def _faces_of_tet(n1: int, n2: int, n3: int, n4: int) -> tuple[tuple[int, int, int], ...]:
    return (
        (n1, n2, n3),
        (n1, n2, n4),
        (n1, n3, n4),
        (n2, n3, n4),
    )


def compute_total_volume_from_cdb(*, cdb_path: Path) -> float:
    """Compute total solid volume by summing tetra corner volumes."""

    nodes = _parse_cdb_nodes(cdb_path)
    elems = _parse_cdb_tet_elements(cdb_path)

    vol = 0.0
    for (n1, n2, n3, n4) in elems:
        try:
            p1, p2, p3, p4 = (nodes[n1], nodes[n2], nodes[n3], nodes[n4])
        except KeyError:
            continue
        v = abs(float(np.dot(p2 - p1, np.cross(p3 - p1, p4 - p1)))) / 6.0
        vol += v

    return float(vol)


def compute_boundary_touch_area_from_cdb(
    *,
    cdb_path: Path,
    size_xyz: Iterable[float],
    tol: float,
) -> TouchAreaResult:
    """Compute average touch area on ±X, ±Y, ±Z boundary planes."""

    nodes = _parse_cdb_nodes(cdb_path)
    elems = _parse_cdb_tet_elements(cdb_path)

    sx, sy, sz = (float(x) for x in size_xyz)
    x_p, x_n = sx / 2.0, -sx / 2.0
    y_p, y_n = sy / 2.0, -sy / 2.0
    z_p, z_n = sz / 2.0, -sz / 2.0

    # Count faces to find exterior ones.
    face_count: dict[tuple[int, int, int], int] = {}
    face_nodes: dict[tuple[int, int, int], tuple[int, int, int]] = {}

    for (n1, n2, n3, n4) in elems:
        for f in _faces_of_tet(n1, n2, n3, n4):
            key = tuple(sorted(f))
            face_count[key] = face_count.get(key, 0) + 1
            face_nodes[key] = f

    a_px = a_nx = 0.0
    a_py = a_ny = 0.0
    a_pz = a_nz = 0.0

    for key, cnt in face_count.items():
        if cnt != 1:
            continue
        f = face_nodes[key]
        try:
            p1, p2, p3 = (nodes[f[0]], nodes[f[1]], nodes[f[2]])
        except KeyError:
            continue

        area = _tri_area(p1, p2, p3)

        # Classify by boundary plane.
        xs = (p1[0], p2[0], p3[0])
        ys = (p1[1], p2[1], p3[1])
        zs = (p1[2], p2[2], p3[2])

        if all(abs(x - x_p) <= tol for x in xs):
            a_px += area
        elif all(abs(x - x_n) <= tol for x in xs):
            a_nx += area
        elif all(abs(y - y_p) <= tol for y in ys):
            a_py += area
        elif all(abs(y - y_n) <= tol for y in ys):
            a_ny += area
        elif all(abs(z - z_p) <= tol for z in zs):
            a_pz += area
        elif all(abs(z - z_n) <= tol for z in zs):
            a_nz += area

    return TouchAreaResult(
        ax=0.5 * (a_px + a_nx),
        ay=0.5 * (a_py + a_ny),
        az=0.5 * (a_pz + a_nz),
    )
