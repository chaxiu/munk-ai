from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from munk.app import AppPlatform

DeviceAvailability = Literal["available", "busy", "offline", "unsupported"]


def empty_device_descriptor_raw() -> dict[str, Any]:
    return {}


@dataclass(frozen=True)
class DeviceDescriptor:
    platform: AppPlatform
    device_ref: str
    display_name: str
    kind: str
    availability: DeviceAvailability = "available"
    is_booted: bool | None = None
    raw: dict[str, Any] = field(default_factory=empty_device_descriptor_raw)


@dataclass(frozen=True)
class ResolvedDeviceTarget:
    platform: AppPlatform
    device_ref: str
    kind: str
    display_name: str
    executable: bool
    launch_endpoint: str | None = None
    raw: dict[str, Any] = field(default_factory=empty_device_descriptor_raw)


@runtime_checkable
class SupportsDeviceDiscovery(Protocol):
    """Optional runtime-factory capability for listing candidate devices before execution."""

    def list_device_descriptors(self) -> list[DeviceDescriptor]: ...
