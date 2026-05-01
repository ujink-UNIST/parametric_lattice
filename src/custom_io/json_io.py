from pathlib import Path
import json

_JSON_SUFFIX = ".json"
_JSON_ROOT = "artifacts/metadata"


def import_json(name: str):
    artifacts_root = (
        Path(__file__).resolve().parents[2] / _JSON_ROOT
    )
    relative_path = Path(name)
    if relative_path.suffix != _JSON_SUFFIX:
        relative_path = relative_path.with_suffix(
            _JSON_SUFFIX
        )
    with (artifacts_root / relative_path).open(
        "r", encoding="utf-8"
    ) as file:
        return json.load(file)


def export_json(name: str, data: object) -> None:
    artifacts_root = (
        Path(__file__).resolve().parents[2] / _JSON_ROOT
    )
    relative_path = Path(name)
    if relative_path.suffix != _JSON_SUFFIX:
        relative_path = relative_path.with_suffix(
            _JSON_SUFFIX
        )
    with (artifacts_root / relative_path).open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
