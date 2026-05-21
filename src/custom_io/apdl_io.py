# apdl_io.py

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from datetime import datetime

from ansys.mapdl.core.launcher import launch_mapdl
from ansys.mapdl.core.mapdl_console import MapdlConsole
from ansys.mapdl.core.mapdl_grpc import MapdlGrpc
from ansys.mapdl.core.launcher.errors import LaunchError

from core.apdl_commands import ApdlCommands, Mapdl
from core.apdl_settings import ApdlSettings


def _print_port_users(port: int) -> None:
    """Best-effort: print which process(es) are listening on/using `port`."""

    try:
        import psutil  # type: ignore
    except ImportError:
        print(f"[mapdl] Port {port} check skipped (psutil not installed)")
        return

    try:
        conns = psutil.net_connections(kind="inet")
    except Exception as e:
        print(f"[mapdl] Port {port} check failed: {e}")
        return

    hits = []
    for c in conns:
        laddr = getattr(c, "laddr", None)
        if not laddr:
            continue
        if getattr(laddr, "port", None) != port:
            continue
        hits.append(c)

    if not hits:
        return

    print(f"[mapdl] Port {port} is already in use by:")
    for c in hits:
        pid = getattr(c, "pid", None)
        status = getattr(c, "status", None)
        laddr = getattr(c, "laddr", None)
        raddr = getattr(c, "raddr", None)
        proc_desc = "<unknown>"
        if pid:
            try:
                p = psutil.Process(pid)
                proc_desc = f"{p.name()} (pid={pid}) cmdline={' '.join(p.cmdline())}"
            except Exception:
                proc_desc = f"pid={pid}"
        print(f"  - {proc_desc} status={status} laddr={laddr} raddr={raddr}")


def start_mapdl(
    settings: ApdlSettings | None = None,
    **launch_kwargs: Any,
) -> Mapdl:
    settings = settings or ApdlSettings()
    settings.prepare_directories()

    kwargs = settings.to_launch_kwargs()
    kwargs.update(launch_kwargs)

    # Preflight check: if we're using gRPC, the default port is 50052 unless overridden.
    if kwargs.get("mode") == "grpc":
        port = int(kwargs.get("port", 50052))
        _print_port_users(port)

    try:
        return launch_mapdl(**kwargs)
    except LaunchError:
        # Print again on failure to make debugging easier.
        if kwargs.get("mode") == "grpc":
            port = int(kwargs.get("port", 50052))
            _print_port_users(port)
        raise


def run_commands(
    mapdl: Mapdl, commands: ApdlCommands
) -> None:
    apdl_script = generate_apdl_script(commands)
    do_count = 0
    if_count = 0
    block = ""

    for apdl_line in apdl_script.splitlines():
        line = apdl_line.rstrip()
        if not line.strip():
            continue

        upper = (
            line.strip().upper().split("!")[0].strip()
        )  # 주석 제거 후 판단

        # 카운터 업데이트 (block에 추가하기 전)
        if upper.startswith("*DO"):
            do_count += 1
        elif upper.startswith("*ENDDO"):
            do_count = max(0, do_count - 1)
        elif upper.startswith("*IF") and "THEN" in upper:
            if_count += 1
        elif upper.startswith("*ENDIF"):
            if_count = max(0, if_count - 1)

        block += line + "\n"

        # DO/IF 블록 밖에서만 전송
        if if_count == 0 and do_count == 0:
            result = mapdl.input_strings(block)
            block = ""
            if result:
                print(result)

    # 혹시 남은 블록
    if block.strip():
        result = mapdl.input_strings(block)
        if result:
            print(result)


def generate_apdl_script(commands: ApdlCommands) -> str:
    return "\n".join(cmd.strip() for cmd in commands if cmd.strip())


def write_apdl_macro(
    path: str | Path,
    commands: ApdlCommands,
    *,
    title: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Write an APDL macro/input file containing the given command sequence.

    Intended for reproducibility/debugging (e.g. artifacts/case/<hash>/main.mac).

    Notes:
      - We write the *flattened* command sequence exactly as we send it to MAPDL.
      - APDL comments use '!'.
    """

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    header: list[str] = []
    header.append("! ------------------------------")
    header.append(f"! Generated: {datetime.now().isoformat(timespec='seconds')}")
    if title:
        header.append(f"! Title: {title}")
    if metadata:
        header.append("! Metadata:")
        for k, v in metadata.items():
            header.append(f"!   {k}: {v}")
    header.append("! ------------------------------")
    header.append("")

    body = generate_apdl_script(commands)
    p.write_text("\n".join(header) + body + "\n", encoding="utf-8")


def _kill_process_tree(pid: int) -> None:
    try:
        import psutil  # type: ignore
    except ImportError:
        print("psutil is not installed; cannot kill MAPDL process tree")
        return

    try:
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
        # Give MAPDL a moment to release the gRPC port/file handles.
        time.sleep(1.0)
