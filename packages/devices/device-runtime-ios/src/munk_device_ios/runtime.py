from __future__ import annotations

from typing import Callable, cast

from munk.app import AppTarget
from munk.device import DeviceDescriptor

from .bootstrap import ensure_simulator_wda_ready
from .device import IOSDevice
from .discovery import CommandRunner, list_ios_devices, resolve_ios_device_target
from .wda_provider import WDAProvider

WDAProviderFactory = Callable[[str], WDAProvider]
Bootstrapper = Callable[..., str]


class IOSDeviceRuntimeFactory:
    runtime_id = "ios"
    supported_platforms = ("ios",)

    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        bootstrapper: Bootstrapper = ensure_simulator_wda_ready,
        provider_factory: WDAProviderFactory | None = None,
    ) -> None:
        self._command_runner = command_runner
        self._bootstrapper = bootstrapper
        self._provider_factory = provider_factory

    def list_device_descriptors(self) -> list[DeviceDescriptor]:
        return cast(list[DeviceDescriptor], list_ios_devices(command_runner=self._command_runner))

    def create_device(
        self,
        *,
        device_ref: str | None,
        app_target: AppTarget,
    ) -> IOSDevice:
        descriptors = list_ios_devices(command_runner=self._command_runner)
        resolved = resolve_ios_device_target(
            device_ref=device_ref,
            descriptors=descriptors,
            default_wda_url=app_target.launch_context.get("wda_url"),
        )
        resolved_wda_url = self._bootstrapper(target=resolved, app_target=app_target, command_runner=self._command_runner)
        launch_context = dict(app_target.launch_context)
        launch_context["wda_url"] = resolved_wda_url
        resolved_app_target = app_target.model_copy(update={"launch_context": launch_context})
        provider = self._provider_factory(resolved_wda_url) if self._provider_factory is not None else None
        device = IOSDevice(device_ref=resolved.device_ref, app_target=resolved_app_target, provider=provider)
        device.provider.ensure_session()
        return device


def build_device_runtime_factory() -> IOSDeviceRuntimeFactory:
    return IOSDeviceRuntimeFactory()
