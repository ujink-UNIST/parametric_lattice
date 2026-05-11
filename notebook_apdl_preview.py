from __future__ import annotations

import importlib
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
src_dir = root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from apdl_preview import (  # noqa: E402
    SimCaseInput,
    build_sim_case,
    generate_apdl_commands,
    generate_apdl_text,
    load_unit_cell,
)


def reload_project_modules():
    project_dirs = (root, src_dir)
    module_names: list[str] = []

    for name, module in list(sys.modules.items()):
        module_file = getattr(module, "__file__", None)
        if module_file is None:
            continue
        try:
            resolved = Path(module_file).resolve()
        except OSError:
            continue
        if any(
            parent == resolved.parent or parent in resolved.parents
            for parent in project_dirs
        ):
            module_names.append(name)

    for name in sorted(
        set(module_names) - {__name__},
        key=lambda item: item.count("."),
        reverse=True,
    ):
        importlib.reload(sys.modules[name])

    return importlib.reload(sys.modules[__name__])

__all__ = [
    "SimCaseInput",
    "build_sim_case",
    "generate_apdl_commands",
    "generate_apdl_text",
    "load_unit_cell",
    "reload_project_modules",
]
