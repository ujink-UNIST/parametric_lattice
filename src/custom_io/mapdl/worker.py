#worker.py
"""Module for worker functionality in src.custom_io.mapdl."""

from __future__ import annotations

"""Subprocess entrypoint for running MAPDL macros.

This module is intended to be executed in a separate Python process so that
multiple MAPDL instances can be run in parallel (future work).

Current responsibility:
- launch MAPDL (grpc)
- feed an APDL macro/input file to MAPDL

It intentionally does *not* touch Excel/COM.
"""

import argparse
from pathlib import Path

from custom_io.mapdl.apdl_io import mapdl_session, run_commands
from core.apdl_settings import ApdlSettings


def _read_macro(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8", errors="replace")
    # Keep all non-empty lines; run_commands will handle block sending.
    lines = [ln.rstrip("\n") for ln in text.splitlines()]
    return tuple(ln for ln in lines if ln.strip())


def main(argv: list[str] | None = None) -> int:
    """Run a MAPDL macro from a subprocess entry point.

    Parameters
    ----------
    argv : list[str] or None, optional
        Command-line arguments. When ``None``, arguments are read from
        ``sys.argv`` by ``argparse``.

    Returns
    -------
    int
        Process exit code.
    """

    p = argparse.ArgumentParser(description="Run an APDL macro in a MAPDL subprocess")
    p.add_argument("--macro", required=True, help="Path to .mac file")
    p.add_argument(
        "--session-dir",
        required=True,
        help="MAPDL run_location for this subprocess (must be unique per process)",
    )
    p.add_argument("--jobname", default="case")
    p.add_argument("--nproc", type=int, default=None, help="MAPDL number of processes (-np)")
    p.add_argument("--cleanup", action="store_true", default=False)
    args = p.parse_args(argv)

    macro_path = Path(args.macro)
    if not macro_path.exists():
        raise FileNotFoundError(macro_path)

    session_dir = Path(args.session_dir)
    session_dir.mkdir(parents=True, exist_ok=True)

    settings = ApdlSettings(
        jobname=str(args.jobname),
        run_location=session_dir,
        cleanup_on_exit=bool(args.cleanup),
        nproc=args.nproc,
    )

    commands = _read_macro(macro_path)

    with mapdl_session(settings=settings) as mapdl:
        run_commands(mapdl, commands)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
