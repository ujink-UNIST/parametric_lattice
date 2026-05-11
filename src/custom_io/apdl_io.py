from __future__ import annotations

from pathlib import Path
from typing import Any
from ansys.mapdl.core.launcher import launch_mapdl
from ansys.mapdl.core.mapdl_console import MapdlConsole
from ansys.mapdl.core.mapdl_grpc import MapdlGrpc
from core.apdl_commands import ApdlCommands, Mapdl
from contextlib import contextmanager

from core.apdl_settings import ApdlSettings

BLOCK_STARTERS = ("*DO", "*IF", "*DOWHILE")
BLOCK_ENDERS = ("*ENDDO", "*ENDIF")


def start_mapdl(
    settings: ApdlSettings | None = None,
    **launch_kwargs: Any,
) -> Mapdl:
    settings = settings or ApdlSettings()
    settings.prepare_directories()

    kwargs = settings.to_launch_kwargs()
    kwargs.update(launch_kwargs)

    return launch_mapdl(**kwargs)


def run_commands(
    mapdl: Mapdl, commands: ApdlCommands | tuple[Any, ...]
) -> None:
    block: list[str] = []
    in_block = False

    for command in commands:
        if callable(command):
            command(mapdl)
            continue
        if isinstance(command, tuple):
            run_commands(mapdl, command)
            continue

        cmd_upper = command.strip().upper()

        if any(
            cmd_upper.startswith(s) for s in BLOCK_STARTERS
        ):
            in_block = True
            block.append(command)
        elif in_block:
            block.append(command)
            if any(
                cmd_upper.startswith(e)
                for e in BLOCK_ENDERS
            ):
                result = mapdl.input_strings(
                    "\n".join(block)
                )
                if result:
                    print(result)
                block = []
                in_block = False
        else:
            result = mapdl.run(command)
            if result:
                print(result)


def _kill_process_tree(pid: int) -> None:
    try:
        import psutil

        parent = psutil.Process(pid)
        for child in parent.children(recursive=True):
            child.kill()
            print(f"Child process {child.pid} killed")
        parent.kill()
        print(f"MAPDL process {pid} killed")
    except psutil.NoSuchProcess:
        print(f"Process {pid} already dead")
    except Exception as e:
        print(f"Process kill error: {e}")


def _stop_grpc(mapdl: MapdlGrpc) -> None:
    proc = getattr(mapdl, "_mapdl_process", None)
    pid = proc.pid if proc is not None else None
    print(f"PID to kill: {pid}")

    mapdl.exit()

    if pid is not None:
        _kill_process_tree(pid)


def stop_mapdl(mapdl: Mapdl) -> None:
    """Stop MAPDL session.

    In unit tests we use a lightweight fake object that only exposes an
    ``exit()`` method, so we fall back to duck-typing when the object is not an
    official MAPDL class.
    """

    try:
        if isinstance(mapdl, MapdlGrpc):
            _stop_grpc(mapdl)
        elif isinstance(mapdl, MapdlConsole):
            mapdl.exit()
        elif hasattr(mapdl, "exit"):
            mapdl.exit()  # type: ignore[call-arg]
        print("MAPDL exited successfully")
    except Exception as e:
        print(f"MAPDL exit error: {e}")


@contextmanager
def mapdl_session(
    settings: ApdlSettings | None = None,
    **launch_kwargs: Any,
):

    mapdl = start_mapdl(settings, **launch_kwargs)
    try:
        yield mapdl
    finally:
        print("Closing MAPDL...")
        stop_mapdl(mapdl)
