from __future__ import annotations

from munk.app import AppTarget
from munk.device import DeviceDescriptor, SupportsDeviceDiscovery

from .device import AndroidDevice
from .discovery import list_android_devices


class AndroidDeviceRuntimeFactory(SupportsDeviceDiscovery):
    runtime_id = "android"
    supported_platforms = ("android",)

    def create_device(
        self,
        *,
        device_ref: str | None,
        app_target: AppTarget,
    ) -> AndroidDevice:
        return AndroidDevice.connect(device_ref, app_target=app_target)

    def list_device_descriptors(self) -> list[DeviceDescriptor]:
        return list_android_devices()


def build_device_runtime_factory() -> AndroidDeviceRuntimeFactory:
    return AndroidDeviceRuntimeFactory()
