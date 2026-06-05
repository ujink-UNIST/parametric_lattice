from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathConfig:
    """Runtime-configurable project paths and compute policy.

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

    # Solve compute policy (used by excel integration):
    #   - smart: reuse caches when valid; otherwise compute; skip if already solved
    #   - cache: reuse caches when valid; otherwise skip
    #   - recompute: ignore caches and compute everything
    compute_policy: str = "smart"

    # MAPDL nproc (optional). If None, let MAPDL decide default.
    nproc: int | None = None

    # Number of solve cases to run per MAPDL launch.
    #   - 1: restart MAPDL every case (previous behavior)
    #   - 0: run all selected cases in one MAPDL session
    #   - N: restart MAPDL every N cases
    ansys_batch_size: int = 1


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_config(repo_root: Path | None = None) -> PathConfig:
    r = repo_root or _default_repo_root()
    return PathConfig(
        repo_root=r,
        lgf_root=r / "lgf",
        artifacts_root=r / "artifacts",
        results_root=r / "results",
        compute_policy="smart",
        nproc=None,
    )


_ACTIVE_CONFIG: PathConfig = default_config()


def get_path_config() -> PathConfig:
    return _ACTIVE_CONFIG


def set_path_config(cfg: PathConfig) -> None:
    global _ACTIVE_CONFIG
    _ACTIVE_CONFIG = cfg


def reset_path_config() -> None:
    set_path_config(default_config())
