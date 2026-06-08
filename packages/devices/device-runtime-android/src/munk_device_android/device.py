from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import cast
from uuid import uuid4

import numpy as np
import uiautomator2 as u2
from munk.app import AppTarget
from munk.device import CurrentAppState, DeviceInfo, RuntimeLogEntry, RuntimeLogLevel
from munk.perception import ObservationTree
from munk.perception.image import BgrImage

_RECT_PATTERN = re.compile(r"Rect\((\d+),\s*(\d+)\s*-\s*(\d+),\s*(\d+)\)")
_BOUNDS_PATTERN = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")
_SK_REGION_PATTERN = re.compile(r"SkRegion\(\((\d+),\s*(\d+),\s*(\d+),\s*(\d+)\)\)")
_IME_HINTS = ("inputmethod", "input method", "ime")
_AUTOMATION_IME_HINTS = ("fastinputime", "adbkeyboard")
_LOCKED_WINDOW_HINTS = (
    "mshowinglockscreen=true",
    "mdreaminglockscreen=true",
    "isstatusbarkeyguard=true",
    "keyguardshowing=true",
)
ENV_ADB_PATH = "MUNK_ADB_PATH"
ENV_ADBUTILS_ADB_PATH = "ADBUTILS_ADB_PATH"


class AndroidDevice:
    def __init__(self, device: u2.Device, *, app_target: AppTarget | None = None) -> None:
        self._device = device
        self._app_target = app_target
        self._log_package_name: str | None = None
        self._log_process_names: tuple[str, ...] = ()
        self._log_pid: int | None = None
        self._log_session_started = False
        self._seen_log_keys: set[tuple[object, ...]] = set()

    @classmethod
    def connect(cls, device_ref: str | None = None, *, app_target: AppTarget | None = None) -> "AndroidDevice":
        _prepare_adb_environment()
        device = u2.connect(device_ref) if device_ref else u2.connect()
        return cls(device, app_target=app_target)

    def info(self) -> DeviceInfo:
        info = self._device.info
        width = int(info.get("displayWidth") or 0)
        height = int(info.get("displayHeight") or 0)
        device_ref = info.get("serial")
        return DeviceInfo(width=width, height=height, platform="android", device_ref=device_ref)

    def screenshot_bgr(self) -> BgrImage:
        image = self._device.screenshot(format="opencv")
        if not isinstance(image, np.ndarray):
            raise ValueError("screenshot not returned as ndarray")
        return cast(BgrImage, image)

    def click(self, x: int, y: int) -> None:
        self._device.click(x, y)

    def long_press(self, x: int, y: int, duration: float | None = None) -> None:
        long_click = getattr(self._device, "long_click", None)
        hold_duration = duration if duration is not None else 1.0
        if callable(long_click):
            long_click(x, y, hold_duration)
            return
        self._device.swipe(x, y, x, y, hold_duration)

    def scroll(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
    ) -> None:
        if duration is None:
            self._device.swipe(start[0], start[1], end[0], end[1])
        else:
            self._device.swipe(start[0], start[1], end[0], end[1], duration)

    def press(self, key: str) -> None:
        self._device.press(key)

    def unlock(self) -> None:
        if self.is_locked() is False:
            return
        unlock = getattr(self._device, "unlock", None)
        if callable(unlock):
            unlock()
            if self.is_locked() is False:
                return
        self._perform_unlock_swipe()
        if self.is_locked() is False:
            return
        self._perform_unlock_swipe()

    def is_locked(self) -> bool | None:
        screen_on = self._is_screen_on()
        if screen_on is False:
            return True
        response = self._device.shell(["dumpsys", "window", "policy"])
        output = _shell_output_text(response)
        locked = _parse_android_lock_state(output)
        if locked is not None:
            return locked
        response = self._device.shell(["dumpsys", "window"])
        output = _shell_output_text(response)
        return _parse_android_lock_state(output)

    def input_text(self, text: str) -> None:
        try:
            self._input_text_via_uiautomator_ime(text)
            return
        except Exception as exc:
            if text.isascii():
                self._input_text_via_adb_shell(text)
                return
            raise RuntimeError(f"android unicode input requires automation IME: {exc}") from exc

    def clear_text(self) -> None:
        self._device.clear_text()

    def app_start(self, entry_identity: str) -> None:
        self._device.app_start(entry_identity, wait=True)

    def app_stop(self, entry_identity: str) -> None:
        self._device.app_stop(entry_identity)

    def app_install(self, artifact_path: str) -> None:
        push = getattr(self._device, "push", None)
        if not callable(push):
            raise RuntimeError("android app install failed: device transport does not support file push")
        remote_artifact_path = f"/data/local/tmp/munk-install-{uuid4().hex}{Path(artifact_path).suffix or '.apk'}"
        try:
            push(artifact_path, remote_artifact_path)
            response = self._device.shell(["pm", "install", "-r", remote_artifact_path])
            output = _shell_output_text(response) or ""
            normalized = output.strip()
            if "success" not in normalized.lower():
                detail = normalized or "unknown install failure"
                raise RuntimeError(f"android app install failed: {detail}")
        finally:
            self._device.shell(["rm", "-f", remote_artifact_path])

    def app_current(self) -> CurrentAppState:
        current = cast(dict[str, object], self._device.app_current())
        entry_identity = current.get("package")
        activity = current.get("activity")
        package_name = entry_identity if isinstance(entry_identity, str) and entry_identity else None
        activity_name = activity if isinstance(activity, str) and activity else None
        return CurrentAppState(
            platform="android",
            entry_identity=package_name,
            surface_identity=_android_surface_identity(package_name, activity_name),
            activity_name=activity_name,
            raw={key: value for key, value in current.items()},
        )

    def dismiss_soft_keyboard(self) -> None:
        self._device.press("back")

    def is_soft_keyboard_visible(self) -> bool | None:
        response = self._device.shell(["dumpsys", "input_method"])
        output = _shell_output_text(response)
        if output is None:
            return None
        lowered = output.lower()
        if "minputshown=true" in lowered:
            return True
        if "minputshown=false" in lowered:
            return False
        return None

    def get_soft_keyboard_bounds(self) -> tuple[int, int, int, int] | None:
        if self.is_soft_keyboard_visible() is not True:
            return None
        response = self._device.shell(["dumpsys", "window", "windows"])
        output = _shell_output_text(response)
        if output is None:
            return None
        return _extract_keyboard_bounds(output)

    def window_size(self) -> tuple[int, int]:
        size = self._device.window_size()
        return int(size[0]), int(size[1])

    def capture_observation_tree(self) -> ObservationTree | None:
        dump = getattr(self._device, "dump_hierarchy", None)
        if not callable(dump):
            return None
        xml_text = dump()
        if not isinstance(xml_text, str):
            return None
        cleaned = xml_text.strip()
        if not cleaned:
            return None
        return ObservationTree(source_type="android_uixml", content_type="xml", payload=cleaned)

    def start_log_session(self) -> None:
        package_name = self._resolve_log_package_name()
        self._log_package_name = package_name
        self._log_process_names = _build_process_name_candidates(package_name)
        self._log_pid = self._resolve_pid(package_name)
        self._seen_log_keys.clear()
        self._log_session_started = True

    def drain_runtime_logs(self) -> list[RuntimeLogEntry]:
        if not self._log_session_started:
            return []
        if self._log_package_name and self._log_pid is None:
            self._log_pid = self._resolve_pid(self._log_package_name)
        output = self._read_logcat_output()
        if not output:
            return []
        entries = _parse_logcat_entries(output)
        if self._log_pid is not None:
            filtered = [entry for entry in entries if _entry_pid(entry) == self._log_pid]
        elif self._log_process_names:
            filtered = [
                entry
                for entry in entries
                if _matches_process_name(entry, self._log_process_names)
            ]
        else:
            return []
        incremental: list[RuntimeLogEntry] = []
        for entry in filtered:
            key = _entry_dedupe_key(entry)
            if key in self._seen_log_keys:
                continue
            self._seen_log_keys.add(key)
            incremental.append(entry)
        return incremental

    def stop_log_session(self) -> None:
        self._log_package_name = None
        self._log_process_names = ()
        self._log_pid = None
        self._log_session_started = False
        self._seen_log_keys.clear()

    def close(self) -> None:
        self.stop_log_session()

    def _resolve_log_package_name(self) -> str | None:
        if self._app_target is not None and self._app_target.android is not None:
            package_name = self._app_target.android.package_name.strip()
            if package_name:
                return package_name
        current = self.app_current().entry_identity
        if isinstance(current, str) and current.strip():
            return current.strip()
        return None

    def _resolve_pid(self, package_name: str | None) -> int | None:
        if not package_name:
            return None
        response = self._device.shell(["pidof", "-s", package_name])
        output = _shell_output_text(response)
        if output is None:
            return None
        first = output.strip().split()
        if not first:
            return None
        try:
            return int(first[0])
        except ValueError:
            return None

    def _is_screen_on(self) -> bool | None:
        info = getattr(self._device, "info", None)
        if isinstance(info, dict):
            info_dict = cast(dict[str, object], info)
            screen_on = info_dict.get("screenOn")
            if isinstance(screen_on, bool):
                return screen_on
        is_screen_on = getattr(self._device, "is_screen_on", None)
        if callable(is_screen_on):
            result = is_screen_on()
            return result if isinstance(result, bool) else None
        return None

    def _ensure_screen_on(self) -> None:
        screen_on = getattr(self._device, "screen_on", None)
        if callable(screen_on):
            screen_on()
            return
        if self._is_screen_on() is False:
            self._device.press("power")

    def _perform_unlock_swipe(self) -> None:
        self._ensure_screen_on()
        width, height = self.window_size()
        x = max(int(round(width * 0.5)), 1)
        start_y = max(int(round(height * 0.82)), 1)
        end_y = max(int(round(height * 0.18)), 1)
        self._device.swipe(x, start_y, x, end_y, 0.2)

    def _read_logcat_output(self) -> str | None:
        command = ["logcat", "-d", "-v", "threadtime"]
        if self._log_pid is not None:
            command.extend(["--pid", str(self._log_pid)])
        response = self._device.shell(command)
        return _shell_output_text(response)

    def _input_text_via_uiautomator_ime(self, text: str) -> None:
        previous_ime = self._current_ime()
        self._ensure_automation_ime_ready()
        try:
            self._device.send_keys(text, clear=False)
        finally:
            self._restore_previous_ime(previous_ime)

    def _input_text_via_adb_shell(self, text: str) -> None:
        payload = text.replace(" ", "%s")
        self._device.shell(["input", "text", payload])

    def _ensure_automation_ime_ready(self) -> None:
        set_fastinput_ime = getattr(self._device, "set_fastinput_ime", None)
        if not callable(set_fastinput_ime):
            raise RuntimeError("uiautomator2 set_fastinput_ime is unavailable")
        set_fastinput_ime(True)
        wait_fastinput_ime = getattr(self._device, "wait_fastinput_ime", None)
        if callable(wait_fastinput_ime):
            wait_fastinput_ime()
        current_ime = self._current_ime()
        if current_ime is not None and not _is_automation_ime(current_ime):
            raise RuntimeError(f"automation IME did not become active: {current_ime}")

    def _current_ime(self) -> str | None:
        current_ime = getattr(self._device, "current_ime", None)
        if not callable(current_ime):
            return None
        value = current_ime()
        if not isinstance(value, str):
            return None
        normalized = value.strip()
        return normalized or None

    def _restore_previous_ime(self, previous_ime: str | None) -> None:
        if not previous_ime or _is_automation_ime(previous_ime):
            return
        try:
            self._device.shell(["ime", "set", previous_ime])
        except Exception:
            # Best-effort restore should not overwrite the main input result.
            return


