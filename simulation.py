# ruff: noqa: E402
from __future__ import annotations

import sys
from contextlib import suppress
from pathlib import Path

import xlwings as xw

# Bootstrap so Excel can run this module from the repo root.
root = Path(__file__).resolve().parent
src_dir = root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from excel_integration.excel_spinner import start_cell_spinner
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

    with suppress(EOFError, KeyboardInterrupt):
        input("\nPress Enter to close...")


def _run_with_spinner(book: xw.Book, fn) -> None:
    """Animate a simple spinner in Sheet1!A1 while `fn()` runs."""

    spinner = None
    fullname = getattr(book, "fullname", None)
    if isinstance(fullname, str) and fullname.strip():
        spinner = start_cell_spinner(fullname, sheet_name="Sheet1", address="A1")

    try:
        fn()
    finally:
        if spinner is not None:
            spinner.stop(clear=True)


def sub_run_selected() -> None:
    book = xw.Book.caller()
    _run_with_spinner(book, lambda: run_selected_action(book))


def sub_run_all() -> None:
    book = xw.Book.caller()
    _run_with_spinner(book, lambda: run_all_action(book))


def sub_run_selected_postprocess() -> None:
    book = xw.Book.caller()
    _run_with_spinner(book, lambda: run_selected_postprocess_action(book))


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
    book = xw.Book.caller()

    def _work() -> None:
        run_all_action(book)
        _pause_to_close()

    _run_with_spinner(book, _work)
