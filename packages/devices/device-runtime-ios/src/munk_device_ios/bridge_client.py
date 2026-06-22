from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Callable, cast

import httpx


class IOSBridgeClientError(RuntimeError):
    """Raised when the iOS bridge sidecar returns an error."""


@dataclass(frozen=True)
class IOSBridgeSessionHandle:
    base_url: str
    session_id: str
    backend_kind: str
    device_udid: str


@dataclass(frozen=True)
class IOSBridgeCurrentAppPayload:
    bundle_id: str | None
    name: str | None
    pid: int | None
    raw: dict[str, Any]


@dataclass(frozen=True)
class IOSBridgeAccessibilityRectPayload:
    x: float
    y: float
    width: float
    height: float

    def to_wda_payload(self) -> dict[str, float]:
        return {
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }


@dataclass(frozen=True)
class IOSBridgeAccessibilityNodePayload:
    node_type: str | None
    name: str | None
    label: str | None
    value: str | int | float | bool | None
    identifier: str | None
    bundle_id: str | None
    enabled: bool | None
    visible: bool | None
    accessible: bool | None
    focused: bool | None
    selected: bool | None
    rect: IOSBridgeAccessibilityRectPayload | None
    native_frame: str | None
    frame: str | None
    children: tuple["IOSBridgeAccessibilityNodePayload", ...]

    def to_wda_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "children": [child.to_wda_payload() for child in self.children],
        }
        if self.node_type is not None:
            payload["type"] = self.node_type
        if self.name is not None:
            payload["name"] = self.name
        if self.label is not None:
            payload["label"] = self.label
        if self.value is not None:
            payload["value"] = self.value
        if self.identifier is not None:
            payload["identifier"] = self.identifier
        if self.bundle_id is not None:
            payload["bundleId"] = self.bundle_id
        if self.enabled is not None:
            payload["enabled"] = self.enabled
        if self.visible is not None:
            payload["visible"] = self.visible
        if self.accessible is not None:
            payload["accessible"] = self.accessible
        if self.focused is not None:
            payload["focused"] = self.focused
        if self.selected is not None:
            payload["selected"] = self.selected
        if self.rect is not None:
            payload["rect"] = self.rect.to_wda_payload()
        if self.native_frame is not None:
            payload["nativeFrame"] = self.native_frame
        if self.frame is not None:
            payload["frame"] = self.frame
        return payload


@dataclass(frozen=True)
class IOSBridgeAccessibilityTreePayload:
    root: IOSBridgeAccessibilityNodePayload

    def to_wda_payload(self) -> dict[str, Any]:
        return self.root.to_wda_payload()


class IOSBridgeClient:
    DEFAULT_TIMEOUT_SEC = 90.0

    def __init__(
        self,
        *,
        session: IOSBridgeSessionHandle,
        timeout_sec: float = DEFAULT_TIMEOUT_SEC,
        client: httpx.Client | None = None,
        on_close: Callable[[str], None] | None = None,
    ) -> None:
        self._session = session
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=session.base_url.rstrip("/"), timeout=timeout_sec, trust_env=False)
        self._on_close = on_close

    @property
    def session_id(self) -> str:
        return self._session.session_id

    @property
    def backend_kind(self) -> str:
        return self._session.backend_kind

    def ensure_ready(self) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/wda/ensure-ready")

    def screenshot_png(self) -> bytes:
        payload = self._request("POST", f"/sessions/{self._session.session_id}/device/screenshot")
        data = cast(dict[str, Any], payload.get("data") or {})
        encoded = data.get("png_base64")
        if not isinstance(encoded, str):
            raise IOSBridgeClientError("ios bridge screenshot response missing png_base64")
        return base64.b64decode(encoded)

    def tap(self, x: int, y: int) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/device/tap", json={"x": x, "y": y})

    def long_press(self, x: int, y: int, duration_sec: float | None = None) -> None:
        self._request(
            "POST",
            f"/sessions/{self._session.session_id}/device/long-press",
            json={"x": x, "y": y, "duration_sec": duration_sec},
        )

    def swipe(
        self,
        *,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_sec: float | None = None,
    ) -> None:
        self._request(
            "POST",
            f"/sessions/{self._session.session_id}/device/swipe",
            json={
                "start_x": start_x,
                "start_y": start_y,
                "end_x": end_x,
                "end_y": end_y,
                "duration_sec": duration_sec,
            },
        )

    def type_text(self, text: str) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/device/type-text", json={"text": text})

    def clear_text(self) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/device/clear-text")

    def press(self, key: str) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/device/press", json={"key": key})

    def dismiss_soft_keyboard(self) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/device/dismiss-soft-keyboard")

    def current_app(self) -> IOSBridgeCurrentAppPayload:
        payload = self._request("GET", f"/sessions/{self._session.session_id}/device/current-app")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise IOSBridgeClientError("ios bridge current-app response missing data object")
        return _parse_current_app_payload(data)

    def window_size(self) -> tuple[int, int]:
        payload = self._request("GET", f"/sessions/{self._session.session_id}/device/window-size")
        data = cast(dict[str, Any], payload.get("data") or {})
        return int(data.get("width", 0)), int(data.get("height", 0))

    def accessibility_tree(self) -> IOSBridgeAccessibilityTreePayload | None:
        payload = self._request("GET", f"/sessions/{self._session.session_id}/device/accessibility-tree")
        data = payload.get("data")
        if data is None:
            return None
        if not isinstance(data, dict):
            raise IOSBridgeClientError("ios bridge accessibility-tree response missing data object")
        return _parse_accessibility_tree_payload(data)

    def launch_app(self, bundle_id: str) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/apps/launch", json={"bundle_id": bundle_id})

    def terminate_app(self, bundle_id: str) -> None:
        self._request("POST", f"/sessions/{self._session.session_id}/apps/terminate", json={"bundle_id": bundle_id})

    def close(self) -> None:
        try:
            if self._on_close is not None:
                self._on_close(self._session.session_id)
        finally:
            if self._owns_client:
                self._client.close()

    def _request(self, method: str, path: str, *, json: dict[str, object] | None = None) -> dict[str, Any]:
        response = self._client.request(method, path, json=json)
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            payload_data = cast(dict[str, Any], payload) if isinstance(payload, dict) else {}
            error = payload_data.get("error")
            if isinstance(error, dict):
                error_data = cast(dict[str, Any], error)
                code = error_data.get("code")
                message = error_data.get("message")
                raise IOSBridgeClientError(f"{code}: {message}")
            response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise IOSBridgeClientError(f"ios bridge response for {path} must be a JSON object")
        return cast(dict[str, Any], payload)