def _shell_output_text(response: object) -> str | None:
    if isinstance(response, str):
        return response
    if isinstance(response, bytes):
        return response.decode("utf-8", errors="ignore")
    if isinstance(response, tuple) and response:
        first = cast(tuple[object, ...], response)[0]
        if isinstance(first, str):
            return first
        if isinstance(first, bytes):
            return first.decode("utf-8", errors="ignore")
    for attr in ("output", "stdout", "content"):
        value = getattr(response, attr, None)
        if isinstance(value, str):
            return value
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="ignore")
    return None


def _prepare_adb_environment() -> None:
    explicit = os.environ.get(ENV_ADB_PATH)
    if explicit:
        os.environ[ENV_ADBUTILS_ADB_PATH] = explicit


def _is_automation_ime(ime_id: str) -> bool:
    lowered = ime_id.strip().lower()
    return any(hint in lowered for hint in _AUTOMATION_IME_HINTS)


def _extract_keyboard_bounds(output: str) -> tuple[int, int, int, int] | None:
    lines = output.splitlines()
    candidates: list[tuple[int, int, int, int]] = []
    for index, line in enumerate(lines):
        lowered = line.lower()
        if not any(hint in lowered for hint in _IME_HINTS):
            continue
        for candidate_line in _iter_window_block_lines(lines, index):
            bounds = _parse_bounds(candidate_line)
            if bounds is not None:
                candidates.append(bounds)
    if not candidates:
        return None
    valid_candidates = [bounds for bounds in candidates if bounds[2] > bounds[0] and bounds[3] > bounds[1]]
    if not valid_candidates:
        return None
    return max(valid_candidates, key=lambda bounds: (bounds[1], _box_area(bounds)))


