#lattice_io.py
"""Module for lattice io functionality in src.custom_io."""

from typing import Any, cast

from dacite import from_dict, Config
from core.lattice import Lattice
from custom_io.json_io import export_json, import_json


def import_lattice(name: str) -> Lattice:
    raw = import_json(name)
    if not isinstance(raw, dict):
        raise ValueError(
            f"Lattice JSON must be a dict, got: {type(raw)!r}"
        )
    return from_dict(
        Lattice,
        cast(dict[str, Any], raw),
        config=Config(strict=True),
    )


def try_import_lattice(name: str) -> Lattice | None:
    try:
        return import_lattice(name)
    except (
        FileNotFoundError,
        ValueError,
        TypeError,
    ):
        return None


def export_lattice(name: str, lattice: Lattice) -> None:
    export_json(name, dict(lattice))
