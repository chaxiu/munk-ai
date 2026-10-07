from __future__ import annotations

import json
from typing import Any, cast

from munk.app import AppTarget, IOSAppIdentity
from munk.services.ios import IOSBridgeRealDevice
from munk_device_ios.bootstrap import IOSWDAReadyResult, ensure_ios_wda_ready, ensure_simulator_wda_ready
from munk_device_ios.discovery import CommandRunner, IOSDeviceDescriptor, list_ios_devices, resolve_ios_device_target
from munk_device_ios.runtime import IOSDeviceRuntimeFactory


def build_app_target(**launch_context: str) -> AppTarget:
    return AppTarget(
        app_id="ios-app",
        platform="ios",
        ios=IOSAppIdentity(bundle_id="com.example.todo"),
        launch_context=launch_context,
    )


def _build_command_runner() -> tuple[list[list[str]], CommandRunner]:
    calls: list[list[str]] = []
    simctl_payload: dict[str, Any] = {
        "devices": {
            "com.apple.CoreSimulator.SimRuntime.iOS-18-5": [
                {
                    "name": "iPhone 16",
                    "udid": "sim-booted",
                    "state": "Booted",
                    "isAvailable": True,
                },
                {
                    "name": "iPhone 15",
                    "udid": "sim-shutdown",
                    "state": "Shutdown",
                    "isAvailable": True,
                },
            ]
        }
    }
    def runner(command: list[str]) -> str:
        calls.append(command)
        if command[:3] == ["xcrun", "simctl", "list"]:
            return json.dumps(simctl_payload)
        if command[:3] == ["xcrun", "simctl", "launch"]:
            return "launched"
        if command[:5] == ["xcrun", "devicectl", "device", "process", "launch"]:
            return "launched"
        raise AssertionError(f"unexpected command: {command}")

    return calls, runner


class _FakeDiscoveryBridgeManager:
    def __init__(self) -> None:
        self.calls = 0
        self.devices = [
            IOSBridgeRealDevice(
                udid="real-1-udid",
                name="Zhutao iPhone",
                platform_version="18.6.2",
                state="connected",
                backend_kind="appium_ios_remotexpc",
                raw={
                    "identifier": "real-1",
                    "connectionProperties": {"state": "connected"},
                    "platform_version": "18.6.2",
                },
            ),
            IOSBridgeRealDevice(
                udid="real-stale-udid",
                name="Old iPhone",
                platform_version=None,
                state="unavailable",
                backend_kind="appium_ios_device",
                raw={
                    "identifier": "real-stale",
                    "connectionProperties": {"tunnelState": "unavailable"},
                },
            ),
        ]

    def list_real_devices(self) -> list[IOSBridgeRealDevice]:
        self.calls += 1
        return list(self.devices)


def test_list_ios_devices_returns_mixed_sorted_descriptors() -> None:
    _, runner = _build_command_runner()
    bridge_manager = _FakeDiscoveryBridgeManager()

    devices = list_ios_devices(command_runner=runner, bridge_manager=bridge_manager)

    assert [device.device_ref for device in devices] == ["sim-booted", "sim-shutdown", "real-1-udid"]
    assert devices[0] == IOSDeviceDescriptor(
        platform="ios",
        device_ref="sim-booted",
        udid="sim-booted",
        display_name="iPhone 16",
        kind="simulator",
        availability="available",
        is_booted=True,
        state="Booted",
        runtime="com.apple.CoreSimulator.SimRuntime.iOS-18-5",
        raw={"runtime": "com.apple.CoreSimulator.SimRuntime.iOS-18-5", "availability_error": None},
    )
    assert devices[1] == IOSDeviceDescriptor(
        platform="ios",
        device_ref="sim-shutdown",
        udid="sim-shutdown",
        display_name="iPhone 15",
        kind="simulator",
        availability="available",
        is_booted=False,
        state="Shutdown",
        runtime="com.apple.CoreSimulator.SimRuntime.iOS-18-5",
        raw={"runtime": "com.apple.CoreSimulator.SimRuntime.iOS-18-5", "availability_error": None},
    )
    assert devices[2] == IOSDeviceDescriptor(
        platform="ios",
        device_ref="real-1-udid",
        udid="real-1-udid",
        coredevice_identifier="real-1",
        display_name="Zhutao iPhone",
        kind="real_device",
        availability="available",
        is_booted=True,
        state="connected",
        runtime=None,
        raw={
            "identifier": "real-1",
            "connectionProperties": {"state": "connected"},
            "platform_version": "18.6.2",
            "real_device_udid": "real-1-udid",
            "bridge_backend_kind": "appium_ios_remotexpc",
            "bridge_visible": True,
        },
    )
    assert bridge_manager.calls == 1


