from __future__ import annotations

import os
import subprocess

from munk_device_android.discovery import list_android_devices


def test_list_android_devices_returns_online_device_descriptors() -> None:
    output = """
List of devices attached
88TY01VGT              device usb:2-2 product:crosshatch model:Pixel_3_XL device:crosshatch transport_id:2
emulator-5554          device product:sdk_gphone64_arm64 model:sdk_gphone64_arm64 device:emu64a transport_id:4
"""

    devices = list_android_devices(command_runner=lambda command: output)

    assert [device.device_ref for device in devices] == ["emulator-5554", "88TY01VGT"]
    assert devices[0].kind == "emulator"
    assert devices[0].display_name == "sdk gphone64 arm64"
    assert devices[0].is_booted is True
    assert devices[1].kind == "real_device"
    assert devices[1].display_name == "Pixel 3 XL"
    assert devices[1].is_booted is True
    assert devices[1].raw == {
        "usb": "2-2",
        "product": "crosshatch",
        "model": "Pixel_3_XL",
        "device": "crosshatch",
        "transport_id": "2",
    }


def test_list_android_devices_filters_non_operable_states() -> None:
    output = """
List of devices attached
ABC123                 offline transport_id:1
DEF456                 unauthorized usb:1-1
"""

    devices = list_android_devices(command_runner=lambda command: output)

    assert devices == []


def test_list_android_devices_prefers_explicit_adb_env(monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setenv("MUNK_ADB_PATH", "/tmp/munk-adb")
    monkeypatch.delenv("ADBUTILS_ADB_PATH", raising=False)
    captured: list[list[str]] = []

    def fake_runner(command: list[str]) -> str:
        captured.append(command)
        return "List of devices attached\n"

    list_android_devices(command_runner=fake_runner)

    assert captured == [["/tmp/munk-adb", "devices", "-l"]]
    assert os.environ["ADBUTILS_ADB_PATH"] == "/tmp/munk-adb"


def test_list_android_devices_retries_after_starting_adb_server(monkeypatch) -> None:  # noqa: ANN001
    calls: list[list[str]] = []
    responses = iter(
        [
            subprocess.CalledProcessError(1, ["/tmp/munk-adb", "devices", "-l"], stderr="daemon not running"),
            subprocess.CompletedProcess(["/tmp/munk-adb", "start-server"], 0, stdout="", stderr=""),
            subprocess.CompletedProcess(["/tmp/munk-adb", "devices", "-l"], 0, stdout="List of devices attached\n", stderr=""),
        ]
    )

    monkeypatch.setenv("MUNK_ADB_PATH", "/tmp/munk-adb")

    def fake_run(command: list[str], *, check: bool, capture_output: bool, text: bool):  # noqa: ANN001
        assert check is True
        assert capture_output is True
        assert text is True
        calls.append(command)
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("munk_device_android.discovery.subprocess.run", fake_run)

    devices = list_android_devices()

    assert devices == []
    assert calls == [
        ["/tmp/munk-adb", "devices", "-l"],
        ["/tmp/munk-adb", "start-server"],
        ["/tmp/munk-adb", "devices", "-l"],
    ]
