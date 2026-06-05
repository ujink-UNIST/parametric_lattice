#tables.py
"""Module for tables functionality in src.custom_io.excel."""

from __future__ import annotations

from typing import Any

import xlwings as xw  # type: ignore[import-not-found]
from xlwings.main import Table  # type: ignore[import-not-found]

Header = tuple[str, ...]
Body = tuple[tuple[Any, ...], ...]


def find_table(book: xw.Book, key: str) -> Table:
    """Find an Excel ListObject by name or display name.

    Parameters
    ----------
    book : xw.Book
        Workbook to search.
    key : str
        Table name or display name.

    Returns
    -------
    Table
        Matching xlwings table.

    Raises
    ------
    KeyError
        If no matching table exists.
    """

    table, _sheet = find_table_and_sheet(book, key)
    return table


def find_table_and_sheet(book: xw.Book, key: str) -> tuple[Table, xw.Sheet]:
    """Find an Excel table and the worksheet that owns it.

    Parameters
    ----------
    book : xw.Book
        Workbook to search.
    key : str
        Table name or display name.

    Returns
    -------
    tuple[Table, xw.Sheet]
        Matching table and containing worksheet.
    """

    for sheet in book.sheets:
        for table in sheet.tables:
            if table.name == key or table.display_name == key:
                return table, sheet

    raise KeyError(f"Could not find Excel table {key!r}")


def get_table_data(table: Table) -> tuple[Header, Body]:
    """Read an Excel table into immutable header and body tuples.

    Parameters
    ----------
    table : Table
        xlwings table to read.

    Returns
    -------
    tuple[Header, Body]
        Header values as strings and body values as row tuples. Empty tables
        return an empty body.
    """

    header_row_range = table.header_row_range
    data_body_range = table.data_body_range

    if header_row_range is None:
        return (), ()

    header_values = header_row_range.options(ndim=1).value
    headers = tuple(str(v) for v in header_values)

    if data_body_range is None:
        return headers, ()

    body_values = data_body_range.options(ndim=2).value
    body = tuple(tuple(row) for row in body_values)

    return headers, body
