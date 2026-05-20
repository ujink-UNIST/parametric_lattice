from __future__ import annotations

"""Excel cell spinner for long-running RunPython calls.

Excel can appear "frozen" during long Python work (e.g. MAPDL), so this module
runs a tiny *separate process* that periodically updates a cell (default:
Sheet1!A1).

A separate process is used (instead of a thread) to avoid COM apartment/thread
issues when talking to Excel.
"""

import time
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from multiprocessing import Event, Process
from pathlib import Path

_FRAMES: tuple[str, ...] = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")


def _find_open_book(app, fullname: str):
    """Best-effort: find an already-open workbook by absolute fullname."""

    target = str(Path(fullname).resolve()).lower()
    for b in app.books:
        with suppress(Exception):
            if str(Path(b.fullname).resolve()).lower() == target:
                return b
    return None


def _spinner_proc(
    stop: Event,
    fullname: str,
    sheet_name: str,
    address: str,
    frames: Sequence[str],
    period_s: float,
) -> None:
    # Import inside the subprocess.
    import xlwings as xw  # type: ignore[import-not-found]

    app = None
    with suppress(Exception):
        app = xw.apps.active
    if app is None:
        # As a last resort, start a new Excel instance.
        app = xw.App(visible=False, add_book=False)

    book = _find_open_book(app, fullname)
    if book is None:
        # Fallback: open (may open a second instance of the workbook).
        book = app.books.open(fullname)

    sht = None
    with suppress(Exception):
        sht = book.sheets[sheet_name]
    if sht is None:
        sht = book.sheets[0]

    rng = sht.range(address)

    # Hide the actual spinner glyph (;;; custom format = display nothing).
    # Row status cells can mirror A1 via formula while controlling their own styling.
    with suppress(Exception):
        rng.number_format = ";;;"

    i = 0
    n = len(frames)
    while not stop.is_set():
        rng.value = frames[i % n]
        i += 1
        with suppress(Exception):
            app.api.Run("DoEvents")
        time.sleep(period_s)


@dataclass
class CellSpinner:
    process: Process
    stop_event: Event
    fullname: str
    sheet_name: str
    address: str

    def stop(
        self,
        *,
        clear: bool = False,
        final: str | None = None,
        timeout_s: float = 2.0,
    ) -> None:
        self.stop_event.set()
        self.process.join(timeout=timeout_s)
        if self.process.is_alive():
            self.process.terminate()

        if not (clear or final is not None):
            return

        # Best-effort: write a final value from the parent process.
        with suppress(Exception):
            import xlwings as xw  # type: ignore[import-not-found]

            app = xw.apps.active
            book = _find_open_book(app, self.fullname)
            if book is None:
                return

            sht = None
            with suppress(Exception):
                sht = book.sheets[self.sheet_name]
            if sht is None:
                sht = book.sheets[0]

            v = "" if clear else final
            sht.range(self.address).value = v
            with suppress(Exception):
                app.api.Run("DoEvents")


def start_cell_spinner(
    book_fullname: str,
    *,
    sheet_name: str = "Sheet1",
    address: str = "A1",
    period_s: float = 0.15,
    frames: Sequence[str] = _FRAMES,
) -> CellSpinner:
    stop = Event()
    p = Process(
        target=_spinner_proc,
        args=(stop, book_fullname, sheet_name, address, tuple(frames), float(period_s)),
        daemon=True,
    )
    p.start()
    return CellSpinner(p, stop, book_fullname, sheet_name, address)
