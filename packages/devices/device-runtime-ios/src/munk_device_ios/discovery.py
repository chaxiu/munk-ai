from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, cast

from munk.device import DeviceDescriptor, ResolvedDeviceTarget

IOSDeviceKind = Literal["simulator", "real_device"]
CommandRunner = Callable[[list[str]], str]


def empty_ios_raw() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class IOSDeviceDescriptor(DeviceDescriptor):
    kind: IOSDeviceKind
    udid: str | None = None
    state: str | None = None
    runtime: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_ios_raw)


@dataclass(frozen=True)
class ResolvedIOSDeviceTarget(ResolvedDeviceTarget):
    kind: IOSDeviceKind
    udid: str | None = None
    is_booted: bool | None = None
    state: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_ios_raw)


def list_ios_devices(*, command_runner: CommandRunner | None = None) -> list[IOSDeviceDescriptor]:
    simulators = [
        descriptor
        for descriptor in _list_simulator_devices(command_runner=command_runner)
        if descriptor.availability == "available" and descriptor.is_booted is True
    ]
    real_devices = [
        descriptor for descriptor in _list_real_devices(command_runner=command_runner) if descriptor.availability == "available"
    ]
    return sorted(
        [*simulators, *real_devices],
        key=lambda item: (
            0 if item.kind == "simulator" and item.is_booted else 1 if item.kind == "simulator" else 2,
            item.display_name.lower(),
            item.device_ref,
        ),
    )


def resolve_ios_device_target(
    *,
    device_ref: str | None,
    descriptors: list[IOSDeviceDescriptor],
    default_wda_url: str | None = None,
) -> ResolvedIOSDeviceTarget:
    if device_ref:
        for descriptor in descriptors:
            if descriptor.device_ref == device_ref:
                return _to_resolved_target(descriptor, default_wda_url=default_wda_url)
        raise ValueError(f"unknown ios device_ref: {device_ref}")

    booted_simulators = [
        descriptor
        for descriptor in descriptors
        if descriptor.kind == "simulator"
        and descriptor.availability == "available"
        and descriptor.is_booted is True
    ]
    if len(booted_simulators) == 1:
        return _to_resolved_target(booted_simulators[0], default_wda_url=default_wda_url)
    if len(booted_simulators) > 1:
        raise ValueError("multiple booted ios simulators found; device_ref is required")

    available_simulators = [
        descriptor for descriptor in descriptors if descriptor.kind == "simulator" and descriptor.availability == "available"
    ]
    if len(available_simulators) == 1:
        return _to_resolved_target(available_simulators[0], default_wda_url=default_wda_url)

    raise ValueError("no ios simulator target could be resolved; provide device_ref explicitly")


def _to_resolved_target(descriptor: IOSDeviceDescriptor, *, default_wda_url: str | None) -> ResolvedIOSDeviceTarget:
    return ResolvedIOSDeviceTarget(
        platform="ios",
        device_ref=descriptor.device_ref,
        display_name=descriptor.display_name,
        kind=descriptor.kind,
        udid=descriptor.udid,
        executable=descriptor.kind == "simulator",
        launch_endpoint=default_wda_url if descriptor.kind == "simulator" else None,
        is_booted=descriptor.is_booted,
        state=descriptor.state,
        raw=dict(descriptor.raw),
    )


def _list_simulator_devices(*, command_runner: CommandRunner | None) -> list[IOSDeviceDescriptor]:
    payload = _run_json_command(
        ["xcrun", "simctl", "list", "devices", "--json"],
        command_runner=command_runner,
        swallow_errors=False,
    )
    devices = payload.get("devices")
    if not isinstance(devices, dict):
        return []
    devices_by_runtime = cast(dict[str, Any], devices)

    results: list[IOSDeviceDescriptor] = []
    for runtime_name, entries in devices_by_runtime.items():
        runtime_name_str = str(runtime_name)
        if "iOS" not in runtime_name_str:
            continue
        if not isinstance(entries, list):
            continue
        for entry in cast(list[Any], entries):
            if not isinstance(entry, dict):
                continue
            entry_dict = cast(dict[str, Any], entry)
            udid = _as_str(entry_dict.get("udid"))
            if udid is None:
                continue
            state = _as_str(entry_dict.get("state"))
            is_available = bool(entry_dict.get("isAvailable", True))
            results.append(
                IOSDeviceDescriptor(
                    platform="ios",
                    device_ref=udid,
                    udid=udid,
                    display_name=_as_str(entry_dict.get("name")) or udid,
                    kind="simulator",
                    availability="available" if is_available else "offline",
                    is_booted=(state or "").lower() == "booted",
                    state=state,
                    runtime=runtime_name_str,
                    raw={
                        "runtime": runtime_name_str,
                        "availability_error": entry_dict.get("availabilityError"),
                    },
                )
            )
    return results


def _list_real_devices(*, command_runner: CommandRunner | None) -> list[IOSDeviceDescriptor]:
    payload = _run_json_command(
        ["xcrun", "devicectl", "list", "devices", "--quiet", "--json-output", "-"],
        command_runner=command_runner,
        swallow_errors=True,
    )
    results: list[IOSDeviceDescriptor] = []
    for entry in _find_device_dicts(payload):
        udid = _lookup_string(entry, "identifier", "udid", "hardwareProperties.udid")
        name = _lookup_string(entry, "deviceProperties.name", "name")
        if udid is None or name is None:
            continue
        availability = "available"
        state = _lookup_string(entry, "connectionProperties.state", "state", "deviceProperties.bootState")
        if state is not None and state.lower() in {"offline", "disconnected", "unavailable"}:
            availability = "offline"
        results.append(
            IOSDeviceDescriptor(
                platform="ios",
                device_ref=udid,
                udid=udid,
                display_name=name,
                kind="real_device",
                availability=availability,
                is_booted=None,
                state=state,
                runtime=None,
                raw=entry,
            )
        )
    unique: dict[str, IOSDeviceDescriptor] = {}
    for item in results:
        unique[item.device_ref] = item
    return list(unique.values())


def _run_json_command(
    command: list[str],
    *,
    command_runner: CommandRunner | None,
    swallow_errors: bool,
) -> dict[str, Any]:
    try:
        output = command_runner(command) if command_runner is not None else _default_command_runner(command)
        loaded = json.loads(output)
        if isinstance(loaded, dict):
            return cast(dict[str, Any], loaded)
    except (FileNotFoundError, subprocess.CalledProcessError, json.JSONDecodeError):
        if swallow_errors:
            return {}
        raise
    return {}


def _default_command_runner(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def _find_device_dicts(payload: Any) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            maybe_udid = _lookup_string(current, "identifier", "udid", "hardwareProperties.udid")
            maybe_name = _lookup_string(current, "deviceProperties.name", "name")
            if maybe_udid is not None and maybe_name is not None:
                results.append(current)
            stack.extend(current.values())
            continue
        if isinstance(current, list):
            stack.extend(current)
    return results


def _lookup_string(mapping: dict[str, Any], *paths: str) -> str | None:
    for path in paths:
        current: Any = mapping
        for segment in path.split("."):
            if not isinstance(current, dict):
                current = None
                break
            current = cast(dict[str, Any], current).get(segment)
        value = _as_str(current)
        if value is not None:
            return value
    return None


def _as_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)
