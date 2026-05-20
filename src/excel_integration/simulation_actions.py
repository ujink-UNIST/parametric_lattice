from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import json
import subprocess
import sys

import xlwings as xw  # type: ignore[import-not-found]

from custom_io.excel_io import (
    _apply_path_config_from_book,
    _get_simulation_cases,
    build_case_hash,
    find_table,
    get_table_data,
    selected_input_indices,
)
from custom_io.geometry_io import geometry_hash
from custom_io.mesh_io import mesh_hash
from custom_io.path_config import get_path_config


class Messenger(Protocol):
    def info(self, text: str) -> None: ...


@dataclass(frozen=True)
class ExcelMessenger:
    book: xw.Book

    def info(self, text: str) -> None:
        # MsgBox is a VBA intrinsic, not an Excel Application COM method,
        # so call it via Application.Run.
        try:
            self.book.app.api.Run("MsgBox", str(text))
            return
        except Exception:
            pass

        # Fallback: native Windows message box
        try:
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                0,
                str(text),
                "parametric_lattice",
                0,
            )
        except Exception:
            print(text)


class Explorer:
    @staticmethod
    def open_folder(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        import os

        os.startfile(str(path.resolve()))

    @staticmethod
    def select_file(path: Path) -> None:
        p = path.resolve()
        subprocess.Popen(f'explorer /select,"{p}"')


def _first_selected_index(book: xw.Book) -> int | None:
    idxs = selected_input_indices(book)
    if not idxs:
        return None
    return int(idxs[0])


def _get_case_hash_and_lattice_relpath(
    book: xw.Book,
    row_idx: int,
) -> tuple[str, str]:
    input_table = find_table(book, "t_input")
    header, body = get_table_data(input_table)
    inputs = _get_simulation_cases(header, body)

    if row_idx < 0 or row_idx >= len(inputs):
        raise IndexError(f"Row index out of range: {row_idx}")

    sim_case = inputs[row_idx]
    case_hash = build_case_hash(sim_case.to_string())
    lattice_rel = sim_case.pre_mesh_spec.geometry.cell_name
    return case_hash, lattice_rel


def _python_for_background() -> str:
    """Prefer pythonw.exe so we don't flash a console when spawning."""

    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        pythonw = exe.with_name("pythonw.exe")
        if pythonw.exists():
            return str(pythonw)
    return str(exe)


def _spawn_background(
    book: xw.Book,
    mode: str,
    selected_indices: tuple[int, ...] | None,
) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    worker = repo_root / "excel_background.py"

    # NOTE: selected_indices is serialized as JSON because xlwings may pass tuples.
    selected_json = json.dumps(selected_indices)

    cmd = [
        _python_for_background(),
        str(worker),
        "--pid",
        str(book.app.pid),
        "--book",
        str(book.fullname),
        "--mode",
        mode,
        "--selected",
        selected_json,
    ]

    # Best-effort detach on Windows.
    creationflags = 0
    creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    subprocess.Popen(
        cmd,
        cwd=str(repo_root),
        close_fds=True,
        creationflags=creationflags,
    )


def run_selected_action(book: xw.Book) -> None:
    selected_indices = selected_input_indices(book)
    _spawn_background(book, mode="run", selected_indices=selected_indices)


def run_all_action(book: xw.Book) -> None:
    _spawn_background(book, mode="run", selected_indices=None)


def run_selected_postprocess_action(book: xw.Book) -> None:
    selected_indices = selected_input_indices(book)
    _spawn_background(book, mode="postprocess", selected_indices=selected_indices)


def open_lattice_file_action(repo_root: Path, book: xw.Book) -> None:
    msg = ExcelMessenger(book)
    _apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    _, lattice_rel = _get_case_hash_and_lattice_relpath(book, row_idx)
    lattice_path = cfg.lgf_root / lattice_rel
    if not lattice_path.exists():
        msg.info(f"LGF 파일을 찾을 수 없습니다: {lattice_path}")
        return

    Explorer.select_file(lattice_path)


def open_case_artifacts_action(repo_root: Path, book: xw.Book) -> None:
    msg = ExcelMessenger(book)
    _apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    case_hash, _ = _get_case_hash_and_lattice_relpath(book, row_idx)
    artifacts_dir = cfg.artifacts_root / "case" / case_hash
    Explorer.open_folder(artifacts_dir)


def open_results_action(repo_root: Path, book: xw.Book) -> None:
    msg = ExcelMessenger(book)
    _apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    case_hash, _ = _get_case_hash_and_lattice_relpath(book, row_idx)
    results_dir = cfg.results_root / "case" / case_hash
    Explorer.open_folder(results_dir)


def open_geometry_db_action(repo_root: Path, book: xw.Book) -> None:
    msg = ExcelMessenger(book)
    _apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    input_table = find_table(book, "t_input")
    header, body = get_table_data(input_table)
    inputs = _get_simulation_cases(header, body)

    sim_case = inputs[row_idx]
    ghash = geometry_hash(sim_case)
    geometry_dir = cfg.artifacts_root / "geometry_db" / ghash
    Explorer.open_folder(geometry_dir)


def open_mesh_db_action(repo_root: Path, book: xw.Book) -> None:
    msg = ExcelMessenger(book)
    _apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    input_table = find_table(book, "t_input")
    header, body = get_table_data(input_table)
    inputs = _get_simulation_cases(header, body)

    sim_case = inputs[row_idx]
    mhash = mesh_hash(sim_case)
    mesh_dir = cfg.artifacts_root / "mesh_db" / mhash
    Explorer.open_folder(mesh_dir)
