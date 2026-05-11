# File: c:\Users\USER\Documents\parametric_lattice\src\io\lgf_io.py
# Author: 김우진 (ujink1225@unist.ac.kr)
# Company: UNIST UCIM Lab
# Created: Thu Apr 30 2026
# Modified: Thu Apr 30 2026


from pathlib import Path

_LGF_SUFFIX = ".lgf"
_LGF_ROOT = "lgf"


def import_lgf(name: str) -> list[str]:
    cells_root = (
        Path(__file__).resolve().parents[2] / _LGF_ROOT
    )
    relative_path = Path(name)
    if relative_path.suffix != _LGF_SUFFIX:
        relative_path = relative_path.with_suffix(
            _LGF_SUFFIX
        )
    return (
        (cells_root / relative_path)
        .read_text(encoding="utf-8")
        .splitlines()
    )
