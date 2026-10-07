from __future__ import annotations

from munk.app import AppTarget

from .device import WebDevice


class WebDeviceRuntimeFactory:
    runtime_id = "web"
    supported_platforms = ("web",)

    def create_device(
        self,
        *,
        device_ref: str | None,
        app_target: AppTarget,
    ) -> WebDevice:
        return WebDevice(device_ref=device_ref, app_target=app_target)


def build_device_runtime_factory() -> WebDeviceRuntimeFactory:
    return WebDeviceRuntimeFactory()
