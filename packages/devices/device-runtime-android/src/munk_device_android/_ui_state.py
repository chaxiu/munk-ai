from __future__ import annotations

import os
import re
from typing import cast

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


def shell_output_text(response: object) -> str | None:
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


def prepare_adb_environment() -> None:
    explicit = os.environ.get(ENV_ADB_PATH)
    if explicit:
        os.environ[ENV_ADBUTILS_ADB_PATH] = explicit


def is_automation_ime(ime_id: str) -> bool:
    lowered = ime_id.strip().lower()
    return any(hint in lowered for hint in _AUTOMATION_IME_HINTS)


def extract_keyboard_bounds(output: str) -> tuple[int, int, int, int] | None:
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


def parse_android_lock_state(output: str | None) -> bool | None:
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


def android_surface_identity(package_name: str | None, activity_name: str | None) -> str | None:
    if package_name and activity_name:
        return f"{package_name}/{activity_name}"
    return package_name


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


def _box_area(bounds: tuple[int, int, int, int]) -> int:
    return max(0, bounds[2] - bounds[0]) * max(0, bounds[3] - bounds[1])


def optional_handle_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def optional_handle_box(value: object) -> tuple[int, int, int, int] | None:
    if not isinstance(value, (tuple, list)) or len(value) != 4:
        return None
    try:
        left, top, right, bottom = (int(value[0]), int(value[1]), int(value[2]), int(value[3]))
    except (TypeError, ValueError):
        return None
    return (left, top, right, bottom)


def format_android_bounds(box: tuple[int, int, int, int]) -> str:
    left, top, right, bottom = box
    return f"[{left},{top}][{right},{bottom}]"


def coerce_checkbox_desired(text: str) -> bool:
    normalized = text.strip().lower()
    if normalized in {"1", "true", "yes", "on", "checked"}:
        return True
    if normalized in {"0", "false", "no", "off", "unchecked"}:
        return False
    return bool(normalized)
