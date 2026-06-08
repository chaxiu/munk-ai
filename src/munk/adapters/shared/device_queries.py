from __future__ import annotations

from typing import cast

from munk.adapters.shared.payload_models import DeviceDescriptorData, DeviceListData
from munk.app import AppPlatform
from munk.device import (
    DeviceDescriptor,
    SupportsDeviceDiscovery,
    list_device_runtime_factories,
    resolve_device_runtime_factory,
)
from munk.paths import export_adb_env


def list_devices_payload(platform: str | None = None) -> DeviceListData:
    return DeviceListData(items=[build_device_payload(item) for item in list_discovered_devices(platform)])


def list_discovered_devices(platform: str | None = None) -> list[DeviceDescriptor]:
    export_adb_env()
    if platform is not None:
        resolved_platform = coerce_platform(platform)
        factory = resolve_device_runtime_factory(platform=resolved_platform)
        if not isinstance(factory, SupportsDeviceDiscovery):
            raise ValueError(f"device discovery is not available for platform '{platform}'")
        return factory.list_device_descriptors()

    items: list[DeviceDescriptor] = []
    for factory in list_device_runtime_factories().values():
        if isinstance(factory, SupportsDeviceDiscovery):
            items.extend(factory.list_device_descriptors())
    return sorted(items, key=lambda item: (item.platform, item.kind, item.display_name.lower(), item.device_ref))


def count_connected_devices() -> int:
    return sum(1 for descriptor in list_discovered_devices() if descriptor.availability == "available")


def build_device_payload(descriptor: DeviceDescriptor) -> DeviceDescriptorData:
    return DeviceDescriptorData(
        platform=descriptor.platform,
        device_ref=descriptor.device_ref,
        display_name=descriptor.display_name,
        kind=descriptor.kind,
        availability=descriptor.availability,
        is_booted=descriptor.is_booted,
        raw=dict(descriptor.raw),
    )


def coerce_platform(platform: str) -> AppPlatform:
    if platform in {"android", "ios", "web"}:
        return cast(AppPlatform, platform)
    raise ValueError(f"unsupported platform '{platform}'")
