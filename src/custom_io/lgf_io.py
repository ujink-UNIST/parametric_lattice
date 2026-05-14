# lgf_io.py

from __future__ import annotations

from pathlib import Path

from custom_io.path_safety import safe_path_under

_LGF_ROOT = "lgf"
_ALLOWED_SUFFIXES = (".lgf", ".txt")

_TXT_DEFAULT_BEAM_LINE = "b CSolid 0.1"


def _import_txt_as_lgf_lines(text: str) -> list[str]:
    """Convert a legacy *.txt lattice file into LGF-like records.

    Expected sections:
      - "Nodal positions:" followed by lines of "x y z" (unit cell coords)
      - "Bar connectivities:" followed by lines of "i j" (1-based indices)

    Output is a list of LGF records using:
      - v x y z
      - e n0 n1 0
      - b CSolid 0.1
    """

    lines = text.splitlines()
    mode: str | None = None
    out: list[str] = []

    for raw in lines:
        s = raw.strip()
        if not s:
            continue

        header = s.lower()
        if header.startswith("nodal positions"):
            mode = "nodes"
            continue
        if header.startswith("bar connectivities"):
            mode = "edges"
            continue

        if mode == "nodes":
            parts = s.split()
            if len(parts) != 3:
                # ignore unexpected lines
                continue
            x, y, z = parts
            out.append(f"v {x} {y} {z}")
            continue

        if mode == "edges":
            parts = s.split()
            if len(parts) != 2:
                continue
            i, j = int(parts[0]), int(parts[1])
            # txt is 1-based; lgf is 0-based
            out.append(f"e {i-1} {j-1} 0")
            continue

    out.append(_TXT_DEFAULT_BEAM_LINE)
    return out


def resolve_cell_name(name: str) -> str:
    """Resolve a user-provided cell name to an existing file under ``lgf/``.

    Returns a *normalized relative path string* including the extension.

    Examples:
      - "bc" -> "bc.lgf" (if exists) else "bc.txt"
      - "custom/bc" -> "custom/bc.lgf" ...
    """

    cells_root = Path(__file__).resolve().parents[2] / _LGF_ROOT

    rel = Path(name)
    if rel.suffix in _ALLOWED_SUFFIXES:
        candidates = [rel]
    else:
        candidates = [rel.with_suffix(s) for s in _ALLOWED_SUFFIXES]

    tried: list[Path] = []
    for cand in candidates:
        p = safe_path_under(cells_root, cand.as_posix(), cand.suffix)
        tried.append(p)
        if p.exists():
            # Return path relative to lgf root with forward slashes for stability.
            return p.relative_to(cells_root).as_posix()

    raise FileNotFoundError(
        f"Could not find cell file for {name!r}. Tried: {', '.join(str(p) for p in tried)}"
    )


def import_lgf(name: str) -> list[str]:
    """Import a unit-cell definition file from the repo's ``lgf/`` folder.

    Supported inputs:
      - "bc"      -> tries "bc.lgf" then "bc.txt"
      - "bc.lgf"  -> reads "bc.lgf"
      - "bc.txt"  -> reads "bc.txt" (converted to LGF records on the fly)
      - "custom/bc", "custom/bc.txt", ... under lgf/

    Note:
      The file is resolved/validated using :func:`resolve_cell_name`.
    """

    cells_root = Path(__file__).resolve().parents[2] / _LGF_ROOT
    rel_name = resolve_cell_name(name)
    suffix = Path(rel_name).suffix
    path = safe_path_under(cells_root, rel_name, suffix)

    text = path.read_text(encoding="utf-8")
    if suffix == ".txt":
        return _import_txt_as_lgf_lines(text)

    return text.splitlines()