def _parse_current_app_payload(data: dict[str, Any]) -> IOSBridgeCurrentAppPayload:
    raw = data.get("raw")
    return IOSBridgeCurrentAppPayload(
        bundle_id=_read_optional_string(data, "bundle_id"),
        name=_read_optional_string(data, "name"),
        pid=_read_optional_int(data, "pid"),
        raw=cast(dict[str, Any], raw) if isinstance(raw, dict) else {},
    )


def _parse_accessibility_tree_payload(
    data: dict[str, Any],
) -> IOSBridgeAccessibilityTreePayload:
    root = data.get("root")
    if not isinstance(root, dict):
        raise IOSBridgeClientError(
            "ios bridge accessibility-tree response missing root object"
        )
    return IOSBridgeAccessibilityTreePayload(root=_parse_accessibility_node(root))


def _parse_accessibility_node(
    data: dict[str, Any],
) -> IOSBridgeAccessibilityNodePayload:
    raw_children = data.get("children")
    children: tuple[IOSBridgeAccessibilityNodePayload, ...]
    if isinstance(raw_children, list):
        child_items = cast(list[Any], raw_children)
        children = tuple(
            _parse_accessibility_node(item)
            for item in child_items
            if isinstance(item, dict)
        )
    else:
        children = ()
    return IOSBridgeAccessibilityNodePayload(
        node_type=_read_optional_string(data, "type"),
        name=_read_optional_string(data, "name"),
        label=_read_optional_string(data, "label"),
        value=_read_optional_scalar(data.get("value")),
        identifier=_read_optional_string(data, "identifier"),
        bundle_id=_read_optional_string(data, "bundle_id"),
        enabled=_read_optional_bool(data, "enabled"),
        visible=_read_optional_bool(data, "visible"),
        accessible=_read_optional_bool(data, "accessible"),
        focused=_read_optional_bool(data, "focused"),
        selected=_read_optional_bool(data, "selected"),
        rect=_parse_accessibility_rect(data.get("rect")),
        native_frame=_read_optional_string(data, "native_frame"),
        frame=_read_optional_string(data, "frame"),
        children=children,
    )


def _parse_accessibility_rect(
    value: Any,
) -> IOSBridgeAccessibilityRectPayload | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise IOSBridgeClientError(
            "ios bridge accessibility-tree rect must be an object"
        )
    return IOSBridgeAccessibilityRectPayload(
        x=_read_required_number(value, "x"),
        y=_read_required_number(value, "y"),
        width=_read_required_number(value, "width"),
        height=_read_required_number(value, "height"),
    )


def _read_optional_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def _read_optional_bool(payload: dict[str, Any], key: str) -> bool | None:
    value = payload.get(key)
    if isinstance(value, bool):
        return value
    return None


def _read_optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if isinstance(value, int):
        return value
    return None


def _read_required_number(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    raise IOSBridgeClientError(
        f"ios bridge accessibility-tree rect missing numeric {key}"
    )


def _read_optional_scalar(
    value: Any,
) -> str | int | float | bool | None:
    if isinstance(value, (str, int, float, bool)):
        return value
    return None