def test_list_ios_devices_filters_stale_real_devices_from_devicectl() -> None:
    _, runner = _build_command_runner()
    bridge_manager = _FakeDiscoveryBridgeManager()

    devices = list_ios_devices(command_runner=runner, bridge_manager=bridge_manager)

    assert all(device.device_ref != "real-stale-udid" for device in devices)


def test_resolve_ios_device_target_defaults_to_single_booted_simulator() -> None:
    _, runner = _build_command_runner()
    descriptors = list_ios_devices(command_runner=runner, bridge_manager=_FakeDiscoveryBridgeManager())

    resolved = resolve_ios_device_target(
        device_ref=None,
        descriptors=descriptors,
        default_wda_url="http://127.0.0.1:8100",
    )

    assert resolved.device_ref == "sim-booted"
    assert resolved.kind == "simulator"
    assert resolved.executable is True
    assert resolved.launch_endpoint == "http://127.0.0.1:8100"


def test_resolve_ios_device_target_marks_real_device_executable() -> None:
    _, runner = _build_command_runner()
    descriptors = list_ios_devices(command_runner=runner, bridge_manager=_FakeDiscoveryBridgeManager())

    resolved = resolve_ios_device_target(
        device_ref="real-1-udid",
        descriptors=descriptors,
        default_wda_url="http://127.0.0.1:8100",
    )

    assert resolved.kind == "real_device"
    assert resolved.executable is True
    assert resolved.launch_endpoint == "http://127.0.0.1:8100"
    assert resolved.udid == "real-1-udid"
    assert resolved.coredevice_identifier == "real-1"


def test_ensure_simulator_wda_ready_launches_when_status_not_ready() -> None:
    calls, runner = _build_command_runner()
    target = resolve_ios_device_target(
        device_ref="sim-booted",
        descriptors=list_ios_devices(command_runner=runner, bridge_manager=_FakeDiscoveryBridgeManager()),
        default_wda_url="http://127.0.0.1:8100",
    )
    statuses = iter([False, False, True])

    resolved = ensure_simulator_wda_ready(
        target=target,
        app_target=build_app_target(),
        command_runner=runner,
        status_checker=lambda url: next(statuses),
        sleep_fn=lambda _: None,
    )

    assert resolved == "http://127.0.0.1:8100"
    assert ["xcrun", "simctl", "launch", "sim-booted", "sh.munk.wda.xctrunner"] in calls


class _FakeBootstrapBridgeManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def create_session(
        self,
        *,
        device_udid: str,
        bundle_id: str,
        wda_bundle_id: str,
        platform_version: str | None,
        diagnostics=None,  # noqa: ANN001
    ):
        self.calls.append(
            {
                "device_udid": device_udid,
                "bundle_id": bundle_id,
                "wda_bundle_id": wda_bundle_id,
                "platform_version": platform_version,
                "diagnostics": diagnostics,
            }
        )
        return type(
            "_BridgeSession",
            (),
            {
                "base_url": "http://127.0.0.1:16910",
                "session_id": "bridge-session-1",
                "backend_kind": "appium_ios_remotexpc",
            },
        )()


