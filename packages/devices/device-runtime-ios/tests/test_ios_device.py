from __future__ import annotations

import json
from typing import cast

import cv2
import numpy as np
from munk.app import AppTarget, IOSAppIdentity
from munk.device import (
    CurrentAppState,
    DeviceDriver,
    RuntimeLogEntry,
    SupportsAppLifecycle,
    SupportsClose,
    SupportsRuntimeLogs,
    SupportsSoftKeyboardBounds,
    SupportsSoftKeyboardDismiss,
    SupportsSoftKeyboardVisibility,
    SupportsTextClear,
)
from munk_device_ios import HttpWDAProvider, IOSDevice, WDAAccessibilityTree, WDAAppState


class FakeWDAProvider:
    def __init__(self) -> None:
        self.ensure_session_calls = 0
        self.close_calls = 0
        self.clear_calls = 0
        self.dismiss_keyboard_calls = 0
        self.tap_calls: list[tuple[int, int]] = []
        self.long_press_calls: list[tuple[int, int, float | None]] = []
        self.swipe_calls: list[tuple[int, int, int, int, float | None]] = []
        self.type_calls: list[str] = []
        self.press_calls: list[str] = []
        self.launch_calls: list[str] = []
        self.terminate_calls: list[str] = []
        self._window_size = (1179, 2556)
        self._app_state = WDAAppState(
            "com.example.demo",
            "com.example.demo",
            "Demo",
            {"bundleId": "com.example.demo", "name": "Demo"},
        )
        self._tree: WDAAccessibilityTree | None = WDAAccessibilityTree(
            payload={
                "value": {
                    "type": "XCUIElementTypeApplication",
                    "name": "Demo",
                    "children": [
                        {
                            "type": "XCUIElementTypeButton",
                            "name": "Continue",
                            "label": "Continue",
                            "rect": {"x": 10, "y": 20, "width": 100, "height": 44},
                            "enabled": True,
                        },
                        {
                            "type": "XCUIElementTypeKeyboard",
                            "nativeFrame": "{{0, 1900}, {1179, 656}}",
                        }
                    ],
                }
            }
        )

    def screenshot_png(self) -> bytes:
        image = np.zeros((2, 3, 3), dtype=np.uint8)
        image[:, :] = (1, 2, 3)
        ok, payload = cv2.imencode(".png", image)
        assert ok is True
        return payload.tobytes()

    def ensure_session(self) -> None:
        self.ensure_session_calls += 1

    def tap(self, x: int, y: int) -> None:
        self.tap_calls.append((x, y))

    def long_press(self, x: int, y: int, duration_sec: float | None = None) -> None:
        self.long_press_calls.append((x, y, duration_sec))

    def swipe(
        self,
        *,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_sec: float | None = None,
    ) -> None:
        self.swipe_calls.append((start_x, start_y, end_x, end_y, duration_sec))

    def type_text(self, text: str) -> None:
        self.type_calls.append(text)

    def clear_text(self) -> None:
        self.clear_calls += 1

    def press(self, key: str) -> None:
        self.press_calls.append(key)

    def dismiss_soft_keyboard(self) -> None:
        self.dismiss_keyboard_calls += 1

    def current_app(self) -> WDAAppState:
        return self._app_state

    def window_size(self) -> tuple[int, int]:
        return self._window_size

    def accessibility_tree(self) -> WDAAccessibilityTree | None:
        return self._tree

    def launch_app(self, bundle_id: str) -> None:
        self.launch_calls.append(bundle_id)

    def terminate_app(self, bundle_id: str) -> None:
        self.terminate_calls.append(bundle_id)

    def close(self) -> None:
        self.close_calls += 1


class FakeLogStream:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.entries: list[RuntimeLogEntry] = [
            RuntimeLogEntry(
                timestamp_ms=1710000000000,
                level="error",
                source="ios_syslog",
                message="Create todo failed",
            )
        ]

    def start(self) -> None:
        self.started += 1

    def drain(self) -> list[RuntimeLogEntry]:
        entries = list(self.entries)
        self.entries.clear()
        return entries

    def stop(self) -> None:
        self.stopped += 1


def build_app_target(**launch_context: str) -> AppTarget:
    return AppTarget(
        app_id="ios-app",
        platform="ios",
        ios=IOSAppIdentity(bundle_id="com.example.demo"),
        launch_context=launch_context,
    )


def test_ios_device_screenshot_bgr_decodes_png() -> None:
    device = IOSDevice(app_target=build_app_target(), provider=FakeWDAProvider())

    image = device.screenshot_bgr()

    assert tuple(int(v) for v in image[0, 0]) == (1, 2, 3)


