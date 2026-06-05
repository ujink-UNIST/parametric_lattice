#batch.py
"""Module for batch functionality in src.custom_io.mapdl."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from core.apdl_settings import ApdlSettings
from core.apdl_commands import ApdlCommands, Mapdl
from custom_io.mapdl.apdl_io import mapdl_session, run_commands


class MapdlBatchRunner:
    """Run APDL command batches while reusing MAPDL for multiple cases.

    Parameters
    ----------
    session_root : Path
        Directory where per-batch MAPDL session directories are created.
    jobname : str
        MAPDL job name used for launched sessions.
    nproc : int or None, optional
        Number of MAPDL processes to request. ``None`` leaves the default to
        PyMAPDL/MAPDL.
    batch_size : int, optional
        Number of cases to run per MAPDL launch. ``0`` means reuse one MAPDL
        session for all cases.
    """

    def __init__(
        self,
        *,
        session_root: Path,
        jobname: str,
        nproc: int | None = None,
        batch_size: int = 1,
    ) -> None:
        if batch_size < 0:
            raise ValueError(f"batch_size must be 0 or positive (got {batch_size})")

        self.session_root = Path(session_root)
        self.jobname = str(jobname)
        self.nproc = nproc
        self.batch_size = int(batch_size)

        self._active_session = None
        self._active_mapdl: Mapdl | None = None
        self._cases_in_session = 0
        self._session_index = 0

    def __enter__(self) -> "MapdlBatchRunner":
        self.session_root.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        """Close the active MAPDL session, if any.

        Notes
        -----
        The runner remains reusable after closing; the next ``run_case`` call
        starts a new session.
        """

        if self._active_session is not None:
            self._active_session.__exit__(None, None, None)
        self._active_session = None
        self._active_mapdl = None
        self._cases_in_session = 0

    def run_case(self, commands: ApdlCommands | Iterable[str]) -> None:
        """Run one APDL command sequence in the current batch session.

        Parameters
        ----------
        commands : ApdlCommands or Iterable[str]
            APDL commands to send to MAPDL.
        """

        mapdl = self._ensure_session()
        run_commands(mapdl, tuple(commands))
        self._cases_in_session += 1

    def _ensure_session(self) -> Mapdl:
        """Return a reusable MAPDL session or launch a new batch session.

        Returns
        -------
        Mapdl
            Active MAPDL gRPC or console object.
        """

        if self._active_mapdl is not None and (
            self.batch_size == 0 or self._cases_in_session < self.batch_size
        ):
            return self._active_mapdl

        self.close()
        self._session_index += 1
        session_dir = self.session_root / f"batch_{self._session_index:04d}"
        session_dir.mkdir(parents=True, exist_ok=True)

        settings = ApdlSettings(
            jobname=self.jobname,
            run_location=session_dir,
            cleanup_on_exit=False,
            nproc=self.nproc,
        )
        session = mapdl_session(settings=settings)
        mapdl = session.__enter__()
        self._active_session = session
        self._active_mapdl = mapdl
        return mapdl
