from __future__ import annotations

import sys
from pathlib import Path

import xlwings as xw

# Bootstrap so Excel can run this module from the repo root.
root = Path(__file__).resolve().parent
src_dir = root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from excel_integration.simulation_actions import (
    open_case_artifacts_action,
    open_geometry_db_action,
    open_lattice_file_action,
    open_mesh_db_action,
    open_results_action,
    run_all_action,
    run_selected_action,
    run_selected_postprocess_action,
)


def _pause_to_close() -> None:
    """Pause when running from a console so the window doesn't close."""

    try:
        input("\nPress Enter to close...")
    except (EOFError, KeyboardInterrupt):
        pass


from excel_integration.simulation_actions import (
    open_case_artifacts_action,
    open_geometry_db_action,
    open_lattice_file_action,
    open_mesh_db_action,
    open_results_action,
    run_all_action,
    run_selected_action,
    run_selected_postprocess_action,
)


def sub_run_selected() -> None:
    book = xw.Book.caller()
    run_selected_action(book)


def sub_run_all() -> None:
    book = xw.Book.caller()
    run_all_action(book)


def sub_run_selected_postprocess() -> None:
    book = xw.Book.caller()
    run_selected_postprocess_action(book)


def sub_open_lattice_file() -> None:
    book = xw.Book.caller()
    open_lattice_file_action(root, book)


def sub_open_case_artifacts() -> None:
    book = xw.Book.caller()
    open_case_artifacts_action(root, book)


def sub_open_geometry_artifacts() -> None:
    book = xw.Book.caller()
    open_geometry_db_action(root, book)


def sub_open_mesh_artifacts() -> None:
    book = xw.Book.caller()
    open_mesh_db_action(root, book)


def sub_open_results() -> None:
    book = xw.Book.caller()
    open_results_action(root, book)


def main() -> None:
    run_all_action(xw.Book.caller())
    _pause_to_close()
