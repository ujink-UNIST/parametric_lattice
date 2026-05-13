from __future__ import annotations

from pathlib import Path
import sys

import xlwings as xw

root = Path(__file__).resolve().parent
src_dir = root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from custom_io.excel_io import (
    build_case_hash,
    find_table,
    get_table_data,
    run_selected,
    selected_input_indices,
    _get_simulation_cases,
)


def _msg(book: xw.Book, text: str) -> None:
    """Show a message to the user.

    Note: MsgBox is a VBA intrinsic, not an Excel Application COM method,
    so we need to call it via Application.Run.
    """

    try:
        # Excel/VBA MsgBox
        book.app.api.Run("MsgBox", text)
        return
    except Exception:
        pass

    try:
        # Fallback: native Windows message box
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, str(text), "parametric_lattice", 0)
    except Exception:
        print(text)


def _first_selected_index(book: xw.Book) -> int | None:
    idxs = selected_input_indices(book)
    if idxs is None or len(idxs) == 0:
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


def _open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    # Windows
    import os

    os.startfile(str(path.resolve()))


def _select_in_explorer(path: Path) -> None:
    # Windows Explorer highlight
    import subprocess

    p = path.resolve()
    subprocess.Popen(f'explorer /select,"{p}"')


@xw.sub
def sub_run_selected():
    book = xw.Book.caller()
    selected_indices = selected_input_indices(book)
    run_selected(book, selected_indices)


@xw.sub
def sub_run_all():
    run_selected(xw.Book.caller(), None)


@xw.sub
def sub_open_lattice_file():
    book = xw.Book.caller()
    row_idx = _first_selected_index(book)
    if row_idx is None:
        _msg(book, "t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    _, lattice_rel = _get_case_hash_and_lattice_relpath(book, row_idx)
    lattice_path = root / "lgf" / lattice_rel
    if not lattice_path.exists():
        _msg(book, f"LGF 파일을 찾을 수 없습니다: {lattice_path}")
        return

    _select_in_explorer(lattice_path)


@xw.sub
def sub_open_case_artifacts():
    book = xw.Book.caller()
    row_idx = _first_selected_index(book)
    if row_idx is None:
        _msg(book, "t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    case_hash, _ = _get_case_hash_and_lattice_relpath(book, row_idx)
    artifacts_dir = root / "artifacts" / "case" / case_hash
    _open_folder(artifacts_dir)


@xw.sub
def sub_open_results():
    book = xw.Book.caller()
    row_idx = _first_selected_index(book)
    if row_idx is None:
        _msg(book, "t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    case_hash, _ = _get_case_hash_and_lattice_relpath(book, row_idx)
    results_dir = root / "results" / "case" / case_hash
    _open_folder(results_dir)

def main():
    # Entry point when running as a script (not from Excel).
    run_selected(xw.Book.caller(), None)
    input()
