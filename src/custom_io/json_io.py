#json_io.py
"""Module for json io functionality in src.custom_io."""

from __future__ import annotations

import json
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any

import numpy as np

from custom_io.path_config import get_path_config
from custom_io.path_safety import safe_path_under

_JSON_SUFFIX = ".json"
_JSON_ROOT = "metadata"


def _to_jsonable(obj: Any) -> Any:
    """Convert common project objects into JSON-serializable structures.

    Implementation note:
    We intentionally avoid recursive self-references inside comprehensions
    (which can produce confusing NameError traces in some interactive reload
    scenarios) by delegating recursion to a nested helper.
    """

    def conv(x: Any) -> Any:
        if is_dataclass(x):
            return {k: conv(v) for k, v in vars(x).items()}
        if isinstance(x, dict):
            return {str(k): conv(v) for k, v in x.items()}
        if isinstance(x, (list, tuple)):
            return [conv(v) for v in x]
        if isinstance(x, Path):
            return str(x)
        if isinstance(x, np.ndarray):
            return x.tolist()
        return x

    return conv(obj)


def import_json(name: str):
    artifacts_root = get_path_config().artifacts_root / _JSON_ROOT
    path = safe_path_under(artifacts_root, name, _JSON_SUFFIX)
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def export_json(name: str, data: object) -> None:
    artifacts_root = get_path_config().artifacts_root / _JSON_ROOT
    path = safe_path_under(artifacts_root, name, _JSON_SUFFIX)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            _to_jsonable(data),
            file,
            ensure_ascii=False,
            indent=2,
        )
