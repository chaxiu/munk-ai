from __future__ import annotations

import socket
import subprocess


def is_port_available(*, host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) != 0


def allocate_ephemeral_port(*, host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        return int(sock.getsockname()[1])


def consume_process_output(process: subprocess.Popen[str]) -> str | None:
    stdout = ""
    stderr = ""
    try:
        stdout, stderr = process.communicate(timeout=0.1)
    except subprocess.TimeoutExpired:
        return None
    except ValueError:
        # sudo stdin is written and closed immediately after launch. Python's
        # communicate() may try to flush that closed pipe, so fall back to
        # reading the remaining output streams directly.
        try:
            stdout = process.stdout.read() if process.stdout is not None else ""
        except (OSError, ValueError):
            stdout = ""
        try:
            stderr = process.stderr.read() if process.stderr is not None else ""
        except (OSError, ValueError):
            stderr = ""
    combined = "\n".join(part.strip() for part in (stderr, stdout) if part and part.strip()).strip()
    return combined or None
