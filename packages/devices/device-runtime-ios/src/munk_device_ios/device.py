from __future__ import annotations

import json
from typing import Any, cast

import cv2
import numpy as np
from munk.app import AppTarget
from munk.device import CurrentAppState, RuntimeLogEntry
from munk.perception import ObservationTree
from munk.perception.image import BgrImage

from .http_wda_provider import HttpWDAProvider
from .runtime_logs import IOSLogStream, IOSRuntimeLogStream
from .wda_provider import WDAProvider


class IOSDevice:
    def __init__(
        self,
        *,
        device_ref: str | None = None,
        app_target: AppTarget,
        provider: WDAProvider | None = None,
        log_stream: IOSLogStream | None = None,
    ) -> None:
        if app_target.platform != "ios" or app_target.ios is None:
            raise ValueError("ios runtime requires an ios app_target")
        self._device_ref = device_ref
        self._app_target = app_target
        self._provider = provider or HttpWDAProvider(base_url=self._resolve_wda_url(app_target))
        self._log_stream = log_stream or IOSRuntimeLogStream(
            device_ref=device_ref,
            bundle_id=app_target.ios.bundle_id,
        )

    def screenshot_bgr(self) -> BgrImage:
        payload = self._provider.screenshot_png()
        return _decode_png_to_bgr(payload)

    def click(self, x: int, y: int) -> None:
        self._provider.tap(x, y)

    def long_press(self, x: int, y: int, duration: float | None = None) -> None:
        self._provider.long_press(x, y, duration_sec=duration)

    def scroll(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        duration: float | None = None,
    ) -> None:
        self._provider.swipe(
            start_x=start[0],
            start_y=start[1],
            end_x=end[0],
            end_y=end[1],
            duration_sec=duration,
        )

    def press(self, key: str) -> None:
        self._provider.press(key)

    def unlock(self) -> None:
        # WDA on real devices cannot reliably bypass passcode-protected lock screens.
        # Treat unlock as a best-effort readiness step so startup flows can call it safely.
        self._provider.ensure_session()

    def is_locked(self) -> bool | None:
        return None

    def input_text(self, text: str) -> None:
        self._provider.type_text(text)

    def clear_text(self) -> None:
        self._provider.clear_text()

    def app_current(self) -> CurrentAppState:
        state = self._provider.current_app()
        entry_identity = state.bundle_id or self._app_target.entry_identity
        surface_identity = state.surface_identity or entry_identity
        raw = dict(state.raw)
        if self._device_ref is not None:
            raw.setdefault("device_ref", self._device_ref)
        return CurrentAppState(
            platform="ios",
            entry_identity=entry_identity,
            title=state.title,
            raw=raw,
            surface_identity=surface_identity,
        )

    def window_size(self) -> tuple[int, int]:
        return self._provider.window_size()

    def capture_observation_tree(self) -> ObservationTree | None:
        tree = self._provider.accessibility_tree()
        if tree is None:
            return None
        return ObservationTree(
            source_type="ios_ax_tree",
            content_type="json",
            payload=json.dumps(tree.payload, ensure_ascii=False),
        )

    def dismiss_soft_keyboard(self) -> None:
        self._provider.dismiss_soft_keyboard()

    def is_soft_keyboard_visible(self) -> bool | None:
        keyboard_node = self._keyboard_node()
        if keyboard_node is None:
            tree = self._provider.accessibility_tree()
            return None if tree is None else False
        return True

    def get_soft_keyboard_bounds(self) -> tuple[int, int, int, int] | None:
        keyboard_node = self._keyboard_node()
        if keyboard_node is None:
            return None
        return _extract_rect_bounds(keyboard_node)

    def app_start(self, entry_identity: str) -> None:
        self._provider.launch_app(entry_identity)

    def app_stop(self, entry_identity: str) -> None:
        self._provider.terminate_app(entry_identity)

    def close(self) -> None:
        self.stop_log_session()
        self._provider.close()

    def start_log_session(self) -> None:
        self._log_stream.start()

    def drain_runtime_logs(self) -> list[RuntimeLogEntry]:
        return self._log_stream.drain()

    def stop_log_session(self) -> None:
        self._log_stream.stop()

    @property
    def provider(self) -> WDAProvider:
        return self._provider

    def _resolve_wda_url(self, app_target: AppTarget) -> str:
        url = app_target.launch_context.get("wda_url")
        if url:
            return url
        return "http://127.0.0.1:8100"

    def _keyboard_node(self) -> dict[str, Any] | None:
        tree = self._provider.accessibility_tree()
        if tree is None:
            return None
        return _find_keyboard_node(tree.payload)


def _decode_png_to_bgr(payload: bytes) -> BgrImage:
    buffer = np.frombuffer(payload, dtype=np.uint8)
    image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("failed to decode iOS screenshot payload")
    return cast(BgrImage, image)


def _find_keyboard_node(payload: dict[str, Any]) -> dict[str, Any] | None:
    stack: list[Any] = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            current_dict = cast(dict[str, Any], current)
            node_type = current_dict.get("type")
            if isinstance(node_type, str) and node_type in {"XCUIElementTypeKeyboard", "Keyboard"}:
                return current_dict
            stack.extend(current_dict.values())
        elif isinstance(current, list):
            stack.extend(current)
    return None


def _extract_rect_bounds(node: dict[str, Any]) -> tuple[int, int, int, int] | None:
    rect = node.get("rect")
    if isinstance(rect, dict):
        rect_dict = cast(dict[str, Any], rect)
        x = rect_dict.get("x")
        y = rect_dict.get("y")
        width = rect_dict.get("width")
        height = rect_dict.get("height")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            return None
        if not isinstance(width, (int, float)) or not isinstance(height, (int, float)):
            return None
        left = int(x)
        top = int(y)
        right = int(x + width)
        bottom = int(y + height)
    else:
        frame_text = node.get("nativeFrame") or node.get("frame")
        parsed = _parse_ios_frame_string(frame_text)
        if parsed is None:
            return None
        left, top, right, bottom = parsed
    if right <= left or bottom <= top:
        return None
    return (left, top, right, bottom)


def _parse_ios_frame_string(value: Any) -> tuple[int, int, int, int] | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text.startswith("{{") or "}, {" not in text or not text.endswith("}}"):
        return None
    try:
        position_part, size_part = text[2:-2].split("}, {", maxsplit=1)
        x_text, y_text = position_part.split(",", maxsplit=1)
        width_text, height_text = size_part.split(",", maxsplit=1)
        x = float(x_text.strip())
        y = float(y_text.strip())
        width = float(width_text.strip())
        height = float(height_text.strip())
    except ValueError:
        return None
    return (int(x), int(y), int(x + width), int(y + height))
