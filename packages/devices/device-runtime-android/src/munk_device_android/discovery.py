from __future__ import annotations

import os
import subprocess
from typing import Any, Callable

from munk.device import DeviceDescriptor

CommandRunner = Callable[[list[str]], str]
ENV_ADB_PATH = "MUNK_ADB_PATH"
ENV_ADBUTILS_ADB_PATH = "ADBUTILS_ADB_PATH"


def list_android_devices(*, command_runner: CommandRunner | None = None) -> list[DeviceDescriptor]:
    command = _adb_command(["devices", "-l"])
    output = command_runner(command) if command_runner is not None else _default_devices_command_runner(command)
    results: list[DeviceDescriptor] = []
    for line in output.splitlines():
        descriptor = _parse_adb_devices_line(line)
        if descriptor is not None:
            results.append(descriptor)
    return sorted(results, key=lambda item: (item.kind, item.display_name.lower(), item.device_ref))


def _parse_adb_devices_line(line: str) -> DeviceDescriptor | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("List of devices attached"):
        return None

    parts = stripped.split()
    if len(parts) < 2:
        return None

    serial, state = parts[0], parts[1]
    if state != "device":
        return None

    raw = _parse_adb_metadata(parts[2:])
    model = _as_str(raw.get("model"))
    display_name = _humanize_model_name(model) or serial
    return DeviceDescriptor(
        platform="android",
        device_ref=serial,
        display_name=display_name,
        kind="emulator" if serial.startswith("emulator-") else "real_device",
        availability="available",
        is_booted=True,
        raw=raw,
    )


def _parse_adb_metadata(parts: list[str]) -> dict[str, Any]:
    metadata: dict[str, Any] = {}
    for part in parts:
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if not key:
            continue
        metadata[key] = value
    return metadata


def _humanize_model_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.replace("_", " ").strip()
    return cleaned or None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _default_devices_command_runner(command: list[str]) -> str:
    try:
        return _run_checked_command(command)
    except subprocess.CalledProcessError:
        _run_checked_command(_adb_command(["start-server"]))
        return _run_checked_command(command)


def _run_checked_command(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def _adb_command(args: list[str]) -> list[str]:
    return [_resolve_adb_executable(), *args]


def _resolve_adb_executable() -> str:
    explicit = os.environ.get(ENV_ADB_PATH) or os.environ.get(ENV_ADBUTILS_ADB_PATH)
    if explicit:
        os.environ[ENV_ADBUTILS_ADB_PATH] = explicit
        return explicit
    return "adb"