def test_ios_device_click_scroll_input_and_press_delegate_to_provider() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    device.click(12, 34)
    device.scroll((10, 20), (100, 200), duration=0.5)
    device.input_text("hello ios")
    device.press("home")

    assert provider.tap_calls == [(12, 34)]
    assert provider.swipe_calls == [(10, 20, 100, 200, 0.5)]
    assert provider.type_calls == ["hello ios"]
    assert provider.press_calls == ["home"]


def test_ios_device_unlock_is_best_effort_and_uses_provider_session() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    device.unlock()

    assert provider.ensure_session_calls == 1
    assert device.is_locked() is None


def test_ios_device_long_press_delegates_to_provider() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    device.long_press(12, 34, duration=1.2)

    assert provider.long_press_calls == [(12, 34, 1.2)]


def test_ios_device_clear_text_delegates_to_provider() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    device.clear_text()

    assert provider.clear_calls == 1


def test_ios_device_app_current_returns_structured_state() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(device_ref="sim-1", app_target=build_app_target(), provider=provider)

    assert device.app_current() == CurrentAppState(
        platform="ios",
        entry_identity="com.example.demo",
        title="Demo",
        raw={"bundleId": "com.example.demo", "name": "Demo", "device_ref": "sim-1"},
        surface_identity="com.example.demo",
    )


def test_ios_device_window_size_delegates_to_provider() -> None:
    device = IOSDevice(app_target=build_app_target(), provider=FakeWDAProvider())

    assert device.window_size() == (1179, 2556)


def test_ios_device_capture_observation_tree_returns_ios_ax_tree() -> None:
    device = IOSDevice(app_target=build_app_target(), provider=FakeWDAProvider())

    result = device.capture_observation_tree()

    assert result is not None
    assert result.source_type == "ios_ax_tree"
    assert result.content_type == "json"
    payload = json.loads(result.payload)
    assert payload["value"]["children"][0]["name"] == "Continue"


def test_ios_device_reports_soft_keyboard_visibility_and_bounds() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    assert device.is_soft_keyboard_visible() is True
    assert device.get_soft_keyboard_bounds() == (0, 1900, 1179, 2556)


def test_ios_device_soft_keyboard_returns_none_when_tree_missing() -> None:
    provider = FakeWDAProvider()
    provider._tree = None
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    assert device.is_soft_keyboard_visible() is None
    assert device.get_soft_keyboard_bounds() is None


def test_ios_device_dismiss_soft_keyboard_delegates_to_provider() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    device.dismiss_soft_keyboard()

    assert provider.dismiss_keyboard_calls == 1


def test_ios_device_app_lifecycle_delegates_to_provider() -> None:
    provider = FakeWDAProvider()
    device = IOSDevice(app_target=build_app_target(), provider=provider)

    device.app_stop("com.example.demo")
    device.app_start("com.example.demo")

    assert provider.terminate_calls == ["com.example.demo"]
    assert provider.launch_calls == ["com.example.demo"]


def test_ios_device_satisfies_device_driver_protocol() -> None:
    device = IOSDevice(app_target=build_app_target(), provider=FakeWDAProvider())

    assert isinstance(cast(object, device), DeviceDriver)
    assert isinstance(cast(object, device), SupportsAppLifecycle)
    assert isinstance(cast(object, device), SupportsClose)
    assert isinstance(cast(object, device), SupportsTextClear)
    assert isinstance(cast(object, device), SupportsSoftKeyboardDismiss)
    assert isinstance(cast(object, device), SupportsSoftKeyboardVisibility)
    assert isinstance(cast(object, device), SupportsSoftKeyboardBounds)
    assert isinstance(cast(object, device), SupportsRuntimeLogs)


def test_ios_device_uses_http_wda_provider_by_default() -> None:
    device = IOSDevice(app_target=build_app_target(wda_url="http://127.0.0.1:8200"))

    assert isinstance(device.provider, HttpWDAProvider)


def test_ios_device_close_delegates_to_provider() -> None:
    provider = FakeWDAProvider()
    log_stream = FakeLogStream()
    device = IOSDevice(app_target=build_app_target(), provider=provider, log_stream=log_stream)

    device.close()

    assert provider.close_calls == 1
    assert log_stream.stopped == 1


def test_ios_device_runtime_logs_delegate_to_log_stream() -> None:
    provider = FakeWDAProvider()
    log_stream = FakeLogStream()
    device = IOSDevice(app_target=build_app_target(), provider=provider, log_stream=log_stream)

    device.start_log_session()
    entries = device.drain_runtime_logs()
    device.stop_log_session()

    assert log_stream.started == 1
    assert log_stream.stopped == 1
    assert [entry.source for entry in entries] == ["ios_syslog"]
