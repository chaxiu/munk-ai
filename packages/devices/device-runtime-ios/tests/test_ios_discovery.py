from __future__ import annotations

import json
from typing import Any

from munk.app import AppTarget, IOSAppIdentity
from munk_device_ios.bootstrap import ensure_simulator_wda_ready
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
    devicectl_payload: dict[str, Any] = {
        "result": {
            "devices": [
                {
                    "identifier": "real-1",
                    "deviceProperties": {"name": "Zhutao iPhone"},
                    "connectionProperties": {"state": "connected"},
                }
            ]
        }
    }

    def runner(command: list[str]) -> str:
        calls.append(command)
        if command[:3] == ["xcrun", "simctl", "list"]:
            return json.dumps(simctl_payload)
        if command[:3] == ["xcrun", "devicectl", "list"]:
            return json.dumps(devicectl_payload)
        if command[:3] == ["xcrun", "simctl", "launch"]:
            return "launched"
        raise AssertionError(f"unexpected command: {command}")

    return calls, runner


def test_list_ios_devices_returns_mixed_sorted_descriptors() -> None:
    _, runner = _build_command_runner()

    devices = list_ios_devices(command_runner=runner)

    assert [device.device_ref for device in devices] == ["sim-booted", "real-1"]
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
    assert devices[1].kind == "real_device"
    assert devices[1].display_name == "Zhutao iPhone"


def test_resolve_ios_device_target_defaults_to_single_booted_simulator() -> None:
    _, runner = _build_command_runner()
    descriptors = list_ios_devices(command_runner=runner)

    resolved = resolve_ios_device_target(
        device_ref=None,
        descriptors=descriptors,
        default_wda_url="http://127.0.0.1:8100",
    )

    assert resolved.device_ref == "sim-booted"
    assert resolved.kind == "simulator"
    assert resolved.executable is True
    assert resolved.launch_endpoint == "http://127.0.0.1:8100"


def test_resolve_ios_device_target_marks_real_device_non_executable() -> None:
    _, runner = _build_command_runner()
    descriptors = list_ios_devices(command_runner=runner)

    resolved = resolve_ios_device_target(
        device_ref="real-1",
        descriptors=descriptors,
        default_wda_url="http://127.0.0.1:8100",
    )

    assert resolved.kind == "real_device"
    assert resolved.executable is False
    assert resolved.launch_endpoint is None


def test_ensure_simulator_wda_ready_launches_when_status_not_ready() -> None:
    calls, runner = _build_command_runner()
    target = resolve_ios_device_target(
        device_ref="sim-booted",
        descriptors=list_ios_devices(command_runner=runner),
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
    assert ["xcrun", "simctl", "launch", "sim-booted", "com.facebook.WebDriverAgentRunner.xctrunner"] in calls


def test_ensure_simulator_wda_ready_rejects_real_device() -> None:
    target = resolve_ios_device_target(
        device_ref="real-1",
        descriptors=[
            IOSDeviceDescriptor(
                platform="ios",
                device_ref="real-1",
                udid="real-1",
                display_name="Zhutao iPhone",
                kind="real_device",
                raw={},
            )
        ],
        default_wda_url=None,
    )

    try:
        ensure_simulator_wda_ready(target=target, app_target=build_app_target())
    except NotImplementedError as exc:
        assert "Phase 3" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected real device bootstrap to be deferred")


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

    def swipe(self, *, start_x: int, start_y: int, end_x: int, end_y: int, duration_sec: float | None = None) -> None:
        _ = start_x, start_y, end_x, end_y, duration_sec
        raise AssertionError("not used")

    def type_text(self, text: str) -> None:
        _ = text
        raise AssertionError("not used")

    def clear_text(self) -> None:
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
        bootstrapper=lambda *, target, app_target, command_runner=None: bootstrap_calls.append(
            (target.device_ref, app_target.entry_identity or "")
        )
        or "http://127.0.0.1:8200",
        provider_factory=lambda _: provider,
    )

    device = factory.create_device(device_ref=None, app_target=build_app_target())

    assert bootstrap_calls == [("sim-booted", "com.example.todo")]
    assert device.provider is provider
    assert device._device_ref == "sim-booted"
    assert provider.ensure_session_calls == 1
