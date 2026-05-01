from pathlib import Path
import sys

import xlwings as xw

from custom_io.excel_io import (
    run_all,
    run_selected,
)

root = Path(__file__).resolve().parent
src_dir = root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))


@xw.sub
def sub_run_selected():
    run_selected(xw.Book.caller())


@xw.sub
def sub_run_all():
    run_all(xw.Book.caller())


def main():
    run_all(xw.Book.caller())
    input()
