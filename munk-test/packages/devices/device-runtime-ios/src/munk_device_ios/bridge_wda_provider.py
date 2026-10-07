from __future__ import annotations

from .bridge_client import IOSBridgeClient
from .wda_provider import WDAAccessibilityTree, WDAAppState


class BridgeWDAProvider:
    def __init__(self, *, client: IOSBridgeClient) -> None:
        self._client = client

    def ensure_session(self) -> None:
        self._client.ensure_ready()

    def screenshot_png(self) -> bytes:
        return self._client.screenshot_png()

    def tap(self, x: int, y: int) -> None:
        self._client.tap(x, y)

    def long_press(self, x: int, y: int, duration_sec: float | None = None) -> None:
        self._client.long_press(x, y, duration_sec)

    def swipe(
        self,
        *,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_sec: float | None = None,
    ) -> None:
        self._client.swipe(
            start_x=start_x,
            start_y=start_y,
            end_x=end_x,
            end_y=end_y,
            duration_sec=duration_sec,
        )

    def type_text(self, text: str) -> None:
        self._client.type_text(text)

    def clear_text(self) -> None:
        self._client.clear_text()

    def find_element(self, using: str, value: str) -> str:
        return self._client.find_element(using, value)

    def click_element(self, element_id: str) -> None:
        self._client.click_element(element_id)

    def clear_element(self, element_id: str) -> None:
        self._client.clear_element(element_id)

    def set_element_value(self, element_id: str, text: str) -> None:
        self._client.set_element_value(element_id, text)

    def get_element_attribute(self, element_id: str, name: str) -> str | None:
        return self._client.get_element_attribute(element_id, name)

    def press(self, key: str) -> None:
        self._client.press(key)

    def dismiss_soft_keyboard(self) -> None:
        self._client.dismiss_soft_keyboard()

    def current_app(self) -> WDAAppState:
        current_app = self._client.current_app()
        raw = dict(current_app.raw)
        bundle_id = current_app.bundle_id
        surface_identity = current_app.bundle_id or current_app.name
        title = current_app.name
        return WDAAppState(
            bundle_id=bundle_id,
            surface_identity=surface_identity,
            title=title,
            raw=raw,
        )

    def window_size(self) -> tuple[int, int]:
        return self._client.window_size()

    def accessibility_tree(self) -> WDAAccessibilityTree | None:
        tree = self._client.accessibility_tree()
        if tree is None:
            return None
        return WDAAccessibilityTree(payload=tree.to_wda_payload())

    def launch_app(self, bundle_id: str) -> None:
        self._client.launch_app(bundle_id)

    def terminate_app(self, bundle_id: str) -> None:
        self._client.terminate_app(bundle_id)

    def close(self) -> None:
        self._client.close()
