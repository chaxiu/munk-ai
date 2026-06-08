from __future__ import annotations

import errno
import os
import signal
import subprocess
import time

import typer

from munk.adapters.local_api.server import serve_local_api
from munk.services.logging_service import setup_persistent_logging
from munk.services.machine_command_service import MachineCommandService
from munk.storage_mode import StorageMode, apply_default_home
from munk.user_data import logs_home

DEFAULT_LOCAL_API_HOST = "127.0.0.1"
DEFAULT_LOCAL_API_PORT = 16888


def _list_listening_pids(port: int) -> list[int]:
    result = subprocess.run(
        ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        stderr = result.stderr.strip()
        raise RuntimeError(f"failed to inspect port {port} with lsof: {stderr or result.returncode}")
    pids: list[int] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if not raw:
            continue
        pids.append(int(raw))
    return pids


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return False
        raise
    return True


def _terminate_port_conflicts(port: int, *, grace_period_seconds: float = 2.0) -> list[int]:
    killed_pids: list[int] = []
    current_pid = os.getpid()
    for pid in _list_listening_pids(port):
        if pid == current_pid:
            continue
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + grace_period_seconds
        while time.monotonic() < deadline:
            if not _is_pid_alive(pid):
                killed_pids.append(pid)
                break
            time.sleep(0.05)
        else:
            os.kill(pid, signal.SIGKILL)
            killed_pids.append(pid)
    return killed_pids


def serve_command(
    *,
    host: str = DEFAULT_LOCAL_API_HOST,
    port: int = DEFAULT_LOCAL_API_PORT,
    log_level: str = "info",
    disable_mcp: bool = False,
    kill_port_conflicts: bool = False,
) -> None:
    apply_default_home(StorageMode.PROFILE)
    serve_log_path = logs_home() / "serve.log"
    serve_log_path.parent.mkdir(parents=True, exist_ok=True)
    setup_persistent_logging(serve_log_path)
    response = MachineCommandService().cleanup_stale_claims()
    cleaned_count = int(response.payload["data"]["cleaned_count"])
    if cleaned_count > 0:
        typer.echo(f"cleaned {cleaned_count} stale device claims before starting local API", err=True)
    if kill_port_conflicts:
        killed_pids = _terminate_port_conflicts(port)
        if killed_pids:
            pid_list = ", ".join(str(pid) for pid in killed_pids)
            typer.echo(
                f"killed processes occupying port {port} before starting local API: {pid_list}",
                err=True,
            )
    serve_local_api(host=host, port=port, log_level=log_level, enable_mcp=not disable_mcp)
