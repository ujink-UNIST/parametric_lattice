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
    open_lattice_file_action,
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


@xw.sub
def sub_run_selected():
    run_selected_action(xw.Book.caller())


@xw.sub
def sub_run_all():
    run_all_action(xw.Book.caller())


@xw.sub
def sub_run_selected_postprocess():
    run_selected_postprocess_action(xw.Book.caller())


@xw.sub
def sub_open_lattice_file():
    open_lattice_file_action(root, xw.Book.caller())


@xw.sub
def sub_open_case_artifacts():
    open_case_artifacts_action(root, xw.Book.caller())


@xw.sub
def sub_open_results():
    open_results_action(root, xw.Book.caller())


def main() -> None:
    # Entry point when running as a script (not from Excel).
    # Note: Book.caller() only works when called from Excel.
    run_all_action(xw.Book.caller())
    _pause_to_close()
