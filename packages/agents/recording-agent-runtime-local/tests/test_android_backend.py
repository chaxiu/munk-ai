from __future__ import annotations

import numpy as np
from munk.device import CurrentAppState
from munk.perception import ObservationTree
from munk_recording_local.android_backend import AndroidRecordingBackend


class FakeDevice:
    def __init__(self) -> None:
        self.info = {
            "displayWidth": 1080,
            "displayHeight": 1920,
            "serial": "SER123",
        }

    def screenshot(self, *, format: str):
        assert format == "opencv"
        return np.zeros((8, 6, 3), dtype=np.uint8)

    def app_current(self):
        return {
            "package": "com.demo.app",
            "activity": ".MainActivity",
        }

    def window_size(self):
        return (1080, 1920)

    def dump_hierarchy(self):
        return "  <hierarchy />  "

    def app_start(self, package: str, wait: bool = True) -> None:
        self.started_package = package

    def app_stop(self, package: str) -> None:
        self.stopped_package = package

    def click(self, x: int, y: int) -> None:
        self.clicked = (x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float | None = None) -> None:
        self.swiped = (x1, y1, x2, y2, duration)

    def press(self, key: str) -> None:
        self.pressed = key

    def shell(self, command):
        if command == ["dumpsys", "input_method"]:
            return "mInputShown=true"
        if command == ["dumpsys", "window", "windows"]:
            return """
            Window #12 Window{abc u0 InputMethod}:
              mWindowFrames=[0,1400][1080,1920]
              frame=Rect(0, 1400 - 1080, 1920)
            """
        self.shell_command = command
        return ""

    def clear_text(self) -> None:
        self.cleared = True


def test_connect_uses_uiautomator_device(monkeypatch) -> None:
    fake_device = FakeDevice()
    monkeypatch.setattr(
        "munk_recording_local.android_backend.AndroidDevice.connect",
        lambda device_ref=None, *, app_target=None: AndroidRecordingBackend(fake_device, app_target=app_target),
    )

    backend = AndroidRecordingBackend.connect(device_ref="SER123")

    assert backend.info().device_ref == "SER123"
    assert backend.window_size() == (1080, 1920)
    assert backend.capture_observation_tree() == ObservationTree(
        source_type="android_uixml",
        content_type="xml",
        payload="<hierarchy />",
    )


def test_backend_reads_screenshot_and_state() -> None:
    backend = AndroidRecordingBackend(FakeDevice())

    image = backend.screenshot_bgr()

    assert image.shape == (8, 6, 3)
    assert backend.app_current() == CurrentAppState(
        platform="android",
        entry_identity="com.demo.app",
        activity_name=".MainActivity",
        surface_identity="com.demo.app/.MainActivity",
        raw={"package": "com.demo.app", "activity": ".MainActivity"},
    )
    assert backend.is_soft_keyboard_visible() is True
    assert backend.get_soft_keyboard_bounds() == (0, 1400, 1080, 1920)


def test_backend_reads_keyboard_bounds_from_sk_region_output() -> None:
    class SkRegionDevice(FakeDevice):
        def shell(self, command):
            if command == ["dumpsys", "input_method"]:
                return "mInputShown=true"
            if command == ["dumpsys", "window", "windows"]:
                return """
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
                """
            return super().shell(command)

    backend = AndroidRecordingBackend(SkRegionDevice())

    assert backend.get_soft_keyboard_bounds() == (0, 1784, 1440, 2960)
