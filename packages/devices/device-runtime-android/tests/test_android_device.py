from __future__ import annotations

import os
from typing import cast

import pytest
from munk.app import AndroidAppIdentity, AppTarget
from munk.device import (
    CurrentAppState,
    DeviceDriver,
    DeviceInfo,
    SupportsAppInstall,
    SupportsClose,
    SupportsRuntimeLogs,
)
from munk_device_android import AndroidDevice


class FakeU2Device:
    def __init__(self) -> None:
        self.swipe_calls: list[tuple[int, int, int, int] | tuple[int, int, int, int, float]] = []
        self.dump_xml = "  <hierarchy><node bounds='[0,0][10,10]'/></hierarchy>  "
        self.app_starts: list[tuple[str, bool]] = []
        self.app_stops: list[str] = []
        self.push_calls: list[tuple[str, str]] = []
        self.clear_text_calls = 0
        self.press_calls: list[str] = []
        self.current = {"package": "com.test.app", "activity": ".MainActivity"}
        self.info = {"displayWidth": 0, "displayHeight": 0, "serial": None}
        self.shell_calls: list[object] = []
        self.shell_response: object = ("", 0)
        self.shell_responses: dict[tuple[str, ...], object] = {}
        self.send_keys_calls: list[tuple[str, bool]] = []
        self.fastinput_enabled: list[bool] = []
        self.current_ime_value = "com.android.inputmethod.latin/.LatinIME"
        self.send_keys_error: Exception | None = None
        self.fastinput_error: Exception | None = None
        self.long_click_calls: list[tuple[int, int, float]] = []
        self.unlock_calls = 0
        self.screen_on_calls = 0

    def swipe(self, *args):  # noqa: ANN002, ANN003
        self.swipe_calls.append(args)

    def dump_hierarchy(self) -> str:
        return self.dump_xml

    def app_start(self, package: str, wait: bool = True) -> None:
        self.app_starts.append((package, wait))

    def app_stop(self, package: str) -> None:
        self.app_stops.append(package)

    def push(self, src: str, dst: str) -> None:
        self.push_calls.append((src, dst))

    def clear_text(self) -> None:
        self.clear_text_calls += 1

    def press(self, key: str) -> None:
        self.press_calls.append(key)

    def app_current(self) -> dict[str, str]:
        return dict(self.current)

    def shell(self, command):  # noqa: ANN001
        self.shell_calls.append(command)
        if command[:2] == ["ime", "set"] and len(command) == 3:
            self.current_ime_value = str(command[2])
        response = self.shell_responses.get(tuple(command))
        if response is not None:
            return response
        return self.shell_response

    def send_keys(self, text: str, clear: bool = False) -> None:
        self.send_keys_calls.append((text, clear))
        if self.send_keys_error is not None:
            raise self.send_keys_error

    def set_fastinput_ime(self, enable: bool = True) -> None:
        self.fastinput_enabled.append(enable)
        if self.fastinput_error is not None:
            raise self.fastinput_error
        if enable:
            self.current_ime_value = "com.github.uiautomator/.FastInputIME"

    def wait_fastinput_ime(self) -> None:
        return None

    def current_ime(self) -> str:
        return self.current_ime_value

    def click(self, x: int, y: int) -> None:
        del x, y

    def long_click(self, x: int, y: int, duration: float) -> None:
        self.long_click_calls.append((x, y, duration))

    def unlock(self) -> None:
        self.unlock_calls += 1

    def screen_on(self) -> None:
        self.screen_on_calls += 1

    def screenshot(self, *, format: str):  # noqa: A002, ANN001, ANN202
        del format
        return None

    def window_size(self) -> tuple[int, int]:
        return (1080, 2400)


def build_app_target() -> AppTarget:
    return AppTarget(
        app_id="demo-app",
        platform="android",
        android=AndroidAppIdentity(package_name="com.test.app", activity_name=".MainActivity"),
    )


def test_android_device_scroll_passes_seconds_duration_to_uiautomator2() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.scroll((10, 20), (30, 40), duration=1.5)

    assert fake.swipe_calls == [(10, 20, 30, 40, 1.5)]


def test_android_device_long_press_prefers_uiautomator2_long_click() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.long_press(10, 20, duration=1.25)

    assert fake.long_click_calls == [(10, 20, 1.25)]
    assert fake.swipe_calls == []


