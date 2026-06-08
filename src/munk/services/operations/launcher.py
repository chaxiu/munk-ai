from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from munk.runtime_distribution import resolve_runtime_layout
from munk.services.operations.models import OPERATION_DB_ENV, OPERATION_ID_ENV, DetachedLaunchResult
from munk.services.operations.paths import operation_dir


def sanitize_detached_args(argv: list[str]) -> list[str]:
    sanitized: list[str] = []
    for arg in argv:
        if arg == "--detach":
            continue
        if arg == "--no-wait":
            continue
        sanitized.append(arg)
    return sanitized


def build_cli_invocation(argv: list[str]) -> list[str]:
    layout = resolve_runtime_layout()
    launcher = layout.bin_root / "munk"
    if layout.layout_mode == "distribution" and launcher.exists():
        return [str(launcher), *argv]
    return [sys.executable, "-m", "munk.cli", *argv]


def launch_detached_operation(
    *,
    argv: list[str],
    operation_id: str,
    db_path: Path,
) -> DetachedLaunchResult:
    invocation = build_cli_invocation(sanitize_detached_args(argv))
    debug_dir = operation_dir(operation_id)
    launcher_log_path = debug_dir / "launcher.log"
    env = os.environ.copy()
    env[OPERATION_ID_ENV] = operation_id
    env[OPERATION_DB_ENV] = str(db_path)
    with launcher_log_path.open("a", encoding="utf-8") as log_file:
        process = subprocess.Popen(  # noqa: S603
            invocation,
            cwd=str(Path.cwd()),
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
            env=env,
        )
    return DetachedLaunchResult(
        operation_id=operation_id,
        pid=process.pid,
        command=invocation,
        launcher_log_path=launcher_log_path,
    )
