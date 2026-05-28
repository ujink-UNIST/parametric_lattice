from __future__ import annotations

"""Excel cell spinner for long-running RunPython calls.

Excel can appear "frozen" during long Python work (e.g. MAPDL), so this module
runs a tiny *separate process* that periodically updates one or more cells
(default: Input!A1).

A separate process is used (instead of a thread) to avoid COM apartment/thread
issues when talking to Excel.
"""

import time
from collections.abc import Sequence
from typing import TypeAlias
from contextlib import suppress
from dataclasses import dataclass
from multiprocessing import Event, Process
from pathlib import Path

_FRAMES: tuple[str, ...] = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")

# Spinner update tempo.
# 100 bpm = 100 updates/minute => 0.6 s per frame.
_DEFAULT_BPM: float = 100.0
_DEFAULT_PERIOD_S: float = 60.0 / _DEFAULT_BPM

SpinnerTarget: TypeAlias = tuple[str, str]


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
    targets: Sequence[SpinnerTarget],
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
        # Do not open the workbook from the spinner process. Opening can create
        # a second window / activate the wrong sheet (often Sheet1). If the
        # already-open workbook cannot be found, silently disable the spinner.
        return

    ranges = []
    for sheet_name, address in targets:
        sht = None
        with suppress(Exception):
            sht = book.sheets[sheet_name]
        if sht is None:
            continue
        with suppress(Exception):
            rng = sht.range(address)
            rng.api.Font.Bold = False
            ranges.append(rng)

    if not ranges:
        return

    i = 0
    n = len(frames)
    while not stop.is_set():
        v = frames[i % n]
        for rng in ranges:
            with suppress(Exception):
                rng.value = v
        i += 1
        with suppress(Exception):
            app.api.Run("DoEvents")
        time.sleep(period_s)


@dataclass
class CellSpinner:
    process: Process
    stop_event: Event
    fullname: str
    targets: tuple[SpinnerTarget, ...]

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

            v = "" if clear else final
            for sheet_name, address in self.targets:
                with suppress(Exception):
                    book.sheets[sheet_name].range(address).value = v
            with suppress(Exception):
                app.api.Run("DoEvents")


def start_cell_spinner(
    book_fullname: str,
    *,
    sheet_name: str = "Input",
    address: str = "A1",
    targets: Sequence[SpinnerTarget] | None = None,
    period_s: float = _DEFAULT_PERIOD_S,
    frames: Sequence[str] = _FRAMES,
) -> CellSpinner:
    resolved_targets = tuple(targets) if targets is not None else ((sheet_name, address),)
    stop = Event()
    p = Process(
        target=_spinner_proc,
        args=(stop, book_fullname, resolved_targets, tuple(frames), float(period_s)),
        daemon=True,
    )
    p.start()
    return CellSpinner(p, stop, book_fullname, resolved_targets)
