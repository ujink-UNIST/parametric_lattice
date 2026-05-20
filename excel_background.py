from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import xlwings as xw  # type: ignore[import-not-found]

# Bootstrap so this module can run from the repo root.
root = Path(__file__).resolve().parent
src_dir = root / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# Imported after sys.path bootstrap in main() to satisfy linters.


def _find_app_by_pid(pid: int) -> xw.App:
    for app in xw.apps:
        try:
            if int(app.pid) == int(pid):
                return app
        except Exception:
            continue
    raise RuntimeError(f"Could not find running Excel instance with pid={pid}")


def _find_book(app: xw.App, fullname: str) -> xw.Book:
    target = os.path.normcase(os.path.abspath(fullname))
    for b in app.books:
        try:
            if os.path.normcase(os.path.abspath(b.fullname)) == target:
                return b
        except Exception:
            continue
    # Fallback: try by name
    name = Path(fullname).name
    try:
        return app.books[name]
    except Exception:
        pass
    raise RuntimeError(f"Could not find workbook {fullname!r} in Excel pid={app.pid}")


def main() -> None:
    p = argparse.ArgumentParser(description="Background worker for Excel xlwings calls")
    p.add_argument("--pid", type=int, required=True, help="Excel application PID")
    p.add_argument("--book", type=str, required=True, help="Workbook full path")
    p.add_argument(
        "--mode",
        type=str,
        required=True,
        choices=["run", "postprocess"],
        help="What to execute",
    )
    p.add_argument(
        "--selected",
        type=str,
        default="null",
        help="JSON list of 0-based row indices, or null for all",
    )
    args = p.parse_args()

    selected = json.loads(args.selected)
    selected_indices = None if selected is None else tuple(int(i) for i in selected)

    from custom_io.excel_io import run_selected, run_selected_postprocess

    app = _find_app_by_pid(args.pid)
    book = _find_book(app, args.book)

    if args.mode == "run":
        run_selected(book, selected_indices)
    else:
        run_selected_postprocess(book, selected_indices)


if __name__ == "__main__":
    main()
