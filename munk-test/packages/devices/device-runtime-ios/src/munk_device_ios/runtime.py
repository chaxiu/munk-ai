from __future__ import annotations

from typing import Callable, cast

from munk.app import AppTarget
from munk.device import DeviceDescriptor
from munk.services.ios import IOSDeviceBridgeDiagnosticsContext, get_default_ios_device_bridge_manager

from .bootstrap import IOSWDAReadyResult, ensure_ios_wda_ready
from .bridge_client import IOSBridgeClient, IOSBridgeSessionHandle
from .bridge_wda_provider import BridgeWDAProvider
from .device import IOSDevice
from .discovery import CommandRunner, SupportsIOSRealDeviceDiscovery, list_ios_devices, resolve_ios_device_target
from .http_wda_provider import HttpWDAProvider
from .wda_provider import WDAProvider

WDAProviderFactory = Callable[[IOSWDAReadyResult], WDAProvider]
Bootstrapper = Callable[..., IOSWDAReadyResult]


class IOSDeviceRuntimeFactory:
    runtime_id = "ios"
    supported_platforms = ("ios",)

    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        bridge_manager: SupportsIOSRealDeviceDiscovery | None = None,
        bootstrapper: Bootstrapper = ensure_ios_wda_ready,
        provider_factory: WDAProviderFactory | None = None,
    ) -> None:
        self._command_runner = command_runner
        self._bridge_manager = bridge_manager
        self._bootstrapper = bootstrapper
        self._provider_factory = provider_factory
        self._diagnostics_context: IOSDeviceBridgeDiagnosticsContext | None = None

    def list_device_descriptors(self) -> list[DeviceDescriptor]:
        return cast(
            list[DeviceDescriptor],
            list_ios_devices(command_runner=self._command_runner, bridge_manager=self._bridge_manager),
        )

    def create_device(
        self,
        *,
        device_ref: str | None,
        app_target: AppTarget,
    ) -> IOSDevice:
        descriptors = list_ios_devices(command_runner=self._command_runner, bridge_manager=self._bridge_manager)
        resolved = resolve_ios_device_target(
            device_ref=device_ref,
            descriptors=descriptors,
            default_wda_url=app_target.launch_context.get("wda_url"),
        )
        bootstrap_result = self._bootstrapper(
            target=resolved,
            app_target=app_target,
            command_runner=self._command_runner,
            diagnostics_context=self._diagnostics_context,
        )
        launch_context = dict(app_target.launch_context)
        if bootstrap_result.wda_url:
            launch_context["wda_url"] = bootstrap_result.wda_url
        resolved_app_target = app_target.model_copy(update={"launch_context": launch_context})
        provider = self._provider_factory(bootstrap_result) if self._provider_factory is not None else _build_provider(bootstrap_result)
        device = IOSDevice(
            device_ref=resolved.device_ref,
            device_kind=resolved.kind,
            app_target=resolved_app_target,
            provider=provider,
        )
        device.provider.ensure_session()
        return device

    def set_diagnostics_context(self, context: IOSDeviceBridgeDiagnosticsContext | None) -> None:
        self._diagnostics_context = context


def build_device_runtime_factory() -> IOSDeviceRuntimeFactory:
    return IOSDeviceRuntimeFactory(bridge_manager=get_default_ios_device_bridge_manager())


def _build_provider(bootstrap_result: IOSWDAReadyResult) -> WDAProvider:
    if bootstrap_result.provider_kind == "bridge":
        if bootstrap_result.bridge_base_url is None or bootstrap_result.bridge_session_id is None:
            raise RuntimeError("bridge bootstrap result is missing bridge session details")
        return BridgeWDAProvider(
            client=IOSBridgeClient(
                session=IOSBridgeSessionHandle(
                    base_url=bootstrap_result.bridge_base_url,
                    session_id=bootstrap_result.bridge_session_id,
                    backend_kind=bootstrap_result.bridge_backend_kind or "unknown",
                    device_udid="unknown",
                ),
                on_close=lambda session_id: get_default_ios_device_bridge_manager().delete_session(session_id=session_id),
            )
        )
    if bootstrap_result.wda_url is None:
        raise RuntimeError("http bootstrap result is missing wda_url")
    return HttpWDAProvider(base_url=bootstrap_result.wda_url)
