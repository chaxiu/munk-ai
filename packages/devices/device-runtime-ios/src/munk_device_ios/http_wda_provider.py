from __future__ import annotations

from typing import Any, cast

import httpx

from .wda_provider import WDAAccessibilityTree, WDAAppState


class HttpWDAProvider:
    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8100",
        timeout_sec: float = 15.0,
        client: httpx.Client | None = None,
        session_capabilities: dict[str, object] | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=self._base_url, timeout=timeout_sec)
        self._session_capabilities = session_capabilities or {"alwaysMatch": {}}
        self._session_id: str | None = None

    def ensure_session(self) -> None:
        self._ensure_session_id()

    def screenshot_png(self) -> bytes:
        payload = self._request("GET", "/screenshot")
        value = payload.get("value")
        if not isinstance(value, str):
            raise ValueError("WDA screenshot response missing base64 payload")
        return _decode_base64(value)

    def tap(self, x: int, y: int) -> None:
        self._session_request("POST", "/wda/tap", json={"x": x, "y": y})

    def long_press(self, x: int, y: int, duration_sec: float | None = None) -> None:
        payload: dict[str, object] = {
            "x": x,
            "y": y,
            "duration": duration_sec if duration_sec is not None else 1.0,
        }
        self._session_request("POST", "/wda/touchAndHold", json=payload)

    def swipe(
        self,
        *,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_sec: float | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "fromX": start_x,
            "fromY": start_y,
            "toX": end_x,
            "toY": end_y,
        }
        if duration_sec is not None:
            payload["duration"] = duration_sec
        self._session_request("POST", "/wda/dragfromtoforduration", json=payload)

    def type_text(self, text: str) -> None:
        self._session_request("POST", "/wda/keyboard/dismiss", json={"keyNames": []}, allow_error=True)
        self._session_request("POST", "/wda/keys", json={"value": list(text)})

    def clear_text(self) -> None:
        element_id = self._active_element_id()
        self._session_request("POST", f"/element/{element_id}/clear")

    def press(self, key: str) -> None:
        normalized = key.strip().lower()
        if normalized == "home":
            self._request("POST", "/wda/homescreen")
            return
        self._session_request("POST", "/wda/keys", json={"value": [key]})

    def dismiss_soft_keyboard(self) -> None:
        self._session_request("POST", "/wda/keyboard/dismiss", json={"keyNames": []}, allow_error=True)

    def current_app(self) -> WDAAppState:
        active_app = self._request("GET", "/wda/activeAppInfo")
        value = active_app.get("value")
        raw: dict[str, Any] = cast(dict[str, Any], value) if isinstance(value, dict) else {}
        bundle_id = _read_string(raw, "bundleId")
        surface_identity = _read_string(raw, "bundleId") or _read_string(raw, "name")
        title = _read_string(raw, "name")
        return WDAAppState(
            bundle_id=bundle_id,
            surface_identity=surface_identity,
            title=title,
            raw=dict(raw),
        )

    def window_size(self) -> tuple[int, int]:
        payload = self._request("GET", "/window/size")
        value = payload.get("value")
        if not isinstance(value, dict):
            raise ValueError("WDA window size response missing value object")
        width = int(value.get("width", 0))
        height = int(value.get("height", 0))
        return width, height

    def accessibility_tree(self) -> WDAAccessibilityTree | None:
        payload = self._request("GET", "/source?format=json")
        value = payload.get("value")
        if isinstance(value, dict):
            return WDAAccessibilityTree(payload=value)
        return None

    def launch_app(self, bundle_id: str) -> None:
        self._session_request("POST", "/wda/apps/launch", json={"bundleId": bundle_id})

    def terminate_app(self, bundle_id: str) -> None:
        self._session_request("POST", "/wda/apps/terminate", json={"bundleId": bundle_id})

    def close(self) -> None:
        session_id = self._session_id
        self._session_id = None
        try:
            if session_id is not None:
                self._delete_session(session_id)
        finally:
            if self._owns_client:
                self._client.close()

    def _session_request(
        self,
        method: str,
        route: str,
        *,
        json: dict[str, object] | None = None,
        allow_error: bool = False,
    ) -> dict[str, Any]:
        try:
            return self._request(method, self._session_path(route), json=json, allow_error=allow_error)
        except httpx.HTTPStatusError as exc:
            if not self._should_recreate_session(exc.response):
                raise
            self._session_id = None
            return self._request(method, self._session_path(route), json=json, allow_error=allow_error)

    def _session_path(self, route: str) -> str:
        route_path = route if route.startswith("/") else f"/{route}"
        return f"/session/{self._ensure_session_id()}{route_path}"

    def _ensure_session_id(self) -> str:
        if self._session_id is None:
            self._session_id = self._create_session()
        return self._session_id

    def _create_session(self) -> str:
        payload = self._request("POST", "/session", json={"capabilities": self._session_capabilities})
        session_id = _read_string(payload, "sessionId")
        value = payload.get("value")
        if session_id is None and isinstance(value, dict):
            session_id = _read_string(cast(dict[str, Any], value), "sessionId")
        if session_id is None:
            raise ValueError("WDA create session response missing sessionId")
        return session_id

    def _active_element_id(self) -> str:
        payload = self._session_request("GET", "/element/active")
        value = payload.get("value")
        if not isinstance(value, dict):
            raise ValueError("WDA active element response missing value object")
        value_dict = cast(dict[str, Any], value)
        element_id = _read_string(value_dict, "element-6066-11e4-a52e-4f735466cecf")
        if element_id is None:
            element_id = _read_string(value_dict, "ELEMENT")
        if element_id is None:
            raise ValueError("WDA active element response missing element identifier")
        return element_id

    def _delete_session(self, session_id: str) -> None:
        try:
            self._request("DELETE", f"/session/{session_id}")
        except httpx.HTTPStatusError as exc:
            if not self._is_missing_session_response(exc.response):
                raise

    def _should_recreate_session(self, response: httpx.Response) -> bool:
        if response.status_code != 404 or self._session_id is None:
            return False
        return self._is_missing_session_response(response)

    def _is_missing_session_response(self, response: httpx.Response) -> bool:
        if response.status_code != 404:
            return False
        try:
            payload = response.json()
        except ValueError:
            return False
        if not isinstance(payload, dict):
            return False
        payload_dict = cast(dict[str, Any], payload)
        value = payload_dict.get("value")
        if not isinstance(value, dict):
            return False
        value_dict = cast(dict[str, Any], value)
        error = value_dict.get("error")
        if error == "invalid session id":
            return True
        message = value_dict.get("message")
        return isinstance(message, str) and "session" in message.lower()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, object] | None = None,
        allow_error: bool = False,
    ) -> dict[str, Any]:
        response = self._client.request(method, path, json=json)
        if allow_error and response.status_code >= 400:
            return {}
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError(f"WDA response for {path} must be a JSON object")
        return cast(dict[str, Any], payload)


def _decode_base64(value: str) -> bytes:
    import base64

    return base64.b64decode(value)


def _read_string(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None
