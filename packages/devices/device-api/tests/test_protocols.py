from __future__ import annotations

from munk.device import (
    CurrentAppState,
    DeviceDescriptor,
    DeviceDriver,
    DeviceInfo,
    ResolvedDeviceTarget,
    RuntimeLogEntry,
    SupportsAppInstall,
    SupportsDeviceDiscovery,
    SupportsDeviceLockState,
    SupportsDeviceUnlock,
    SupportsRuntimeLogs,
)
from munk.perception import ObservationTree


class FakeDeviceDriver:
    def screenshot_bgr(self):  # noqa: ANN202
        return None

    def click(self, x: int, y: int) -> None:
        del x, y

    def long_press(self, x: int, y: int, duration: float | None = None) -> None:
        del x, y, duration

    def scroll(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
    ) -> None:
        del start, end, duration

    def press(self, key: str) -> None:
        del key

    def input_text(self, text: str) -> None:
        del text

    def app_current(self) -> CurrentAppState:
        return CurrentAppState(
            platform="android",
            entry_identity="com.test.app",
            activity_name=".MainActivity",
        )

    def window_size(self) -> tuple[int, int]:
        return (1080, 2400)

    def capture_observation_tree(self) -> ObservationTree | None:
        return ObservationTree(
            source_type="android_uixml",
            content_type="xml",
            payload="<hierarchy />",
        )

    def clear_text(self) -> None:
        return None

    def dismiss_soft_keyboard(self) -> None:
        return None

    def is_soft_keyboard_visible(self) -> bool | None:
        return False

    def get_soft_keyboard_bounds(self) -> tuple[int, int, int, int] | None:
        return (0, 1800, 1080, 2400)

    def app_start(self, package: str) -> None:
        del package

    def app_stop(self, package: str) -> None:
        del package

    def app_install(self, artifact_path: str) -> None:
        del artifact_path

    def unlock(self) -> None:
        return None

    def is_locked(self) -> bool | None:
        return False

    def start_log_session(self) -> None:
        return None

    def drain_runtime_logs(self) -> list[RuntimeLogEntry]:
        return [
            RuntimeLogEntry(
                timestamp_ms=1710000000000,
                level="error",
                source="android_logcat",
                message="boom",
            )
        ]

    def stop_log_session(self) -> None:
        return None


class FakeDiscoveryFactory:
    def list_device_descriptors(self) -> list[DeviceDescriptor]:
        return [
            DeviceDescriptor(
                platform="ios",
                device_ref="sim-1",
                display_name="iPhone 16",
                kind="simulator",
                is_booted=True,
            )
        ]


def test_device_info_fields_are_stable() -> None:
    info = DeviceInfo(width=1080, height=2400, platform="android", device_ref="emulator-5554")

    assert info.width == 1080
    assert info.height == 2400
    assert info.platform == "android"
    assert info.device_ref == "emulator-5554"


def test_device_driver_protocol_covers_required_capabilities() -> None:
    assert isinstance(FakeDeviceDriver(), DeviceDriver)


def test_runtime_log_entry_fields_are_stable() -> None:
    entry = RuntimeLogEntry(
        timestamp_ms=1710000000000,
        level="error",
        source="web_console",
        message="console exploded",
        step_index=2,
        target_identity="https://example.com",
        surface_identity="https://example.com/app",
        raw={"type": "error"},
    )

    assert entry.level == "error"
    assert entry.source == "web_console"
    assert entry.message == "console exploded"
    assert entry.step_index == 2
    assert entry.raw["type"] == "error"


def test_runtime_logs_protocol_is_runtime_checkable() -> None:
    assert isinstance(FakeDeviceDriver(), SupportsRuntimeLogs)


def test_app_install_protocol_is_runtime_checkable() -> None:
    assert isinstance(FakeDeviceDriver(), SupportsAppInstall)


def test_device_unlock_protocols_are_runtime_checkable() -> None:
    fake = FakeDeviceDriver()

    assert isinstance(fake, SupportsDeviceUnlock)
    assert isinstance(fake, SupportsDeviceLockState)


def test_device_discovery_protocol_is_runtime_checkable() -> None:
    assert isinstance(FakeDiscoveryFactory(), SupportsDeviceDiscovery)


def test_device_descriptor_fields_are_stable() -> None:
    descriptor = DeviceDescriptor(
        platform="ios",
        device_ref="sim-1",
        display_name="iPhone 16",
        kind="simulator",
        availability="available",
        is_booted=True,
        raw={"runtime": "iOS 18.5"},
    )

    assert descriptor.platform == "ios"
    assert descriptor.device_ref == "sim-1"
    assert descriptor.display_name == "iPhone 16"
    assert descriptor.kind == "simulator"
    assert descriptor.is_booted is True
    assert descriptor.raw["runtime"] == "iOS 18.5"


def test_resolved_device_target_fields_are_stable() -> None:
    target = ResolvedDeviceTarget(
        platform="ios",
        device_ref="sim-1",
        display_name="iPhone 16",
        kind="simulator",
        executable=True,
        launch_endpoint="http://127.0.0.1:8100",
        raw={"booted": True},
    )

    assert target.platform == "ios"
    assert target.device_ref == "sim-1"
    assert target.display_name == "iPhone 16"
    assert target.executable is True
    assert target.launch_endpoint == "http://127.0.0.1:8100"
    assert target.raw["booted"] is True