def test_ensure_ios_wda_ready_launches_real_device_when_not_ready() -> None:
    calls, runner = _build_command_runner()
    target = resolve_ios_device_target(
        device_ref="real-1-udid",
        descriptors=list_ios_devices(command_runner=runner, bridge_manager=_FakeDiscoveryBridgeManager()),
        default_wda_url=None,
    )
    manager = _FakeBootstrapBridgeManager()
    import munk_device_ios.bootstrap as bootstrap_module

    original = bootstrap_module.get_default_ios_device_bridge_manager
    bootstrap_module.get_default_ios_device_bridge_manager = lambda: manager
    try:
        result = ensure_ios_wda_ready(
            target=target,
            app_target=build_app_target(),
            command_runner=runner,
            status_checker=lambda url: False,
            sleep_fn=lambda _: None,
        )
    finally:
        bootstrap_module.get_default_ios_device_bridge_manager = original

    assert result.provider_kind == "bridge"
    assert result.bridge_base_url == "http://127.0.0.1:16910"
    assert result.bridge_session_id == "bridge-session-1"
    assert result.bridge_backend_kind == "appium_ios_remotexpc"
    assert manager.calls == [
        {
            "device_udid": "real-1-udid",
            "bundle_id": "com.example.todo",
            "wda_bundle_id": "sh.munk.wda.xctrunner",
            "platform_version": "18.6.2",
            "diagnostics": None,
        }
    ]
    assert ["xcrun", "devicectl", "device", "process", "launch", "--device", "real-1-udid", "com.facebook.WebDriverAgentRunner.xctrunner"] not in calls


class _NoopProvider:
    def __init__(self) -> None:
        self.ensure_session_calls = 0

    def ensure_session(self) -> None:
        self.ensure_session_calls += 1

    def screenshot_png(self) -> bytes:
        raise AssertionError("not used")

    def tap(self, x: int, y: int) -> None:
        _ = x, y
        raise AssertionError("not used")

    def long_press(self, x: int, y: int, duration_sec: float | None = None) -> None:
        _ = x, y, duration_sec
        raise AssertionError("not used")

    def swipe(self, *, start_x: int, start_y: int, end_x: int, end_y: int, duration_sec: float | None = None) -> None:
        _ = start_x, start_y, end_x, end_y, duration_sec
        raise AssertionError("not used")

    def type_text(self, text: str) -> None:
        _ = text
        raise AssertionError("not used")

    def clear_text(self) -> None:
        raise AssertionError("not used")

    def find_element(self, using: str, value: str) -> str:
        _ = using, value
        raise AssertionError("not used")

    def click_element(self, element_id: str) -> None:
        _ = element_id
        raise AssertionError("not used")

    def clear_element(self, element_id: str) -> None:
        _ = element_id
        raise AssertionError("not used")

    def set_element_value(self, element_id: str, text: str) -> None:
        _ = element_id, text
        raise AssertionError("not used")

    def get_element_attribute(self, element_id: str, name: str) -> str | None:
        _ = element_id, name
        raise AssertionError("not used")

    def press(self, key: str) -> None:
        _ = key
        raise AssertionError("not used")

    def dismiss_soft_keyboard(self) -> None:
        raise AssertionError("not used")

    def current_app(self):
        raise AssertionError("not used")

    def window_size(self) -> tuple[int, int]:
        raise AssertionError("not used")

    def accessibility_tree(self):
        raise AssertionError("not used")

    def launch_app(self, bundle_id: str) -> None:
        _ = bundle_id
        raise AssertionError("not used")

    def terminate_app(self, bundle_id: str) -> None:
        _ = bundle_id
        raise AssertionError("not used")

    def close(self) -> None:
        return None


def test_runtime_factory_uses_discovery_and_bootstrap_before_device_creation() -> None:
    _, runner = _build_command_runner()
    provider = _NoopProvider()
    bootstrap_calls: list[tuple[str, str]] = []

    factory = IOSDeviceRuntimeFactory(
        command_runner=runner,
        bridge_manager=_FakeDiscoveryBridgeManager(),
        bootstrapper=lambda *, target, app_target, command_runner=None, diagnostics_context=None: IOSWDAReadyResult(
            wda_url=bootstrap_calls.append(
            (target.device_ref, app_target.entry_identity or "")
        )
        or "http://127.0.0.1:8200"
        ),
        provider_factory=cast(Any, lambda _: provider),
    )

    device = factory.create_device(device_ref=None, app_target=build_app_target())

    assert bootstrap_calls == [("sim-booted", "com.example.todo")]
    assert device.provider is provider
    assert device._device_ref == "sim-booted"
    assert provider.ensure_session_calls == 1
