from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    """Runtime-configurable project paths.

    Defaults are derived from the repository root (two levels above this file).

    Notes:
      - Callers may override these at runtime (e.g. Excel integration) to point
        to external folders.
      - We intentionally do *not* expand '~' or environment variables here.
    """

    repo_root: Path
    lgf_root: Path
    artifacts_root: Path
    results_root: Path


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config(repo_root: Path | None = None) -> PathConfig:
    r = repo_root or _default_repo_root()
    return PathConfig(
        repo_root=r,
        lgf_root=r / "lgf",
        artifacts_root=r / "artifacts",
        results_root=r / "results",
    )


_ACTIVE_CONFIG: PathConfig = default_config()


def get_path_config() -> PathConfig:
    return _ACTIVE_CONFIG


def set_path_config(cfg: PathConfig) -> None:
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = cfg


def reset_path_config() -> None:
    set_path_config(default_config())
