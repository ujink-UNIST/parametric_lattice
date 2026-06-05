#status.py
"""Module for status functionality in src.custom_io.excel."""

from __future__ import annotations

from contextlib import suppress

import xlwings as xw  # type: ignore[import-not-found]

from custom_io.excel.tables import find_table_and_sheet

_STATUS_COL = "A"
_PENDING_MARK = "…"
_DONE_MARK = "✔"
_FAIL_MARK = "✘"
_SKIP_MARK = "➥"

_PENDING_COLOR = (235, 235, 235)
_RUNNING_COLOR = (255, 242, 204)
_DONE_COLOR = (198, 239, 206)
_FAIL_COLOR = (255, 199, 206)
_SKIP_COLOR = (221, 235, 247)

_PENDING_FONT = (90, 90, 90)
_RUNNING_FONT = (156, 101, 0)
_DONE_FONT = (0, 97, 0)
_FAIL_FONT = (156, 0, 6)
_SKIP_FONT = (31, 78, 121)


def doevents(book: xw.Book) -> None:
    """Let Excel process UI events after cell updates."""

    with suppress(Exception):
        book.app.api.Run("DoEvents")


def status_range_for_input_row(
    book: xw.Book,
    row_idx: int,
    *,
    input_table: str = "t_input",
    status_col: str = _STATUS_COL,
) -> xw.Range | None:
    """Return the status cell for a row in the input table.

    Parameters
    ----------
    book : xw.Book
        Workbook containing the input table.
    row_idx : int
        Zero-based body row index in ``input_table``.
    input_table : str, optional
        Name of the input ListObject.
    status_col : str, optional
        Excel column letter used for status marks.

    Returns
    -------
    xw.Range or None
        Status cell range, or ``None`` if the table or row cannot be resolved.
    """

    try:
        t, sheet = find_table_and_sheet(book, input_table)
    except KeyError:
        return None

    body = t.data_body_range
    if body is None:
        return None

    excel_row = int(body.row) + int(row_idx)
    addr = f"{status_col}{excel_row}"

    try:
        return sheet.range(addr)
    except Exception:
        return None


def set_status_pending(book: xw.Book, cell: xw.Range | None) -> None:
    """Mark a case as pending in Excel.

    Parameters
    ----------
    book : xw.Book
        Workbook used to process UI events.
    cell : xw.Range or None
        Status cell to update. ``None`` is ignored.
    """

    if cell is None:
        return
    cell.value = _PENDING_MARK
    _style_status_cell(cell, fill_rgb=_PENDING_COLOR, font_rgb=_PENDING_FONT, bold=True)
    doevents(book)


def set_status_running(book: xw.Book, cell: xw.Range | None) -> None:
    """Mark a case as running and mirror the global spinner cell.

    Parameters
    ----------
    book : xw.Book
        Workbook used to process UI events.
    cell : xw.Range or None
        Status cell to update. ``None`` is ignored.
    """

    if cell is None:
        return
    cell.formula = "=Input!$A$1"
    _style_status_cell(cell, fill_rgb=_RUNNING_COLOR, font_rgb=_RUNNING_FONT)
    doevents(book)


def set_status_done(book: xw.Book, cell: xw.Range | None) -> None:
    """Mark a case as successfully completed in Excel.

    Parameters
    ----------
    book : xw.Book
        Workbook used to process UI events.
    cell : xw.Range or None
        Status cell to update. ``None`` is ignored.
    """

    if cell is None:
        return
    cell.value = _DONE_MARK
    _style_status_cell(cell, fill_rgb=_DONE_COLOR, font_rgb=_DONE_FONT)
    doevents(book)


def set_status_fail(book: xw.Book, cell: xw.Range | None) -> None:
    """Mark a case as failed in Excel.

    Parameters
    ----------
    book : xw.Book
        Workbook used to process UI events.
    cell : xw.Range or None
        Status cell to update. ``None`` is ignored.
    """

    if cell is None:
        return
    cell.value = _FAIL_MARK
    _style_status_cell(cell, fill_rgb=_FAIL_COLOR, font_rgb=_FAIL_FONT)
    doevents(book)


def set_status_skip(book: xw.Book, cell: xw.Range | None) -> None:
    """Mark a case as skipped in Excel.

    Parameters
    ----------
    book : xw.Book
        Workbook used to process UI events.
    cell : xw.Range or None
        Status cell to update. ``None`` is ignored.
    """

    if cell is None:
        return
    cell.value = _SKIP_MARK
    _style_status_cell(cell, fill_rgb=_SKIP_COLOR, font_rgb=_SKIP_FONT)
    doevents(book)


def _rgb_to_excel_color(rgb: tuple[int, int, int]) -> int:
    """Convert an RGB tuple to Excel's BGR integer color format.

    Parameters
    ----------
    rgb : tuple[int, int, int]
        Red, green, and blue components.

    Returns
    -------
    int
        Excel/VBA color integer.
    """

    r, g, b = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
    return (b << 16) | (g << 8) | r


def _style_status_cell(
    cell: xw.Range,
    *,
    fill_rgb: tuple[int, int, int],
    font_rgb: tuple[int, int, int] | None = None,
    bold: bool = False,
) -> None:
    with suppress(Exception):
        cell.color = fill_rgb
    with suppress(Exception):
        if font_rgb is not None:
            cell.api.Font.Color = _rgb_to_excel_color(font_rgb)
    with suppress(Exception):
        cell.api.Font.Bold = bool(bold)
    with suppress(Exception):
        cell.api.HorizontalAlignment = -4108
