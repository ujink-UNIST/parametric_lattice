#config.py
"""Module for config functionality in src.custom_io.excel."""

from __future__ import annotations

from pathlib import Path

import xlwings as xw  # type: ignore[import-not-found]

from custom_io.excel.tables import find_table, get_table_data
from custom_io.path_config import PathConfig, default_config, set_path_config


def apply_path_config_from_book(book: xw.Book, *, config_table: str = "t_config") -> None:
    """Apply runtime path configuration from an Excel workbook.

    Parameters
    ----------
    book : xw.Book
        Workbook that may contain the configuration table.
    config_table : str, optional
        Excel ListObject name to read. The first data row is used.

    Notes
    -----
    Relative paths are resolved against the workbook directory. Missing tables,
    missing rows, and empty cells fall back to repository defaults.
    """

    repo_root = Path(__file__).resolve().parents[3]
    cfg = default_config(repo_root)

    try:
        workbook_path = Path(str(book.fullname))
        relative_base = workbook_path.parent if str(book.fullname).strip() else cfg.repo_root
    except Exception:
        relative_base = cfg.repo_root

    try:
        table = find_table(book, config_table)
    except KeyError:
        set_path_config(cfg)
        return

    header, body = get_table_data(table)
    if not body:
        set_path_config(cfg)
        return

    row0 = body[0]
    col_index = {str(h).strip().lower(): i for i, h in enumerate(header)}

    def read_path(col: str) -> Path | None:
        i = col_index.get(col)
        if i is None or i >= len(row0):
            return None
        v = row0[i]
        if v is None:
            return None
        s = str(v).strip()
        if not s:
            return None
        p = Path(s)
        if p.is_absolute():
            return p
        return (relative_base / p).resolve()

    lgf_root = read_path("lgf") or cfg.lgf_root
    artifacts_root = read_path("artifacts") or cfg.artifacts_root
    results_root = read_path("results") or cfg.results_root
    compute_policy = _read_compute_policy(row0=row0, col_index=col_index)
    nproc = _read_optional_positive_int(row0=row0, col_index=col_index, column="n_proc")
    ansys_batch_size = _read_ansys_batch_size(row0=row0, col_index=col_index, default=cfg.ansys_batch_size)

    set_path_config(
        PathConfig(
            repo_root=cfg.repo_root,
            lgf_root=lgf_root,
            artifacts_root=artifacts_root,
            results_root=results_root,
            compute_policy=compute_policy,
            nproc=nproc,
            ansys_batch_size=ansys_batch_size,
        )
    )


def _read_compute_policy(*, row0: tuple[object, ...], col_index: dict[str, int]) -> str:
    """Read and validate the solve cache policy from ``t_config``.

    Parameters
    ----------
    row0 : tuple[object, ...]
        First data row of the config table.
    col_index : dict[str, int]
        Lower-case column name to zero-based index mapping.

    Returns
    -------
    str
        One of ``"cache"``, ``"recompute"``, or ``"smart"``.
    """

    compute_policy = "smart"
    i_pol = col_index.get("compute_policy")
    if i_pol is not None and i_pol < len(row0):
        v = row0[i_pol]
        if v is not None and str(v).strip():
            compute_policy = str(v).strip().lower()

    if compute_policy not in {"cache", "recompute", "smart"}:
        raise ValueError(
            f"t_config.compute_policy must be one of cache/recompute/smart (got {compute_policy!r})"
        )
    return compute_policy


def _read_optional_positive_int(
    *,
    row0: tuple[object, ...],
    col_index: dict[str, int],
    column: str,
) -> int | None:
    """Read an optional positive integer config value.

    Parameters
    ----------
    row0 : tuple[object, ...]
        First data row of the config table.
    col_index : dict[str, int]
        Lower-case column name to zero-based index mapping.
    column : str
        Column name to read.

    Returns
    -------
    int or None
        Parsed positive integer, or ``None`` when the value is absent.
    """

    i = col_index.get(column)
    if i is None or i >= len(row0):
        return None
    v = row0[i]
    if v is None or not str(v).strip():
        return None
    try:
        value = int(float(v))
    except Exception as e:
        raise ValueError(f"t_config.{column} must be an int (got {v!r})") from e
    if value <= 0:
        raise ValueError(f"t_config.{column} must be positive (got {value})")
    return value


def _read_ansys_batch_size(
    *,
    row0: tuple[object, ...],
    col_index: dict[str, int],
    default: int,
) -> int:
    """Read the MAPDL restart interval from Excel configuration.

    Parameters
    ----------
    row0 : tuple[object, ...]
        First data row of the config table.
    col_index : dict[str, int]
        Lower-case column name to zero-based index mapping.
    default : int
        Value to use when no configured value is present.

    Returns
    -------
    int
        Number of cases per MAPDL session. ``0`` means all cases in one
        session.
    """

    i = col_index.get("ansys_batch_size")
    if i is None:
        i = col_index.get("mapdl_batch_size")
    if i is None:
        i = col_index.get("ansys_restart_every")
    if i is None or i >= len(row0):
        return int(default)

    v = row0[i]
    if v is None or not str(v).strip():
        return int(default)
    try:
        value = int(float(v))
    except Exception as e:
        raise ValueError(f"t_config.ansys_batch_size must be an int (got {v!r})") from e
    if value < 0:
        raise ValueError(f"t_config.ansys_batch_size must be 0 or positive (got {value})")
    return value
