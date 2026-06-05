#ui_heartbeat.py
"""Module for ui heartbeat functionality in src.custom_io.excel."""

from __future__ import annotations

"""Excel UI heartbeat.

Long-running Python/COM loops can starve Excel's message pump, making the UI
appear frozen (scrolling, repaint, sheet switching).

This helper provides a throttled `tick()` that yields to Excel via DoEvents.
"""

import time
from contextlib import suppress

import xlwings as xw  # type: ignore[import-not-found]


class UIHeartbeat:
    def __init__(self, book: xw.Book, *, min_interval_s: float = 0.15) -> None:
        self._book = book
        self._min_interval_s = float(min_interval_s)
        self._t_last = 0.0

    def tick(self, *, force: bool = False) -> None:
        """Yield to Excel UI if enough time elapsed (or force=True)."""

        t = time.perf_counter()
        if not force and (t - self._t_last) < self._min_interval_s:
            return
        self._t_last = t

        # Best-effort DoEvents.
        with suppress(Exception):
            self._book.app.api.Run("DoEvents")