def test_android_device_unlock_prefers_uiautomator2_unlock_when_locked() -> None:
    class UnlockingFakeU2Device(FakeU2Device):
        def unlock(self) -> None:
            super().unlock()
            self.info["screenOn"] = True
            self.shell_responses[("dumpsys", "window", "policy")] = ("mShowingLockscreen=false", 0)

    fake = UnlockingFakeU2Device()
    fake.info["screenOn"] = False
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.unlock()

    assert fake.unlock_calls == 1
    assert fake.swipe_calls == []


def test_android_device_unlock_falls_back_to_vertical_swipe_when_u2_unlock_does_not_clear_lock() -> None:
    fake = FakeU2Device()
    fake.info["screenOn"] = False
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.unlock()

    assert fake.unlock_calls == 1
    assert fake.screen_on_calls == 2
    assert fake.swipe_calls == [(540, 1968, 540, 432, 0.2), (540, 1968, 540, 432, 0.2)]


def test_android_device_unlock_skips_when_device_is_not_locked() -> None:
    fake = FakeU2Device()
    fake.info["screenOn"] = True
    fake.shell_responses[("dumpsys", "window", "policy")] = ("mShowingLockscreen=false", 0)
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.unlock()

    assert fake.unlock_calls == 0
    assert fake.swipe_calls == []


def test_android_device_is_locked_uses_screen_and_window_policy() -> None:
    fake = FakeU2Device()
    fake.info["screenOn"] = True
    fake.shell_responses[("dumpsys", "window", "policy")] = ("isStatusBarKeyguard=true", 0)
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    assert device.is_locked() is True


def test_android_device_scroll_uses_device_default_when_duration_is_none() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.scroll((1, 2), (3, 4), duration=None)

    assert fake.swipe_calls == [(1, 2, 3, 4)]


def test_android_device_capture_observation_tree_returns_android_tree() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    result = device.capture_observation_tree()

    assert result is not None
    assert result.source_type == "android_uixml"
    assert result.payload == "<hierarchy><node bounds='[0,0][10,10]'/></hierarchy>"


def test_android_device_app_stop_delegates_to_uiautomator2() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.app_stop("com.test.app")

    assert fake.app_stops == ["com.test.app"]


def test_android_device_app_install_pushes_to_device_tmp_then_installs_and_cleans_up() -> None:
    fake = FakeU2Device()
    fake.shell_response = ("Success\n", 0)
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.app_install("/tmp/demo.apk")

    assert fake.push_calls == [("/tmp/demo.apk", fake.push_calls[0][1])]
    assert fake.push_calls[0][1].startswith("/data/local/tmp/munk-install-")
    assert fake.push_calls[0][1].endswith(".apk")
    assert fake.shell_calls == [
        ["pm", "install", "-r", fake.push_calls[0][1]],
        ["rm", "-f", fake.push_calls[0][1]],
    ]


def test_android_device_app_install_raises_on_failure_output() -> None:
    fake = FakeU2Device()
    fake.shell_response = ("Failure [INSTALL_FAILED_VERSION_DOWNGRADE]\n", 1)
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="android app install failed"):
        device.app_install("/tmp/demo.apk")

    assert fake.shell_calls[-1] == ["rm", "-f", fake.push_calls[0][1]]


def test_android_device_clear_text_delegates_to_uiautomator2() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.clear_text()

    assert fake.clear_text_calls == 1


def test_android_device_input_text_prefers_uiautomator2_ime_for_unicode() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.input_text("你好啊")

    assert fake.fastinput_enabled == [True]
    assert fake.send_keys_calls == [("你好啊", False)]
    assert ["input", "text", "你好啊"] not in fake.shell_calls
    assert fake.shell_calls[-1] == ["ime", "set", "com.android.inputmethod.latin/.LatinIME"]


def test_android_device_input_text_falls_back_to_adb_for_ascii_when_fastinput_unavailable() -> None:
    fake = FakeU2Device()
    fake.fastinput_error = RuntimeError("FastInputIME unavailable")
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.input_text("hello world")

    assert fake.send_keys_calls == []
    assert fake.shell_calls[-1] == ["input", "text", "hello%sworld"]


