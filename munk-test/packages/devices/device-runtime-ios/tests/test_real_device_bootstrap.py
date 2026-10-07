from __future__ import annotations

import subprocess

import pytest
from munk.app import AppTarget, IOSAppIdentity
from munk_device_ios.bootstrap import _launch_real_device_wda, ensure_ios_wda_ready
from munk_device_ios.device import IOSDevice
from munk_device_ios.discovery import IOSDeviceDescriptor, resolve_ios_device_target


def build_app_target(**launch_context: str) -> AppTarget:
    return AppTarget(
        app_id="ios-app",
        platform="ios",
        ios=IOSAppIdentity(bundle_id="com.example.todo"),
        launch_context=launch_context,
    )


class _TrackingProvider:
    def __init__(self) -> None:
        self.closed = False

    def ensure_session(self) -> None:
        return None

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
        self.closed = True


class _TrackingTransport:
    def __init__(self, wda_url: str) -> None:
        self.wda_url = wda_url
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_ensure_ios_wda_ready_returns_bridge_metadata_for_real_devices() -> None:
    target = resolve_ios_device_target(
        device_ref="real-1-udid",
        descriptors=[
            IOSDeviceDescriptor(
                platform="ios",
                device_ref="real-1-udid",
                udid="real-1-udid",
                coredevice_identifier="real-1",
                display_name="Zhutao iPhone",
                kind="real_device",
                availability="available",
            )
        ],
        default_wda_url=None,
    )

    class _FakeBridgeManager:
        def create_session(
            self,
            *,
            device_udid: str,
            bundle_id: str,
            wda_bundle_id: str,
            platform_version: str | None,
            diagnostics=None,  # noqa: ANN001
        ):
            assert device_udid == "real-1-udid"
            assert bundle_id == "com.example.todo"
            assert wda_bundle_id == "sh.munk.wda.xctrunner"
            assert platform_version is None
            assert diagnostics is None
            return type(
                "_BridgeSession",
                (),
                {
                    "base_url": "http://127.0.0.1:16910",
                    "session_id": "bridge-session-1",
                    "backend_kind": "appium_ios_device",
                },
            )()

    import munk_device_ios.bootstrap as bootstrap_module

    original = bootstrap_module.get_default_ios_device_bridge_manager
    bootstrap_module.get_default_ios_device_bridge_manager = lambda: _FakeBridgeManager()
    try:
        result = ensure_ios_wda_ready(
            target=target,
            app_target=build_app_target(),
            command_runner=lambda command: "launched",
            status_checker=lambda url: False,
            sleep_fn=lambda _: None,
        )
    finally:
        bootstrap_module.get_default_ios_device_bridge_manager = original

    assert result.provider_kind == "bridge"
    assert result.bridge_base_url == "http://127.0.0.1:16910"
    assert result.bridge_session_id == "bridge-session-1"
    assert result.bridge_backend_kind == "appium_ios_device"


def test_ios_device_close_closes_transport() -> None:
    provider = _TrackingProvider()
    transport = _TrackingTransport("http://127.0.0.1:9100")

    device = IOSDevice(
        device_ref="real-1",
        app_target=build_app_target(wda_url="http://127.0.0.1:9100"),
        provider=provider,
        transport=transport,
    )
    device.close()

    assert provider.closed is True
    assert transport.closed is True


def test_launch_real_device_wda_includes_stdout_and_stderr_in_error_message(monkeypatch: pytest.MonkeyPatch) -> None:
    target = resolve_ios_device_target(
        device_ref="real-1-udid",
        descriptors=[
            IOSDeviceDescriptor(
                platform="ios",
                device_ref="real-1-udid",
                udid="real-1-udid",
                coredevice_identifier="real-1",
                display_name="Zhutao iPhone",
                kind="real_device",
                availability="available",
            )
        ],
        default_wda_url=None,
    )

    def _raise_called_process_error(*_unused_args: object, **_unused_kwargs: object) -> None:
        raise subprocess.CalledProcessError(
            1,
            ["xcrun", "devicectl"],
            output="launch stdout",
            stderr="launch stderr",
        )

    monkeypatch.setattr(subprocess, "run", _raise_called_process_error)

    with pytest.raises(RuntimeError) as exc_info:
        _launch_real_device_wda(target=target, bundle_id="com.facebook.WebDriverAgentRunner.xctrunner", command_runner=None)

    assert "stdout=launch stdout" in str(exc_info.value)
    assert "stderr=launch stderr" in str(exc_info.value)
