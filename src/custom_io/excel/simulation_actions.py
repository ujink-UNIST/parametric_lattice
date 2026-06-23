#simulation_actions.py
"""Module for simulation actions functionality in src.custom_io.excel."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import xlwings as xw  # type: ignore[import-not-found]

from custom_io.excel.config import apply_path_config_from_book
from custom_io.case_hash import build_case_hash
from custom_io.excel.cases import get_simulation_cases
from custom_io.excel.tables import find_table, get_table_data
from custom_io.excel_io import (
    run_selected,
    run_selected_postprocess,
    selected_input_indices,
)
from custom_io.post.cache_sync import sync_post_cache_to_t_out
from custom_io.geometry_io import geometry_hash
from custom_io.mesh_io import mesh_hash
from custom_io.path_config import get_path_config


class Messenger(Protocol):
    """Protocol for user-facing Excel action messages."""

    def info(self, text: str) -> None:
        """Show an informational message.

        Parameters
        ----------
        text : str
            Message text to display.
        """
        ...


@dataclass(frozen=True)
class ExcelMessenger:
    """Display informational messages from Excel actions.

    Parameters
    ----------
    book : xw.Book
        Workbook whose Excel application should display the message.
    """

    book: xw.Book

    def info(self, text: str) -> None:
        """Show a message box or fallback console message.

        Parameters
        ----------
        text : str
            Message text to display.
        """

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

    def confirm_yes_no(self, text: str) -> bool:
        """Ask for deletion confirmation.

        Parameters
        ----------
        text : str
            Prompt text to display.

        Returns
        -------
        bool
            True when the user selects Yes.
        """

        # VBA constants: vbYesNo=4, vbExclamation=48, vbYes=6.
        try:
            result = self.book.app.api.Run("MsgBox", str(text), 4 + 48, "parametric_lattice")
            return int(result) == 6
        except Exception:
            pass

        try:
            import ctypes

            # Win32 constants: MB_YESNO=0x4, MB_ICONEXCLAMATION=0x30, IDYES=6.
            result = ctypes.windll.user32.MessageBoxW(
                0,
                str(text),
                "parametric_lattice",
                0x4 | 0x30,
            )
            return int(result) == 6
        except Exception:
            print(text)
            return False


class Explorer:
    """Small wrapper around Windows Explorer actions."""

    @staticmethod
    def open_folder(path: Path) -> None:
        """Open a folder in Windows Explorer, creating it if needed.

        Parameters
        ----------
        path : Path
            Folder path to open.
        """

        path.mkdir(parents=True, exist_ok=True)
        import os

        os.startfile(str(path.resolve()))

    @staticmethod
    def select_file(path: Path) -> None:
        """Reveal a file in Windows Explorer.

        Parameters
        ----------
        path : Path
            File path to select.
        """

        p = path.resolve()
        subprocess.Popen(f'explorer /select,"{p}"')


def _first_selected_index(book: xw.Book) -> int | None:
    idxs = selected_input_indices(book)
    if not idxs:
        return None
    return int(idxs[0])


def _get_input_case_hashes(book: xw.Book) -> set[str]:
    input_table = find_table(book, "t_input")
    header, body = get_table_data(input_table)
    inputs = get_simulation_cases(header, body)
    return {build_case_hash(sim_case.to_string()) for sim_case in inputs}


def _get_case_hash_and_lattice_relpath(
    book: xw.Book,
    row_idx: int,
) -> tuple[str, str]:
    input_table = find_table(book, "t_input")
    header, body = get_table_data(input_table)
    inputs = get_simulation_cases(header, body)

    if row_idx < 0 or row_idx >= len(inputs):
        raise IndexError(f"Row index out of range: {row_idx}")

    sim_case = inputs[row_idx]
    case_hash = build_case_hash(sim_case.to_string())
    lattice_rel = sim_case.pre_mesh_spec.geometry.cell_name
    return case_hash, lattice_rel


def _is_case_hash_dir(path: Path) -> bool:
    name = path.name.lower()
    return path.is_dir() and len(name) == 64 and all(c in "0123456789abcdef" for c in name)


def run_selected_action(book: xw.Book) -> None:
    """Run solve for the currently selected input rows.

    Parameters
    ----------
    book : xw.Book
        Calling workbook.
    """

    selected_indices = selected_input_indices(book)
    run_selected(book, selected_indices)


def run_all_action(book: xw.Book) -> None:
    """Run solve for every input row in the workbook.

    Parameters
    ----------
    book : xw.Book
        Calling workbook.
    """

    run_selected(book, None)


def run_selected_postprocess_action(book: xw.Book) -> None:
    """Run postprocessing for the currently selected input rows.

    Parameters
    ----------
    book : xw.Book
        Calling workbook.
    """

    msg = ExcelMessenger(book)
    selected_indices = selected_input_indices(book)
    if not selected_indices:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return
    run_selected_postprocess(book, selected_indices)


def sync_post_cache_action(book: xw.Book) -> None:
    """Synchronize post cache JSON files into the Excel output table.

    Parameters
    ----------
    book : xw.Book
        Calling workbook.
    """

    sync_post_cache_to_t_out(book)


def delete_orphaned_results_action(book: xw.Book) -> None:
    """Delete result case directories that are no longer present in ``t_input``.

    Parameters
    ----------
    book : xw.Book
        Calling workbook.
    """

    msg = ExcelMessenger(book)
    apply_path_config_from_book(book)
    cfg = get_path_config()

    active_hashes = _get_input_case_hashes(book)
    case_root = (cfg.results_root / "case").resolve()
    if not case_root.exists():
        msg.info(f"results/case 폴더가 없습니다: {case_root}")
        return

    orphan_dirs = sorted(
        p for p in case_root.iterdir() if _is_case_hash_dir(p) and p.name not in active_hashes
    )
    if not orphan_dirs:
        msg.info("삭제할 orphaned 해석결과가 없습니다.")
        return

    preview = "\n".join(p.name for p in orphan_dirs[:10])
    more = "" if len(orphan_dirs) <= 10 else f"\n... 외 {len(orphan_dirs) - 10}개"
    prompt = (
        f"t_input에 없는 results/case 해석결과 {len(orphan_dirs)}개를 삭제할까요?\n\n"
        f"대상 폴더:\n{preview}{more}\n\n"
        "이 작업은 되돌릴 수 없습니다."
    )
    if not msg.confirm_yes_no(prompt):
        msg.info("삭제를 취소했습니다.")
        return

    deleted = 0
    failures: list[str] = []
    for path in orphan_dirs:
        try:
            resolved = path.resolve()
            if resolved.parent != case_root:
                raise ValueError(f"Unsafe result path: {resolved}")
            shutil.rmtree(resolved)
            deleted += 1
        except Exception as e:
            failures.append(f"{path.name}: {e}")

    if failures:
        msg.info(
            f"orphaned 해석결과 {deleted}개를 삭제했습니다.\n"
            f"실패 {len(failures)}개:\n" + "\n".join(failures[:5])
        )
    else:
        msg.info(f"orphaned 해석결과 {deleted}개를 삭제했습니다.")


def open_lattice_file_action(repo_root: Path, book: xw.Book) -> None:
    """Reveal the selected case's lattice file in Windows Explorer.

    Parameters
    ----------
    repo_root : Path
        Repository root passed by the Excel entry-point module.
    book : xw.Book
        Calling workbook.
    """

    msg = ExcelMessenger(book)
    apply_path_config_from_book(book)
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
    """Open the selected case artifact directory.

    Parameters
    ----------
    repo_root : Path
        Repository root passed by the Excel entry-point module.
    book : xw.Book
        Calling workbook.
    """

    msg = ExcelMessenger(book)
    apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    case_hash, _ = _get_case_hash_and_lattice_relpath(book, row_idx)
    artifacts_dir = cfg.artifacts_root / "case" / case_hash
    Explorer.open_folder(artifacts_dir)


def open_results_action(repo_root: Path, book: xw.Book) -> None:
    """Open the selected case result directory.

    Parameters
    ----------
    repo_root : Path
        Repository root passed by the Excel entry-point module.
    book : xw.Book
        Calling workbook.
    """

    msg = ExcelMessenger(book)
    apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    case_hash, _ = _get_case_hash_and_lattice_relpath(book, row_idx)
    results_dir = cfg.results_root / "case" / case_hash
    Explorer.open_folder(results_dir)


def open_geometry_db_action(repo_root: Path, book: xw.Book) -> None:
    """Open the selected case geometry cache directory.

    Parameters
    ----------
    repo_root : Path
        Repository root passed by the Excel entry-point module.
    book : xw.Book
        Calling workbook.
    """

    msg = ExcelMessenger(book)
    apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    input_table = find_table(book, "t_input")
    header, body = get_table_data(input_table)
    inputs = get_simulation_cases(header, body)

    sim_case = inputs[row_idx]
    ghash = geometry_hash(sim_case)
    geometry_dir = cfg.artifacts_root / "geometry_db" / ghash
    Explorer.open_folder(geometry_dir)


def open_mesh_db_action(repo_root: Path, book: xw.Book) -> None:
    """Open the selected case mesh cache directory.

    Parameters
    ----------
    repo_root : Path
        Repository root passed by the Excel entry-point module.
    book : xw.Book
        Calling workbook.
    """

    msg = ExcelMessenger(book)
    apply_path_config_from_book(book)
    cfg = get_path_config()

    row_idx = _first_selected_index(book)
    if row_idx is None:
        msg.info("t_input에서 열(row)을 선택한 뒤 실행하세요.")
        return

    input_table = find_table(book, "t_input")
    header, body = get_table_data(input_table)
    inputs = get_simulation_cases(header, body)

    sim_case = inputs[row_idx]
    mhash = mesh_hash(sim_case)
    mesh_dir = cfg.artifacts_root / "mesh_db" / mhash
    Explorer.open_folder(mesh_dir)