def test_android_device_input_text_raises_for_unicode_when_fastinput_unavailable() -> None:
    fake = FakeU2Device()
    fake.fastinput_error = RuntimeError("FastInputIME unavailable")
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    with pytest.raises(RuntimeError, match="android unicode input requires automation IME"):
        device.input_text("你好啊")

    assert fake.send_keys_calls == []
    assert all(command != ["input", "text", "你好啊"] for command in fake.shell_calls)


def test_android_device_input_text_restores_previous_ime_after_send_keys_failure() -> None:
    fake = FakeU2Device()
    fake.send_keys_error = RuntimeError("send_keys failed")
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.input_text("hello")

    assert fake.send_keys_calls == [("hello", False)]
    assert fake.shell_calls[-2:] == [
        ["ime", "set", "com.android.inputmethod.latin/.LatinIME"],
        ["input", "text", "hello"],
    ]


def test_android_device_app_current_returns_structured_state() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    assert device.app_current() == CurrentAppState(
        platform="android",
        entry_identity="com.test.app",
        activity_name=".MainActivity",
        raw={"package": "com.test.app", "activity": ".MainActivity"},
        surface_identity="com.test.app/.MainActivity",
    )


def test_android_device_app_current_falls_back_to_package_when_activity_is_missing() -> None:
    fake = FakeU2Device()
    fake.current = {"package": "com.test.app"}
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    assert device.app_current() == CurrentAppState(
        platform="android",
        entry_identity="com.test.app",
        activity_name=None,
        raw={"package": "com.test.app"},
        surface_identity="com.test.app",
    )


def test_android_device_dismiss_soft_keyboard_uses_back_press() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.dismiss_soft_keyboard()

    assert fake.press_calls == ["back"]


def test_android_device_soft_keyboard_visibility_reads_dumpsys() -> None:
    fake = FakeU2Device()
    fake.shell_response = ("mShowRequested=true mInputShown=true", 0)
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    assert device.is_soft_keyboard_visible() is True
    assert fake.shell_calls == [["dumpsys", "input_method"]]


def test_android_device_soft_keyboard_visibility_returns_false_when_hidden() -> None:
    fake = FakeU2Device()
    fake.shell_response = ("mShowRequested=false mInputShown=false", 0)
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    assert device.is_soft_keyboard_visible() is False


def test_android_device_keyboard_bounds_reads_sk_region_output() -> None:
    fake = FakeU2Device()

    def shell(command):  # noqa: ANN001
        fake.shell_calls.append(command)
        if command == ["dumpsys", "input_method"]:
            return ("mInputShown=true", 0)
        if command == ["dumpsys", "window", "windows"]:
            return (
                """
                Window #7 Window{82dd42b u0 InputMethod}:
                  mOwnerUid=10186 package=com.google.android.inputmethod.latin
                  mAttrs={(0,0)(fillxfill) ty=INPUT_METHOD fmt=TRANSPARENT}
                  mBaseLayer=151000
                  mViewVisibility=0x0
                  mGivenContentInsets=[0,1613][0,0] mGivenVisibleInsets=[0,1613][0,0]
                  mTouchableInsets=3 mGivenInsetsPending=false
                  touchable region=SkRegion((0,1784,1440,2960))
                  mFrame=[0,171][1440,2960]
                Window #8 Window{next u0 com.demo/.MainActivity}:
                  mFrame=[0,0][1440,2960]
                """,
                0,
            )
        return ("", 0)

    fake.shell = shell  # type: ignore[method-assign]
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    assert device.get_soft_keyboard_bounds() == (0, 1784, 1440, 2960)


def test_android_device_info_uses_shared_device_info() -> None:
    fake = FakeU2Device()
    fake.current = {"package": "com.test.app", "activity": ".MainActivity"}
    fake.info = {"displayWidth": 1080, "displayHeight": 2400, "serial": "emulator-5554"}
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    info = device.info()

    assert info == DeviceInfo(width=1080, height=2400, platform="android", device_ref="emulator-5554")


def test_android_device_satisfies_device_driver_protocol() -> None:
    fake = FakeU2Device()
    fake.info = {"displayWidth": 1080, "displayHeight": 2400, "serial": "emulator-5554"}
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    assert isinstance(cast(object, device), DeviceDriver)
    assert isinstance(cast(object, device), SupportsAppInstall)
    assert isinstance(cast(object, device), SupportsClose)
    assert isinstance(cast(object, device), SupportsRuntimeLogs)