def _iter_window_block_lines(lines: list[str], start_index: int) -> list[str]:
    block_lines: list[str] = []
    for index in range(start_index, len(lines)):
        candidate_line = lines[index]
        if index > start_index and candidate_line.startswith("  Window #"):
            break
        block_lines.append(candidate_line)
    return block_lines


def _parse_bounds(line: str) -> tuple[int, int, int, int] | None:
    rect_match = _RECT_PATTERN.search(line)
    if rect_match is not None:
        left = int(rect_match.group(1))
        top = int(rect_match.group(2))
        right = int(rect_match.group(3))
        bottom = int(rect_match.group(4))
        return (left, top, right, bottom)
    bounds_match = _BOUNDS_PATTERN.search(line)
    if bounds_match is not None:
        left = int(bounds_match.group(1))
        top = int(bounds_match.group(2))
        right = int(bounds_match.group(3))
        bottom = int(bounds_match.group(4))
        return (left, top, right, bottom)
    sk_region_match = _SK_REGION_PATTERN.search(line)
    if sk_region_match is not None:
        left = int(sk_region_match.group(1))
        top = int(sk_region_match.group(2))
        right = int(sk_region_match.group(3))
        bottom = int(sk_region_match.group(4))
        return (left, top, right, bottom)
    return None


