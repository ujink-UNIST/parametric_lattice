#apdl_settings.py
"""Module for apdl settings functionality in src.core."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from core.apdl_commands import Mapdl

MapdlMode = Literal["grpc", "console"]
GpuMode = Literal["off", "on"]


@dataclass(frozen=True)
class ApdlSettings:
    # Default execution settings
    jobname: str = "file"
    # NOTE: Avoid hard-coding the Windows username. Use the current user's home directory.
    # Default: ~/Documents/ANSYS workdir
    run_location: Path = Path.home() / "Documents" / "ANSYS workdir"
    mode: MapdlMode = "grpc"
    override: bool = True

    # CPU / memory
    nproc: int | None = None
    memory_mb: int | None = None  # MAPDL -m
    database_mb: int | None = None  # MAPDL -db

    # GPU
    gpu: GpuMode = "off"

    # Miscellaneous settings
    additional_switches: tuple[str, ...] = field(
        default_factory=tuple
    )
    cleanup_on_exit: bool = True

    def to_launch_kwargs(self) -> dict[str, Any]:
        switches = list(self.additional_switches)

        if self.memory_mb is not None:
            switches += ["-m", str(self.memory_mb)]

        if self.database_mb is not None:
            switches += ["-db", str(self.database_mb)]

        if self.gpu == "on":
            switches.append("-acc")

        kwargs: dict[str, Any] = {
            "jobname": self.jobname,
            "run_location": str(self.run_location),
            "mode": self.mode,
            "override": self.override,
            "cleanup_on_exit": self.cleanup_on_exit,
        }

        if self.nproc is not None:
            kwargs["nproc"] = self.nproc

        if switches:
            kwargs["additional_switches"] = " ".join(
                switches
            )

        return kwargs

    def prepare_directories(self) -> None:
        self.run_location.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class ApdlRuntimeSettings:
    use_gpu_solver: bool = False
    solver: str | None = None  # e.g. "SPARSE", "PCG", "JCG"

    def apply(self, mapdl: Mapdl) -> None:
        if self.solver is not None:
            mapdl.run(f"EQSLV,{self.solver}")

        if self.use_gpu_solver:
            mapdl.run("ACCOPTION,ON")