def test_android_device_runtime_logs_use_pid_scoped_logcat() -> None:
    fake = FakeU2Device()
    fake.shell_responses[("pidof", "-s", "com.test.app")] = ("1234\n", 0)
    fake.shell_responses[("logcat", "-d", "-v", "threadtime", "--pid", "1234")] = (
        "\n".join(
            [
                "05-17 12:34:56.123  1234  1235 E TestTag: first boom",
                "05-17 12:34:57.123  1234  1235 W TestTag: careful",
            ]
        ),
        0,
    )
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.start_log_session()
    first = device.drain_runtime_logs()
    second = device.drain_runtime_logs()

    assert fake.shell_calls[0] == ["pidof", "-s", "com.test.app"]
    assert fake.shell_calls[1] == ["logcat", "-d", "-v", "threadtime", "--pid", "1234"]
    assert [entry.level for entry in first] == ["error", "warning"]
    assert [entry.message for entry in first] == ["first boom", "careful"]
    assert second == []


def test_android_device_runtime_logs_fall_back_to_package_filter_when_pid_missing() -> None:
    fake = FakeU2Device()
    fake.shell_responses[("pidof", "-s", "com.test.app")] = ("", 0)
    fake.shell_responses[("logcat", "-d", "-v", "threadtime")] = (
        "\n".join(
            [
                "05-17 12:34:56.123  4567  4568 E TestTag: com.test.app exploded",
                "05-17 12:34:57.123  4567  4568 W TestTag: unrelated noise",
            ]
        ),
        0,
    )
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.start_log_session()
    entries = device.drain_runtime_logs()

    assert fake.shell_calls[-1] == ["logcat", "-d", "-v", "threadtime"]
    assert [entry.message for entry in entries] == ["com.test.app exploded"]


def test_android_device_runtime_logs_return_empty_when_no_stable_filter_is_available() -> None:
    fake = FakeU2Device()
    app_target = AppTarget(app_id="demo-app", platform="android", android=AndroidAppIdentity(package_name=""))
    fake.current = {"package": ""}
    fake.shell_responses[("logcat", "-d", "-v", "threadtime")] = (
        "05-17 12:34:56.123  4567  4568 E TestTag: global boom",
        0,
    )
    device = AndroidDevice(fake, app_target=app_target)  # type: ignore[arg-type]

    device.start_log_session()

    assert device.drain_runtime_logs() == []


def test_android_device_close_clears_runtime_log_state() -> None:
    fake = FakeU2Device()
    fake.shell_responses[("pidof", "-s", "com.test.app")] = ("1234\n", 0)
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.start_log_session()
    device.close()

    assert device._log_package_name is None  # type: ignore[attr-defined]
    assert device._log_process_names == ()  # type: ignore[attr-defined]
    assert device._log_pid is None  # type: ignore[attr-defined]
    assert device._log_session_started is False  # type: ignore[attr-defined]
    assert device._seen_log_keys == set()  # type: ignore[attr-defined]


def test_android_device_close_is_idempotent() -> None:
    fake = FakeU2Device()
    device = AndroidDevice(fake, app_target=build_app_target())  # type: ignore[arg-type]

    device.close()
    device.close()

    assert device._log_package_name is None  # type: ignore[attr-defined]
    assert device._log_process_names == ()  # type: ignore[attr-defined]
    assert device._log_pid is None  # type: ignore[attr-defined]
    assert device._log_session_started is False  # type: ignore[attr-defined]
    assert device._seen_log_keys == set()  # type: ignore[attr-defined]


def test_android_device_connect_exports_munk_adb_path_to_adbutils(monkeypatch) -> None:  # noqa: ANN001
    fake = FakeU2Device()
    monkeypatch.setenv("MUNK_ADB_PATH", "/tmp/munk-adb")
    monkeypatch.delenv("ADBUTILS_ADB_PATH", raising=False)
    monkeypatch.setattr("munk_device_android.device.u2.connect", lambda serial=None: fake)

    device = AndroidDevice.connect("emulator-5554", app_target=build_app_target())

    assert os.environ["ADBUTILS_ADB_PATH"] == "/tmp/munk-adb"
    assert isinstance(device, AndroidDevice)