def _parse_android_lock_state(output: str | None) -> bool | None:
    if not output:
        return None
    lowered = output.lower()
    if any(hint in lowered for hint in _LOCKED_WINDOW_HINTS):
        return True
    if (
        "mshowinglockscreen=false" in lowered
        or "mdreaminglockscreen=false" in lowered
        or "isstatusbarkeyguard=false" in lowered
        or "keyguardshowing=false" in lowered
    ):
        return False
    return None


def _box_area(bounds: tuple[int, int, int, int]) -> int:
    return max(0, bounds[2] - bounds[0]) * max(0, bounds[3] - bounds[1])


def _android_surface_identity(package_name: str | None, activity_name: str | None) -> str | None:
    if package_name and activity_name:
        return f"{package_name}/{activity_name}"
    return package_name


_LOGCAT_THREADTIME_PATTERN = re.compile(
    r"^(?P<month>\d{2})-(?P<day>\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+"
    r"(?P<pid>\d+)\s+"
    r"(?P<tid>\d+)\s+"
    r"(?P<priority>[VDIWEAF])\s+"
    r"(?P<tag>.*?):\s(?P<message>.*)$"
)

_LOG_LEVELS = {
    "V": "debug",
    "D": "debug",
    "I": "info",
    "W": "warning",
    "E": "error",
    "A": "error",
    "F": "error",
}


def _build_process_name_candidates(package_name: str | None) -> tuple[str, ...]:
    if not package_name:
        return ()
    return (package_name,)


def _parse_logcat_entries(output: str) -> list[RuntimeLogEntry]:
    entries: list[RuntimeLogEntry] = []
    for raw_line in output.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        match = _LOGCAT_THREADTIME_PATTERN.match(line)
        if match is None:
            entries.append(
                RuntimeLogEntry(
                    timestamp_ms=None,
                    level="unknown",
                    source="android_logcat",
                    message=line,
                    raw={"line": line},
                )
            )
            continue
        raw = match.groupdict()
        message = raw["message"].strip()
        if not message:
            continue
        pid = int(raw["pid"])
        timestamp_ms = _parse_log_timestamp_ms(raw["month"], raw["day"], raw["time"])
        entries.append(
            RuntimeLogEntry(
                timestamp_ms=timestamp_ms,
                level=cast(RuntimeLogLevel, _LOG_LEVELS.get(raw["priority"], "unknown")),
                source="android_logcat",
                message=message,
                raw={
                    "line": line,
                    "pid": pid,
                    "tid": int(raw["tid"]),
                    "priority": raw["priority"],
                    "tag": raw["tag"].strip(),
                },
            )
        )
    return entries


def _parse_log_timestamp_ms(month: str, day: str, time_value: str) -> int | None:
    try:
        current_year = datetime.now().year
        parsed = datetime.strptime(
            f"{current_year}-{month}-{day} {time_value}",
            "%Y-%m-%d %H:%M:%S.%f",
        )
    except ValueError:
        return None
    return int(parsed.timestamp() * 1000)


def _entry_pid(entry: RuntimeLogEntry) -> int | None:
    value = entry.raw.get("pid")
    if isinstance(value, int):
        return value
    return None


def _matches_process_name(entry: RuntimeLogEntry, candidates: tuple[str, ...]) -> bool:
    line = str(entry.raw.get("line", "")).strip()
    tag = str(entry.raw.get("tag", "")).strip()
    message = entry.message
    searchable = "\n".join((line, tag, message))
    return any(candidate in searchable for candidate in candidates)


def _entry_dedupe_key(entry: RuntimeLogEntry) -> tuple[object, ...]:
    return (
        entry.timestamp_ms,
        entry.level,
        entry.message,
        entry.raw.get("pid"),
        entry.raw.get("tag"),
    )
