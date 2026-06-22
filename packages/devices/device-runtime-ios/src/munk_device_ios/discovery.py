from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any, Callable, Literal, Protocol, cast

from munk.device import DeviceDescriptor, ResolvedDeviceTarget
from munk.services.ios import IOSBridgeRealDevice, get_default_ios_device_bridge_manager

IOSDeviceKind = Literal["simulator", "real_device"]
CommandRunner = Callable[[list[str]], str]


class SupportsIOSRealDeviceDiscovery(Protocol):
    def list_real_devices(self) -> list[IOSBridgeRealDevice]: ...


def empty_ios_raw() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class IOSDeviceDescriptor(DeviceDescriptor):
    kind: IOSDeviceKind
    udid: str | None = None
    coredevice_identifier: str | None = None
    state: str | None = None
    runtime: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_ios_raw)


@dataclass(frozen=True)
class ResolvedIOSDeviceTarget(ResolvedDeviceTarget):
    kind: IOSDeviceKind
    udid: str | None = None
    coredevice_identifier: str | None = None
    is_booted: bool | None = None
    state: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_ios_raw)


def list_ios_devices(
    *,
    command_runner: CommandRunner | None = None,
    bridge_manager: SupportsIOSRealDeviceDiscovery | None = None,
) -> list[IOSDeviceDescriptor]:
    simulators = [
        descriptor
        for descriptor in _list_simulator_devices(command_runner=command_runner)
        if descriptor.availability == "available"
    ]
    real_devices = [
        descriptor
        for descriptor in _list_real_devices_via_bridge(bridge_manager=bridge_manager)
        if descriptor.availability == "available"
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
            if _matches_device_ref(descriptor, device_ref):
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
        coredevice_identifier=descriptor.coredevice_identifier,
        executable=descriptor.availability == "available",
        launch_endpoint=default_wda_url,
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


def _list_real_devices_via_bridge(*, bridge_manager: SupportsIOSRealDeviceDiscovery | None) -> list[IOSDeviceDescriptor]:
    manager = bridge_manager or get_default_ios_device_bridge_manager()
    real_devices = manager.list_real_devices()
    unique: dict[str, IOSDeviceDescriptor] = {}
    for item in real_devices:
        descriptor = _bridge_device_to_descriptor(item)
        unique[descriptor.device_ref] = descriptor
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
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        if swallow_errors:
            return {}
        raise
    return {}


def _default_command_runner(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout


def _bridge_device_to_descriptor(device: IOSBridgeRealDevice) -> IOSDeviceDescriptor:
    availability = "available"
    if device.state is not None and device.state.lower() in {"offline", "disconnected", "unavailable"}:
        availability = "offline"
    coredevice_identifier = _lookup_string(device.raw, "coredevice_identifier", "identifier")
    raw = dict(device.raw)
    raw.setdefault("platform_version", device.platform_version)
    raw.setdefault("real_device_udid", device.udid)
    if device.backend_kind is not None:
        raw.setdefault("bridge_backend_kind", device.backend_kind)
    raw.setdefault("bridge_visible", True)
    return IOSDeviceDescriptor(
        platform="ios",
        device_ref=device.udid,
        udid=device.udid,
        display_name=device.name,
        kind="real_device",
        coredevice_identifier=coredevice_identifier,
        availability=availability,
        is_booted=_infer_real_device_boot_state(device.state, availability=availability),
        state=device.state,
        runtime=None,
        raw=raw,
    )


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


def _infer_real_device_boot_state(state: str | None, *, availability: str) -> bool | None:
    if state is None:
        return True if availability == "available" else False if availability == "offline" else None
    normalized = state.lower()
    if normalized in {"offline", "disconnected", "unavailable"}:
        return False
    if normalized in {"connected", "available", "booted"}:
        return True
    return True if availability == "available" else False if availability == "offline" else None


def _matches_device_ref(descriptor: IOSDeviceDescriptor, device_ref: str) -> bool:
    return descriptor.device_ref == device_ref
